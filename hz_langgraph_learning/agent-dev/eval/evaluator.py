"""
LangSmith Evaluator for Market Assistant Agent

This module provides custom evaluators and evaluation datasets for testing
the market agent's performance on various tasks.

Features:
- Custom evaluators for intent detection, tool selection, response quality
- Evaluation datasets with ground truth
- LangSmith integration for tracking results
- Automated scoring and reporting

Usage:
    python evaluator.py --run-eval
"""

import os
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

# LangSmith imports
from langsmith import Client, aevaluate
from langsmith.evaluation import LangChainStringEvaluator
from langsmith.schemas import Example, Run

# Our agent
from agent_core.graph import run_market_agent
from agent_core.state import ChatMessage

load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Initialize LangSmith client
client = Client()

# ====== EVALUATION DATASET ======

EVALUATION_DATASET = [
    {
        "input": "What's the stock price of TSLA?",
        "expected_output": {
            "intents": ["price_check"],
            "symbols": ["TSLA"],
            "tools": ["yfinance", "alphavantage", "polygon"],
            "has_price_data": True,
            "has_news_data": False,
        },
        "metadata": {
            "category": "simple_price",
            "difficulty": "easy",
            "description": "Basic price check query",
        },
    },
    {
        "input": "Tell me about NVDA stock",
        "expected_output": {
            "intents": ["price_check", "news_search", "market_summary"],
            "symbols": ["NVDA"],
            "tools": ["yfinance", "alphavantage", "polygon", "news"],
            "has_price_data": True,
            "has_news_data": True,
        },
        "metadata": {
            "category": "market_summary",
            "difficulty": "medium",
            "description": "Comprehensive market analysis",
        },
    },
    {
        "input": "Compare NVDA and AMD stock prices",
        "expected_output": {
            "intents": ["comparison"],
            "symbols": ["NVDA", "AMD"],
            "tools": ["yfinance", "alphavantage", "polygon"],
            "has_price_data": True,
            "has_news_data": False,
        },
        "metadata": {
            "category": "comparison",
            "difficulty": "medium",
            "description": "Multi-symbol comparison",
        },
    },
    {
        "input": "What's the price of GLD and what happened to it?",
        "expected_output": {
            "intents": ["price_check", "news_search"],
            "symbols": ["GLD"],
            "tools": ["yfinance", "alphavantage", "polygon", "news"],
            "has_price_data": True,
            "has_news_data": True,
        },
        "metadata": {
            "category": "multi_intent",
            "difficulty": "medium",
            "description": "Multiple intents in one query",
        },
    },
    {
        "input": "Hello, how are you?",
        "expected_output": {
            "intents": ["chat"],
            "symbols": [],
            "tools": [],
            "has_price_data": False,
            "has_news_data": False,
        },
        "metadata": {
            "category": "chat",
            "difficulty": "easy",
            "description": "Conversational query",
        },
    },
]

# Multi-turn conversation test
CONVERSATION_DATASET = [
    {
        "turns": [
            {
                "input": "What's the stock price of TSLA?",
                "expected_output": {
                    "intents": ["price_check"],
                    "symbols": ["TSLA"],
                },
            },
            {
                "input": "What happened to it?",
                "expected_output": {
                    "intents": ["price_check", "news_search"],
                    "symbols": ["TSLA"],  # Should resolve "it" to TSLA
                },
            },
            {
                "input": "Compare it with RIVN",
                "expected_output": {
                    "intents": ["comparison"],
                    "symbols": ["TSLA", "RIVN"],  # Should resolve "it" to TSLA
                },
            },
        ],
        "metadata": {
            "category": "multi_turn",
            "difficulty": "hard",
            "description": "Multi-turn pronoun resolution",
        },
    },
]


# ====== CUSTOM EVALUATORS ======


