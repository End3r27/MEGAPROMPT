"""Output formatting utilities with rich support."""

import json
import sys
from typing import Any, Optional

try:
    from rich.console import Console
    from rich.json import JSON
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.progress import (
        BarColumn,
        Progress,
        SpinnerColumn,
        TaskID,
        TextColumn,
        TimeElapsedColumn,
    )
    from rich.table import Table
    from rich.text import Text

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


class OutputFormatter:
    """Formats output with optional rich support."""

    def __init__(self, use_rich: bool = True, force_color: bool = False):
        """Initialize formatter."""
        self.use_rich = use_rich and RICH_AVAILABLE
        if self.use_rich:
            self.console = Console(force_terminal=force_color, file=sys.stdout)
            self.progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeElapsedColumn(),
                console=self.console,
            )
        else:
            self.console = None
            self.progress = None

    def format_json(self, data: Any, indent: int = 2) -> str:
        """Format JSON with syntax highlighting if rich is available."""
        json_str = json.dumps(data, indent=indent, ensure_ascii=False)
        if self.use_rich:
            return str(JSON(json_str))
        return json_str

    def format_markdown(self, text: str) -> str:
        """Format markdown with rich rendering if available."""
        if self.use_rich:
            return str(Markdown(text))
        return text

    def print_json(self, data: Any, indent: int = 2) -> None:
        """Print JSON with syntax highlighting."""
        if self.use_rich:
            self.console.print(JSON(json.dumps(data, indent=indent, ensure_ascii=False)))
        else:
            print(json.dumps(data, indent=indent, ensure_ascii=False))

    def print_markdown(self, text: str) -> None:
        """Print markdown with rich rendering."""
        if self.use_rich:
            self.console.print(Markdown(text))
        else:
            print(text)

    def print_stats(self, stats: dict[str, Any]) -> None:
        """Print statistics in a formatted table."""
        if self.use_rich:
            table = Table(title="Generation Statistics", show_header=True, header_style="bold magenta")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")

            for key, value in stats.items():
                table.add_row(key.replace("_", " ").title(), str(value))

            self.console.print(table)
        else:
            print("\nGeneration Statistics:")
            print("-" * 40)
            for key, value in stats.items():
                print(f"{key.replace('_', ' ').title()}: {value}")
            print("-" * 40)

    def print_success(self, message: str) -> None:
        """Print success message."""
        if self.use_rich:
            self.console.print(f"[green]✓[/green] {message}")
        else:
            print(f"✓ {message}")

    def print_error(self, message: str) -> None:
        """Print error message."""
        if self.use_rich:
            self.console.print(f"[red]✗[/red] {message}", file=sys.stderr)
        else:
            print(f"✗ {message}", file=sys.stderr)

    def print_warning(self, message: str) -> None:
        """Print warning message."""
        if self.use_rich:
            self.console.print(f"[yellow]⚠[/yellow] {message}")
        else:
            print(f"⚠ {message}")

    def print_info(self, message: str) -> None:
        """Print info message."""
        if self.use_rich:
            self.console.print(f"[blue]ℹ[/blue] {message}")
        else:
            print(f"ℹ {message}")
    
    def print_stage_header(self, stage_num: int, stage_name: str, description: str = "") -> None:
        """Print a stage header with formatting."""
        if self.use_rich:
            header = f"[bold cyan]Stage {stage_num}: {stage_name}[/bold cyan]"
            if description:
                header += f" - {description}"
            self.console.print(header)
        else:
            header = f"Stage {stage_num}: {stage_name}"
            if description:
                header += f" - {description}"
            print(header)
    
    def print_loading(self, message: str, dots: int = 0) -> None:
        """Print loading message with animated dots."""
        dots_str = "." * (dots % 4)
        if self.use_rich:
            self.console.print(f"[dim]{message}{dots_str}[/dim]", end="\r")
        else:
            print(f"{message}{dots_str}", end="\r", flush=True)
    
    def create_progress_bar(self, description: str, total: int = 100) -> Optional[TaskID]:
        """Create a progress bar and return task ID."""
        if self.use_rich and self.progress:
            if not self.progress.live.is_started:
                self.progress.start()
            return self.progress.add_task(description, total=total)
        return None
    
    def update_progress(self, task_id: TaskID, completed: int, description: Optional[str] = None) -> None:
        """Update progress bar."""
        if self.use_rich and self.progress:
            self.progress.update(task_id, completed=completed, description=description)
    
    def remove_progress(self, task_id: TaskID) -> None:
        """Remove progress bar task."""
        if self.use_rich and self.progress:
            self.progress.remove_task(task_id)
    
    def stop_progress(self) -> None:
        """Stop all progress bars."""
        if self.use_rich and self.progress and self.progress.live.is_started:
            self.progress.stop()


def estimate_tokens(text: str) -> int:
    """Rough token estimation (4 characters ≈ 1 token)."""
    return len(text) // 4


def estimate_cost(tokens: int, provider: str, model: Optional[str] = None) -> Optional[float]:
    """Estimate cost based on provider and model (rough estimates)."""
    # Rough cost estimates per 1K tokens
    cost_estimates = {
        "ollama": 0.0,  # Local, free
        "gemini": {
            "gemini-2.5-flash": 0.0,  # Free tier
            "gemini-3-flash": 0.0,  # Free tier
            "default": 0.0,
        },
        "qwen": {
            "qwen-plus": 0.008,  # ~$0.008 per 1K tokens
            "qwen-turbo": 0.002,
            "qwen-max": 0.02,
            "default": 0.008,
        },
    }

    if provider not in cost_estimates:
        return None

    provider_cost = cost_estimates[provider]
    if isinstance(provider_cost, dict):
        cost_per_1k = provider_cost.get(model, provider_cost.get("default", 0.0))
    else:
        cost_per_1k = provider_cost

    return (tokens / 1000) * cost_per_1k

