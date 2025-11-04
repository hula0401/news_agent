#!/usr/bin/env python3
"""
Interactive CLI Chat Interface for Market Assistant Agent

Features:
- Multi-turn conversations with context
- Clear LLM input/output logging
- Conversation history tracking
- Exit with Ctrl+C or 'exit'/'quit'
- Optional debug mode for detailed logs

Usage:
    python chat.py                    # Normal mode
    python chat.py --debug            # Debug mode with LLM logs
    python chat.py --voice            # Voice mode (oral responses)
    python chat.py --save-history     # Save conversation to file
"""

import asyncio
import argparse
import logging
import sys
import signal
from datetime import datetime
from typing import List, Optional
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.live import Live
from rich.spinner import Spinner
from rich import box

from agent_core.graph import run_market_agent
from agent_core.state import ChatMessage
from agent_core.logging_config import start_new_chat_session, get_chat_log_path

load_dotenv()

# Rich console for pretty output
console = Console()

# Global conversation state
conversation_history: List[ChatMessage] = []
thread_id: str = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
message_count = 0
chat_session_id: Optional[str] = None


class LLMLogger:
    """Custom logger to capture and display LLM interactions."""

    def __init__(self, debug: bool = False):
        self.debug = debug
        self.llm_calls = []

    def log_llm_input(self, prompt: str, system: Optional[str] = None):
        """Log LLM input."""
        if self.debug:
            console.print("\n" + "─" * 80, style="dim")
            console.print("🔵 [bold cyan]LLM INPUT:[/bold cyan]")

            if system:
                console.print("\n[yellow]System Prompt:[/yellow]")
                console.print(Panel(
                    system[:500] + "..." if len(system) > 500 else system,
                    border_style="yellow",
                    box=box.ROUNDED
                ))

            console.print("\n[yellow]User Prompt:[/yellow]")
            console.print(Panel(
                prompt[:800] + "..." if len(prompt) > 800 else prompt,
                border_style="yellow",
                box=box.ROUNDED
            ))
            console.print("─" * 80 + "\n", style="dim")

    def log_llm_output(self, response: str):
        """Log LLM output."""
        if self.debug:
            console.print("\n" + "─" * 80, style="dim")
            console.print("🟢 [bold green]LLM OUTPUT:[/bold green]")
            console.print(Panel(
                response[:800] + "..." if len(response) > 800 else response,
                border_style="green",
                box=box.ROUNDED
            ))
            console.print("─" * 80 + "\n", style="dim")


# Global logger
llm_logger: Optional[LLMLogger] = None


def setup_logging(debug: bool = False):
    """Set up logging configuration."""
    global llm_logger
    llm_logger = LLMLogger(debug=debug)

    if debug:
        # In debug mode, write logs to a file instead of stdout to avoid interfering with user input
        import os
        log_dir = os.path.join(os.path.dirname(__file__), "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "chat_debug.log")

        # Configure root logger to write to file
        logging.basicConfig(
            level=logging.INFO,  # Only INFO and above to reduce noise
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            filename=log_file,
            filemode='a'
        )

        # Suppress noisy loggers
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("langsmith").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)

        console.print(f"[dim]Debug logs: {log_file}[/dim]\n")
    else:
        # Suppress most logs except errors
        logging.basicConfig(
            level=logging.WARNING,
            format='%(levelname)s: %(message)s'
        )


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    console.print("\n\n[yellow]Goodbye! 👋[/yellow]")
    sys.exit(0)


def print_welcome():
    """Print welcome message."""
    welcome_text = Text()
    welcome_text.append("Market Assistant Agent\n", style="bold cyan")
    welcome_text.append("Interactive Chat Mode\n\n", style="cyan")
    welcome_text.append("Commands:\n", style="yellow")
    welcome_text.append("  • Type your question and press Enter\n", style="dim")
    welcome_text.append("  • Type 'exit' or 'quit' to end\n", style="dim")
    welcome_text.append("  • Press Ctrl+C to interrupt\n", style="dim")
    welcome_text.append("  • Type 'history' to view conversation\n", style="dim")
    welcome_text.append("  • Type 'clear' to reset conversation\n\n", style="dim")
    welcome_text.append("Examples:\n", style="yellow")
    welcome_text.append("  • What's the price of TSLA?\n", style="dim")
    welcome_text.append("  • What happened to it?\n", style="dim")
    welcome_text.append("  • Compare NVDA and AMD\n", style="dim")

    console.print(Panel(
        welcome_text,
        title="🤖 Welcome",
        border_style="cyan",
        box=box.DOUBLE
    ))


def print_conversation_history():
    """Print conversation history."""
    if not conversation_history:
        console.print("[dim]No conversation history yet[/dim]")
        return

    table = Table(title="Conversation History", box=box.ROUNDED)
    table.add_column("#", style="cyan", width=4)
    table.add_column("Role", style="yellow", width=10)
    table.add_column("Message", style="white")
    table.add_column("Time", style="dim", width=20)

    for i, msg in enumerate(conversation_history, 1):
        role = "You" if msg.role == "user" else "Agent"
        content = msg.content[:80] + "..." if len(msg.content) > 80 else msg.content
        timestamp = msg.timestamp[:19].replace("T", " ")

        table.add_row(
            str(i),
            role,
            content,
            timestamp
        )

    console.print(table)