def intent_accuracy_evaluator(run: Run, example: Example) -> dict:
    """
    Evaluator for intent detection accuracy.

    Checks if the agent correctly identified the user's intent(s).
    """
    try:
        # Extract actual intents from run output
        actual_intents = run.outputs.get("intents", [])
        if isinstance(actual_intents, list) and len(actual_intents) > 0:
            if isinstance(actual_intents[0], dict):
                actual_intents = [intent.get("intent") for intent in actual_intents]

        # Get expected intents
        expected_intents = example.outputs.get("intents", [])

        # Calculate accuracy
        if not expected_intents:
            return {"key": "intent_accuracy", "score": 1.0, "comment": "No expected intents"}

        # Check if all expected intents are present (order doesn't matter)
        correct = set(actual_intents) == set(expected_intents)
        score = 1.0 if correct else 0.0

        comment = f"Expected: {expected_intents}, Got: {actual_intents}"

        return {
            "key": "intent_accuracy",
            "score": score,
            "comment": comment,
        }

    except Exception as e:
        return {
            "key": "intent_accuracy",
            "score": 0.0,
            "comment": f"Error: {str(e)}",
        }


def symbol_extraction_evaluator(run: Run, example: Example) -> dict:
    """
    Evaluator for symbol extraction accuracy.

    Checks if the agent correctly extracted stock symbols from the query.
    """
    try:
        # Extract actual symbols
        actual_symbols = run.outputs.get("symbols", [])

        # Get expected symbols
        expected_symbols = example.outputs.get("symbols", [])

        # Calculate accuracy
        if not expected_symbols:
            return {"key": "symbol_accuracy", "score": 1.0, "comment": "No symbols expected"}

        # Check if all expected symbols are present (case insensitive)
        actual_upper = [s.upper() for s in actual_symbols]
        expected_upper = [s.upper() for s in expected_symbols]

        correct = set(actual_upper) == set(expected_upper)
        score = 1.0 if correct else 0.0

        comment = f"Expected: {expected_symbols}, Got: {actual_symbols}"

        return {
            "key": "symbol_accuracy",
            "score": score,
            "comment": comment,
        }

    except Exception as e:
        return {
            "key": "symbol_accuracy",
            "score": 0.0,
            "comment": f"Error: {str(e)}",
        }


def tool_selection_evaluator(run: Run, example: Example) -> dict:
    """
    Evaluator for tool selection accuracy.

    Checks if the agent selected appropriate tools for the task.
    """
    try:
        # Extract actual tools
        actual_tools = run.outputs.get("selected_tools", [])

        # Get expected tools
        expected_tools = example.outputs.get("tools", [])

        # Calculate accuracy
        if not expected_tools:
            return {"key": "tool_accuracy", "score": 1.0, "comment": "No tools expected"}

        # Check if all expected tools are present (order doesn't matter)
        correct = set(actual_tools) >= set(expected_tools)  # Actual can have more
        score = 1.0 if correct else 0.0

        comment = f"Expected (at least): {expected_tools}, Got: {actual_tools}"

        return {
            "key": "tool_accuracy",
            "score": score,
            "comment": comment,
        }

    except Exception as e:
        return {
            "key": "tool_accuracy",
            "score": 0.0,
            "comment": f"Error: {str(e)}",
        }


def response_quality_evaluator(run: Run, example: Example) -> dict:
    """
    Evaluator for response quality.

    Checks if the agent provided appropriate data in the response.
    """
    try:
        # Check if response has required data
        has_price_data = len(run.outputs.get("market_data", [])) > 0
        has_news_data = len(run.outputs.get("news_data", [])) > 0
        has_summary = bool(run.outputs.get("summary", "").strip())

        # Get expected data presence
        expected_price = example.outputs.get("has_price_data", False)
        expected_news = example.outputs.get("has_news_data", False)

        # Calculate score
        score = 0.0
        issues = []

        # Check summary exists
        if has_summary:
            score += 0.4
        else:
            issues.append("No summary generated")

        # Check price data if expected
        if expected_price:
            if has_price_data:
                score += 0.3
            else:
                issues.append("Missing expected price data")
        else:
            score += 0.3  # Not expected, so no penalty

        # Check news data if expected
        if expected_news:
            if has_news_data:
                score += 0.3
            else:
                issues.append("Missing expected news data")
        else:
            score += 0.3  # Not expected, so no penalty

        comment = f"Issues: {', '.join(issues)}" if issues else "All expected data present"

        return {
            "key": "response_quality",
            "score": score,
            "comment": comment,
        }

    except Exception as e:
        return {
            "key": "response_quality",
            "score": 0.0,
            "comment": f"Error: {str(e)}",
        }


