"""Enhanced progress indicator with animated loading and colored output."""

import sys
import threading
import time
from typing import Optional

try:
    from rich.console import Console
    from rich.live import Live
    from rich.spinner import Spinner
    from rich.text import Text
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskID, TimeElapsedColumn
    
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


class AnimatedProgress:
    """Animated dots spinner for loading indicators."""
    
    def __init__(self, message: str = "Processing", stream=sys.stderr):
        self.message = message
        self.stream = stream
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.dots = 0
        self.max_dots = 3
        self.lock = threading.Lock()
        
    def _animate(self):
        """Animation loop."""
        while self.running:
            with self.lock:
                dots_str = "." * ((self.dots % (self.max_dots + 1)) + 1)
                # Clear line and write
                self.stream.write(f"\r{self.message}{dots_str:<{self.max_dots + 1}}")
                self.stream.flush()
                self.dots = (self.dots + 1) % (self.max_dots + 1)
            time.sleep(0.5)
    
    def start(self):
        """Start the animation."""
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._animate, daemon=True)
        self.thread.start()
    
    def stop(self, final_message: Optional[str] = None):
        """Stop the animation and show final message."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        # Clear the line
        with self.lock:
            self.stream.write("\r" + " " * (len(self.message) + self.max_dots + 5) + "\r")
            if final_message:
                self.stream.write(f"{final_message}\n")
            self.stream.flush()
    
    def is_running(self) -> bool:
        """Check if animation is running."""
        return self.running


class ProgressIndicator:
    """Enhanced progress indicator with animation and colored output."""

    def __init__(self, enabled: bool = True, stream=sys.stderr, use_rich: bool = True):
        """Initialize progress indicator."""
        self.enabled = enabled
        self.stream = stream
        self.use_rich = use_rich and RICH_AVAILABLE
        self.current_stage: Optional[str] = None
        self.animated_progress: Optional[AnimatedProgress] = None
        self._progress_update_thread: Optional[threading.Thread] = None
        self._stop_progress_updates = threading.Event()
        
        if self.use_rich:
            self.console = Console(file=stream, force_terminal=True)
            self.progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeElapsedColumn(),
                console=self.console,
                refresh_per_second=10,
            )
            self.progress_task: Optional[TaskID] = None
            self.live: Optional[Live] = None
        else:
            self.console = None
            self.progress = None
            self.progress_task = None
            self.live = None

    def start_stage(self, stage_name: str, description: str = ""):
        """Start a new stage."""
        if not self.enabled:
            return

        self.current_stage = stage_name
        message = f"Stage {stage_name}: {description}" if description else f"Stage {stage_name}"
        
        if self.use_rich:
            # Start Live context if not already started
            if self.live is None:
                self.live = Live(self.progress, console=self.console, refresh_per_second=10)
                self.live.start()
            
            if self.progress_task is None:
                # First stage - create new task
                self.progress_task = self.progress.add_task(
                    f"[cyan]{message}[/cyan]",
                    total=100,
                )
            else:
                # Subsequent stage - update description but keep current progress
                # Don't reset to 0, continue from where we are
                current_progress = self.progress.tasks[self.progress_task].completed
                self.progress.update(
                    self.progress_task,
                    description=f"[cyan]{message}[/cyan]",
                    # Keep current progress, don't reset
                )
        else:
            # Stop any existing animation
            if self.animated_progress:
                self.animated_progress.stop()
            # Start new animation for this stage
            self.animated_progress = AnimatedProgress(message, self.stream)
            self.animated_progress.start()

    def update(self, message: str, progress: Optional[float] = None):
        """Update progress message."""
        if not self.enabled:
            return

        if self.use_rich:
            if self.progress_task is not None:
                # Stop background progress updates when explicitly updating
                if progress is not None:
                    self.stop_progress_updates()
                    self.progress.update(
                        self.progress_task,
                        description=f"[cyan]{self.current_stage or 'Processing'}:[/cyan] {message}",
                        completed=int(progress * 100),
                    )
                else:
                    # Update description only, don't change progress
                    self.progress.update(
                        self.progress_task,
                        description=f"[cyan]{self.current_stage or 'Processing'}:[/cyan] {message}",
                    )
            else:
                self.console.print(f"  [dim]{message}[/dim]")
        else:
            # Don't stop animation, just update status in a way that doesn't interfere
            if self.current_stage:
                # Write status on new line, keep animation on current line
                self.stream.write(f"\n  {message}\n")
            else:
                self.stream.write(f"{message}\n")
            self.stream.flush()
            # Keep animation running - don't restart it

    def complete_stage(self, message: str = "", progress: float = 1.0):
        """Complete current stage."""
        if not self.enabled:
            return

        # Stop any background progress updates
        self.stop_progress_updates()

        if self.use_rich:
            if self.progress_task is not None:
                if message:
                    self.progress.update(
                        self.progress_task,
                        description=f"[green]✓[/green] {message or 'Complete'}",
                        completed=int(progress * 100),
                    )
                else:
                    self.progress.update(
                        self.progress_task,
                        completed=int(progress * 100),
                    )
        else:
            if self.animated_progress:
                final_msg = f"  ✓ {message}" if message else "  ✓ Complete"
                self.animated_progress.stop(final_msg)
                self.animated_progress = None
        
        self.current_stage = None

    def error(self, message: str):
        """Report an error."""
        if not self.enabled:
            return

        if self.use_rich:
            self.console.print(f"  [red]✗[/red] {message}")
        else:
            if self.animated_progress:
                self.animated_progress.stop()
                self.animated_progress = None
            self.stream.write(f"  ✗ {message}\n")
            self.stream.flush()
    
    def warning(self, message: str):
        """Report a warning."""
        if not self.enabled:
            return
        
        if self.use_rich:
            self.console.print(f"  [yellow]⚠[/yellow] {message}")
        else:
            if self.animated_progress:
                self.animated_progress.stop()
                self.animated_progress = None
            self.stream.write(f"  ⚠ {message}\n")
            self.stream.flush()
    
    def info(self, message: str):
        """Report info message."""
        if not self.enabled:
            return
        
        if self.use_rich:
            self.console.print(f"  [blue]ℹ[/blue] {message}")
        else:
            # Don't stop animation for info messages
            self.stream.write(f"\n  ℹ {message}\n")
            self.stream.flush()
    
    def start_progress_updates(self, start_progress: float = 0.1, end_progress: float = 0.7, duration: float = 60.0):
        """Start background thread to gradually update progress during long operations."""
        if not self.enabled or not self.use_rich or self.progress_task is None:
            return
        
        # Stop any existing progress update thread
        self.stop_progress_updates()
        
        # Reset stop event
        self._stop_progress_updates.clear()
        
        def _update_gradually():
            """Gradually update progress."""
            current = start_progress
            increment = (end_progress - start_progress) / (duration / 1.0)  # Update every 1 second
            last_update = time.time()
            
            while current < end_progress and self.progress_task is not None and not self._stop_progress_updates.is_set():
                time.sleep(0.5)
                now = time.time()
                # Only update every 1 second to avoid oscillation
                if now - last_update >= 1.0:
                    current = min(current + increment, end_progress)
                    if self.progress_task is not None and not self._stop_progress_updates.is_set():
                        # Don't update description, just progress percentage
                        self.progress.update(
                            self.progress_task,
                            completed=int(current * 100),
                        )
                    last_update = now
        
        self._progress_update_thread = threading.Thread(target=_update_gradually, daemon=True)
        self._progress_update_thread.start()
        return self._progress_update_thread
    
    def stop_progress_updates(self):
        """Stop any running progress update thread."""
        if self._progress_update_thread and self._progress_update_thread.is_alive():
            self._stop_progress_updates.set()
            self._progress_update_thread.join(timeout=1.0)
            self._progress_update_thread = None
    
    def finish(self):
        """Finish progress display."""
        # Stop any background progress updates
        self.stop_progress_updates()
        
        if self.use_rich:
            if self.live is not None:
                self.live.stop()
                self.live = None
            if self.progress_task is not None:
                self.progress_task = None
        elif self.animated_progress:
            self.animated_progress.stop()
            self.animated_progress = None