def print_session_info():
    """Print session information."""
    info = Table(box=box.SIMPLE)
    info.add_column("Property", style="cyan")
    info.add_column("Value", style="yellow")

    info.add_row("Thread ID", thread_id)
    info.add_row("Messages", str(len(conversation_history)))
    info.add_row("Session Start", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    console.print(Panel(info, title="📊 Session Info", border_style="blue"))


async def process_query(
    query: str,
    output_mode: str = "voice",
    debug: bool = False
) -> str:
    """Process user query and return response."""
    global conversation_history, message_count

    message_count += 1

    # Show processing indicator
    with console.status(
        f"[bold cyan]Processing query {message_count}...[/bold cyan]",
        spinner="dots"
    ):
        try:
            # Run agent
            result = await run_market_agent(
                query=query,
                chat_history=conversation_history,
                thread_id=thread_id,
                output_mode=output_mode,
            )

            # Log debug info
            if debug:
                console.print("\n[bold cyan]🔍 Debug Info:[/bold cyan]")
                debug_table = Table(box=box.ROUNDED)
                debug_table.add_column("Property", style="cyan")
                debug_table.add_column("Value", style="yellow")

                debug_table.add_row("Intents", str([i.intent for i in result.intents]))
                debug_table.add_row("Symbols", str(result.symbols))
                debug_table.add_row("Tools Selected", str(result.selected_tools))
                debug_table.add_row("APIs Used", str(result.selected_apis))
                debug_table.add_row("Market Data", f"{len(result.market_data)} items")
                debug_table.add_row("News Data", f"{len(result.news_data)} items")
                debug_table.add_row("Memory ID", str(result.memory_id))

                console.print(debug_table)

            # Update conversation history
            conversation_history.append(ChatMessage(role="user", content=query))
            conversation_history.append(ChatMessage(role="assistant", content=result.summary))

            return result.summary

        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {str(e)}")
            if debug:
                import traceback
                console.print("[dim]" + traceback.format_exc() + "[/dim]")
            return f"Sorry, I encountered an error: {str(e)}"


def save_conversation_history(filename: Optional[str] = None):
    """Save conversation history to file."""
    if not conversation_history:
        console.print("[yellow]No conversation to save[/yellow]")
        return

    if filename is None:
        filename = f"chat_history_{thread_id}.txt"

    filepath = Path("chat_logs") / filename
    filepath.parent.mkdir(exist_ok=True)

    with open(filepath, "w") as f:
        f.write(f"Market Assistant Chat Log\n")
        f.write(f"Thread ID: {thread_id}\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Messages: {len(conversation_history)}\n")
        f.write("=" * 80 + "\n\n")

        for i, msg in enumerate(conversation_history, 1):
            role = "USER" if msg.role == "user" else "AGENT"
            f.write(f"[{i}] {role} ({msg.timestamp})\n")
            f.write(f"{msg.content}\n")
            f.write("-" * 80 + "\n\n")

    console.print(f"[green]✅ Conversation saved to {filepath}[/green]")


async def interactive_chat(
    output_mode: str = "voice",
    debug: bool = False,
    save_history: bool = False
):
    """Main interactive chat loop."""
    global chat_session_id

    setup_logging(debug=debug)

    # Start new chat session with detailed logging
    chat_session_id = start_new_chat_session()
    log_file = get_chat_log_path()

    print_welcome()

    # Show log file location
    console.print(f"[dim]📝 Detailed logs: {log_file}[/dim]")

    # Register Ctrl+C handler
    signal.signal(signal.SIGINT, signal_handler)

    console.print("[dim]Type your question or 'help' for commands[/dim]\n")

    while True:
        try:
            # Get user input
            user_input = console.input("[bold cyan]You:[/bold cyan] ").strip()

            if not user_input:
                continue

            # Handle commands
            if user_input.lower() in ["exit", "quit", "bye"]:
                if save_history and conversation_history:
                    save_conversation_history()
                console.print("\n[yellow]Goodbye! 👋[/yellow]")
                break

            elif user_input.lower() == "help":
                print_welcome()
                continue

            elif user_input.lower() == "history":
                print_conversation_history()
                continue

            elif user_input.lower() == "clear":
                conversation_history.clear()
                console.print("[green]✅ Conversation history cleared[/green]")
                continue

            elif user_input.lower() == "info":
                print_session_info()
                continue

            elif user_input.lower() == "save":
                save_conversation_history()
                continue

            # Process query
            response = await process_query(user_input, output_mode, debug)

            # Display response
            console.print(f"\n[bold green]Agent:[/bold green]")
            console.print(Panel(
                response,
                border_style="green",
                box=box.ROUNDED
            ))
            console.print()

        except KeyboardInterrupt:
            if save_history and conversation_history:
                save_conversation_history()
            console.print("\n\n[yellow]Goodbye! 👋[/yellow]")
            break

        except EOFError:
            if save_history and conversation_history:
                save_conversation_history()
            console.print("\n[yellow]Goodbye! 👋[/yellow]")
            break

        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {str(e)}")
            if debug:
                import traceback
                console.print("[dim]" + traceback.format_exc() + "[/dim]")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Interactive chat with Market Assistant Agent"
    )
    parser.add_argument(
        "--voice",
        action="store_true",
        help="Use voice mode (oral responses) - default",
    )
    parser.add_argument(
        "--text",
        action="store_true",
        help="Use text mode (structured responses)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode with detailed logs",
    )
    parser.add_argument(
        "--save-history",
        action="store_true",
        help="Save conversation history on exit",
    )

    args = parser.parse_args()

    # Determine output mode
    output_mode = "text" if args.text else "voice"

    # Run chat
    try:
        asyncio.run(interactive_chat(
            output_mode=output_mode,
            debug=args.debug,
            save_history=args.save_history,
        ))
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted[/yellow]")
        sys.exit(0)


if __name__ == "__main__":
    main()
