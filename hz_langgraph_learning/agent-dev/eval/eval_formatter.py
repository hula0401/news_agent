"""
Evaluation Results Formatter

Pretty-prints evaluation results with questions and responses.

Usage:
    python eval_formatter.py --experiment-id <experiment_id>
    python eval_formatter.py --latest
"""

import argparse
import sys
from datetime import datetime
from langsmith import Client
from typing import List, Dict, Any

client = Client()


def format_chat_history(chat_history: List[Dict]) -> str:
    """Format chat history for display."""
    if not chat_history:
        return "None"

    lines = []
    for msg in chat_history[-3:]:  # Show last 3 messages
        role = msg.get("role", "unknown")
        content = msg.get("content", "")[:80]
        lines.append(f"    {role}: {content}...")

    return "\n".join(lines)


def format_evaluation_result(example_num: int, run: Any, example: Any) -> str:
    """Format a single evaluation result."""
    output = []

    # Header
    output.append("\n" + "="*80)
    output.append(f"TEST CASE #{example_num}")
    output.append("="*80)

    # Question
    query = run.inputs.get("query", "Unknown")
    chat_history = run.inputs.get("chat_history", [])

    output.append(f"\n📝 QUESTION:")
    output.append(f"   {query}")

    if chat_history:
        output.append(f"\n📜 CHAT HISTORY:")
        output.append(format_chat_history(chat_history))

    # Expected vs Actual
    output.append(f"\n🎯 EXPECTED:")
    expected = example.outputs or {}
    output.append(f"   Intents: {expected.get('intents', [])}")
    output.append(f"   Symbols: {expected.get('symbols', [])}")
    output.append(f"   Tools: {expected.get('tools', [])}")

    output.append(f"\n✅ ACTUAL:")
    actual = run.outputs or {}
    output.append(f"   Intents: {actual.get('intents', [])}")
    output.append(f"   Symbols: {actual.get('symbols', [])}")
    output.append(f"   Tools: {actual.get('selected_tools', [])}")

    # Response
    summary = actual.get('summary', '')
    output.append(f"\n💬 RESPONSE:")
    if len(summary) > 200:
        output.append(f"   {summary[:200]}...")
        output.append(f"   (truncated, full length: {len(summary)} chars)")
    else:
        output.append(f"   {summary}")

    # Evaluation scores
    if hasattr(run, 'feedback_stats') and run.feedback_stats:
        output.append(f"\n📊 SCORES:")
        for key, stats in run.feedback_stats.items():
            score = stats.get('avg', 0)
            output.append(f"   {key}: {score:.2f}")

    # Metadata
    output.append(f"\n🔧 METADATA:")
    metadata = example.metadata or {}
    output.append(f"   Category: {metadata.get('category', 'unknown')}")
    output.append(f"   Difficulty: {metadata.get('difficulty', 'unknown')}")

    # Timing
    if run.end_time and run.start_time:
        duration = (run.end_time - run.start_time).total_seconds()
        output.append(f"   Duration: {duration:.2f}s")

    output.append("\n" + "="*80)

    return "\n".join(output)


def get_latest_experiment(dataset_name: str = "market-agent-eval") -> str:
    """Get the ID of the latest experiment for a dataset."""
    dataset = client.read_dataset(dataset_name=dataset_name)

    # List experiments for this dataset
    experiments = list(client.list_projects(
        reference_dataset_id=dataset.id,
    ))

    if not experiments:
        raise ValueError(f"No experiments found for dataset {dataset_name}")

    # Get most recent
    latest = max(experiments, key=lambda x: x.created_at)
    return str(latest.id)


def print_evaluation_results(experiment_id: str):
    """Print formatted evaluation results."""
    # Get experiment runs
    runs = list(client.list_runs(project_id=experiment_id))

    if not runs:
        print(f"No runs found for experiment {experiment_id}")
        return

    # Print header
    print("\n" + "="*80)
    print("🔬 EVALUATION RESULTS")
    print("="*80)
    print(f"Experiment ID: {experiment_id}")
    print(f"Total Test Cases: {len(runs)}")
    print(f"View full results: https://smith.langchain.com/")
    print("="*80)

    # Print each test case
    for i, run in enumerate(runs, 1):
        # Get example
        example = None
        if run.reference_example_id:
            try:
                example = client.read_example(run.reference_example_id)
            except Exception:
                pass

        if example:
            print(format_evaluation_result(i, run, example))
        else:
            print(f"\nTest case #{i}: No example data available")

    # Print summary statistics
    print("\n" + "="*80)
    print("📈 SUMMARY STATISTICS")
    print("="*80)

    # Calculate aggregate scores
    all_scores = {}
    for run in runs:
        if hasattr(run, 'feedback_stats') and run.feedback_stats:
            for key, stats in run.feedback_stats.items():
                if key not in all_scores:
                    all_scores[key] = []
                all_scores[key].append(stats.get('avg', 0))

    if all_scores:
        for key, scores in all_scores.items():
            avg = sum(scores) / len(scores)
            print(f"Average {key}: {avg:.3f}")

    # Timing statistics
    durations = []
    for run in runs:
        if run.end_time and run.start_time:
            duration = (run.end_time - run.start_time).total_seconds()
            durations.append(duration)

    if durations:
        print(f"\nAverage Duration: {sum(durations)/len(durations):.2f}s")
        print(f"Min Duration: {min(durations):.2f}s")
        print(f"Max Duration: {max(durations):.2f}s")

    print("="*80)


def main():
    parser = argparse.ArgumentParser(
        description="Format and display evaluation results"
    )
    parser.add_argument(
        "--experiment-id",
        type=str,
        help="Experiment ID to display",
    )
    parser.add_argument(
        "--latest",
        action="store_true",
        help="Display latest experiment results",
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default="market-agent-eval",
        help="Dataset name (for --latest)",
    )

    args = parser.parse_args()

    if args.latest:
        print(f"Finding latest experiment for dataset: {args.dataset}...")
        try:
            experiment_id = get_latest_experiment(args.dataset)
            print(f"Found: {experiment_id}\n")
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
    elif args.experiment_id:
        experiment_id = args.experiment_id
    else:
        parser.print_help()
        sys.exit(1)

    print_evaluation_results(experiment_id)


if __name__ == "__main__":
    main()