def latency_evaluator(run: Run, example: Example) -> dict:
    """
    Evaluator for response latency.

    Checks if the agent responded within acceptable time.
    """
    try:
        # Get latency from run metadata
        latency = run.end_time - run.start_time if run.end_time and run.start_time else None

        if not latency:
            return {"key": "latency", "score": 0.0, "comment": "No timing data"}

        latency_seconds = latency.total_seconds()

        # Score based on latency (5s excellent, 10s good, 20s acceptable, >20s poor)
        if latency_seconds < 5:
            score = 1.0
        elif latency_seconds < 10:
            score = 0.8
        elif latency_seconds < 20:
            score = 0.6
        else:
            score = 0.4

        comment = f"Latency: {latency_seconds:.2f}s"

        return {
            "key": "latency",
            "score": score,
            "comment": comment,
        }

    except Exception as e:
        return {
            "key": "latency",
            "score": 0.0,
            "comment": f"Error: {str(e)}",
        }


# ====== AGENT WRAPPER FOR EVALUATION ======


async def run_agent_for_eval(inputs: dict) -> dict:
    """
    Wrapper function to run agent and format output for evaluation.

    Args:
        inputs: Dict with 'query' key

    Returns:
        Dict with agent outputs formatted for evaluation
    """
    query = inputs["query"]
    chat_history = inputs.get("chat_history", [])

    # Log the question
    logger.info(f"\n{'='*80}")
    logger.info(f"📝 QUESTION: {query}")
    if chat_history:
        logger.info(f"📜 Chat History: {len(chat_history)} messages")
    logger.info(f"{'='*80}")

    # Run agent
    result = await run_market_agent(
        query=query,
        chat_history=chat_history,
        output_mode="text",  # Use text mode for evaluation
    )

    # Log the response
    logger.info(f"\n{'='*80}")
    logger.info(f"✅ RESPONSE:")
    logger.info(f"   Intents: {[intent.intent for intent in result.intents]}")
    logger.info(f"   Symbols: {result.symbols}")
    logger.info(f"   Tools: {result.selected_tools}")
    logger.info(f"   Summary: {result.summary[:200]}..." if len(result.summary) > 200 else f"   Summary: {result.summary}")
    logger.info(f"{'='*80}\n")

    # Format output for evaluation
    return {
        "query": query,
        "intents": [intent.intent for intent in result.intents],
        "symbols": result.symbols,
        "selected_tools": result.selected_tools,
        "selected_apis": result.selected_apis,
        "market_data": result.market_data,
        "news_data": result.news_data,
        "summary": result.summary,
        "memory_id": result.memory_id,
    }


# ====== DATASET CREATION ======


def create_langsmith_dataset(dataset_name: str = "market-agent-eval"):
    """
    Create or update evaluation dataset in LangSmith.

    Args:
        dataset_name: Name of the dataset
    """
    logger.info(f"Creating dataset: {dataset_name}")

    # Check if dataset exists
    try:
        existing_dataset = client.read_dataset(dataset_name=dataset_name)
        logger.info(f"Dataset {dataset_name} already exists. Deleting...")
        client.delete_dataset(dataset_id=existing_dataset.id)
    except Exception:
        pass

    # Create new dataset
    dataset = client.create_dataset(
        dataset_name=dataset_name,
        description="Evaluation dataset for Market Assistant Agent",
    )

    # Add examples
    for example in EVALUATION_DATASET:
        client.create_example(
            inputs={"query": example["input"]},
            outputs=example["expected_output"],
            metadata=example["metadata"],
            dataset_id=dataset.id,
        )

    logger.info(f"✅ Created dataset with {len(EVALUATION_DATASET)} examples")
    return dataset


def create_conversation_dataset(dataset_name: str = "market-agent-conversation-eval"):
    """
    Create evaluation dataset for multi-turn conversations.

    Args:
        dataset_name: Name of the dataset
    """
    logger.info(f"Creating conversation dataset: {dataset_name}")

    # Check if dataset exists
    try:
        existing_dataset = client.read_dataset(dataset_name=dataset_name)
        logger.info(f"Dataset {dataset_name} already exists. Deleting...")
        client.delete_dataset(dataset_id=existing_dataset.id)
    except Exception:
        pass

    # Create new dataset
    dataset = client.create_dataset(
        dataset_name=dataset_name,
        description="Multi-turn conversation evaluation dataset",
    )

    # Add conversation examples
    for conv_example in CONVERSATION_DATASET:
        # For multi-turn, we'll create examples for each turn
        for i, turn in enumerate(conv_example["turns"]):
            # Build chat history from previous turns
            chat_history = []
            for j in range(i):
                prev_turn = conv_example["turns"][j]
                chat_history.append(ChatMessage(role="user", content=prev_turn["input"]))
                chat_history.append(ChatMessage(role="assistant", content="<previous response>"))

            # Serialize chat history for storage
            chat_history_dict = [
                {"role": msg.role, "content": msg.content, "timestamp": msg.timestamp}
                for msg in chat_history
            ]

            client.create_example(
                inputs={
                    "query": turn["input"],
                    "chat_history": chat_history_dict,
                },
                outputs=turn["expected_output"],
                metadata={
                    **conv_example["metadata"],
                    "turn": i + 1,
                    "total_turns": len(conv_example["turns"]),
                },
                dataset_id=dataset.id,
            )

    logger.info(f"✅ Created conversation dataset with multi-turn examples")
    return dataset


# ====== RUN EVALUATION ======


async def run_evaluation(dataset_name: str = "market-agent-eval"):
    """
    Run evaluation on the dataset.

    Args:
        dataset_name: Name of the dataset to evaluate
    """
    logger.info(f"Running evaluation on dataset: {dataset_name}")

    # Define evaluators
    evaluators = [
        intent_accuracy_evaluator,
        symbol_extraction_evaluator,
        tool_selection_evaluator,
        response_quality_evaluator,
        latency_evaluator,
    ]

    # Run evaluation (use aevaluate for async functions)
    results = await aevaluate(
        run_agent_for_eval,
        data=dataset_name,
        evaluators=evaluators,
        experiment_prefix=f"market-agent-eval-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        metadata={
            "version": "1.0",
            "agent": "market-assistant",
            "features": [
                "multi-intent",
                "chat-history",
                "pronoun-resolution",
                "parallel-fetching",
            ],
        },
    )

    # Print summary
    logger.info(f"\n{'='*80}")
    logger.info(f"📊 EVALUATION SUMMARY")
    logger.info(f"{'='*80}")
    logger.info(f"Dataset: {dataset_name}")
    logger.info(f"Results available at: https://smith.langchain.com/")
    logger.info(f"{'='*80}\n")

    logger.info("✅ Evaluation complete!")
    return results


# ====== MAIN ======


async def main():
    """Main function to run evaluations."""
    import argparse

    parser = argparse.ArgumentParser(description="LangSmith Evaluator for Market Agent")
    parser.add_argument(
        "--create-dataset",
        action="store_true",
        help="Create evaluation dataset in LangSmith",
    )
    parser.add_argument(
        "--run-eval",
        action="store_true",
        help="Run evaluation on dataset",
    )
    parser.add_argument(
        "--dataset-name",
        default="market-agent-eval",
        help="Name of the dataset",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Create dataset and run evaluation",
    )

    args = parser.parse_args()

    if args.all or args.create_dataset:
        logger.info("Creating datasets...")
        create_langsmith_dataset(args.dataset_name)
        create_conversation_dataset(f"{args.dataset_name}-conversation")

    if args.all or args.run_eval:
        logger.info("Running evaluation...")
        await run_evaluation(args.dataset_name)
        await run_evaluation(f"{args.dataset_name}-conversation")


if __name__ == "__main__":
    asyncio.run(main())
