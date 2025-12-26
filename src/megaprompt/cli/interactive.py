"""Interactive CLI prompts and confirmations."""

import os
import sys
from typing import Optional

import click

from megaprompt.core.config import Config


def prompt_provider(default: str = "auto") -> str:
    """Prompt for LLM provider with validation."""
    while True:
        provider = click.prompt(
            "LLM Provider",
            type=click.Choice(["auto", "ollama", "qwen", "gemini"], case_sensitive=False),
            default=default,
            show_choices=True,
        )
        if provider:
            return provider.lower()
        click.echo("Please select a valid provider.", err=True)


def prompt_model(provider: str, default: Optional[str] = None) -> Optional[str]:
    """Prompt for model name with suggestions."""
    suggestions = {
        "ollama": ["llama3.1", "llama3", "mistral", "codellama"],
        "qwen": ["qwen-plus", "qwen-turbo", "qwen-max"],
        "gemini": ["gemini-2.5-flash", "gemini-3-flash", "gemini-pro"],
    }
    
    suggestion_list = suggestions.get(provider, [])
    if suggestion_list:
        click.echo(f"  Suggested models: {', '.join(suggestion_list)}")
    
    model = click.prompt(
        "Model name",
        default=default or "",
        show_default=bool(default),
    )
    return model.strip() or None


def prompt_api_key(provider: str, env_var: Optional[str] = None) -> Optional[str]:
    """Prompt for API key with masking."""
    if env_var and os.getenv(env_var):
        click.echo(f"  Using API key from {env_var} environment variable")
        if click.confirm("  Use different API key?", default=False):
            return click.prompt("API Key", hide_input=True, confirmation_prompt=True)
        return None
    
    click.echo(f"  API key not found in environment variables")
    if click.confirm("  Enter API key now?", default=True):
        return click.prompt("API Key", hide_input=True, confirmation_prompt=True)
    return None


def prompt_temperature(default: float = 0.0) -> float:
    """Prompt for temperature with validation."""
    while True:
        try:
            temp = click.prompt(
                "Temperature",
                type=float,
                default=default,
                show_default=True,
            )
            if 0.0 <= temp <= 2.0:
                return temp
            click.echo("Temperature must be between 0.0 and 2.0", err=True)
        except click.Abort:
            raise
        except Exception:
            click.echo("Invalid temperature value. Please enter a number.", err=True)


def prompt_output_format(default: str = "markdown") -> str:
    """Prompt for output format."""
    return click.prompt(
        "Output format",
        type=click.Choice(["markdown", "json", "yaml"], case_sensitive=False),
        default=default,
        show_choices=True,
    )


def prompt_output_file(default: Optional[str] = None) -> Optional[str]:
    """Prompt for output file path."""
    output = click.prompt(
        "Output file (leave empty for stdout)",
        default=default or "",
        show_default=False,
    )
    return output.strip() or None


def confirm_overwrite(filepath: str) -> bool:
    """Confirm before overwriting an existing file."""
    if not os.path.exists(filepath):
        return True
    
    return click.confirm(
        f"File '{filepath}' already exists. Overwrite?",
        default=False,
    )


def confirm_action(message: str, default: bool = False) -> bool:
    """Generic confirmation prompt."""
    return click.confirm(message, default=default)


def interactive_config(config: Config, skip_confirmations: bool = False) -> Config:
    """
    Interactively configure missing settings.
    
    Args:
        config: Base configuration object
        skip_confirmations: If True, skip confirmation prompts
    
    Returns:
        Updated configuration object
    """
    try:
        from rich.console import Console
        console = Console()
        console.print("\n[bold cyan]Interactive Configuration[/bold cyan]")
        console.print("=" * 50)
    except ImportError:
        click.echo("\nInteractive Configuration")
        click.echo("=" * 50)
    
    # Provider
    if not config.provider or config.provider == "auto":
        if not skip_confirmations:
            config.provider = prompt_provider(config.provider or "auto")
        else:
            config.provider = config.provider or "auto"
    
    # Model
    if not config.model:
        if not skip_confirmations:
            config.model = prompt_model(config.provider)
    
    # API Key (if needed)
    if config.provider in ["qwen", "gemini"]:
        env_vars = {
            "qwen": "QWEN_API_KEY",
            "gemini": "GEMINI_API_KEY",
        }
        env_var = env_vars.get(config.provider)
        if not config.api_key and not skip_confirmations:
            config.api_key = prompt_api_key(config.provider, env_var)
    
    # Temperature
    if config.temperature == 0.0 and not skip_confirmations:
        if click.confirm("  Use custom temperature?", default=False):
            config.temperature = prompt_temperature(config.temperature)
    
    # Output format
    if not skip_confirmations:
        if click.confirm("  Customize output format?", default=False):
            config.output_format = prompt_output_format(config.output_format)
    
    try:
        from rich.console import Console
        console = Console()
        console.print("\n[green]✓[/green] Configuration complete!")
    except ImportError:
        click.echo("\n✓ Configuration complete!")
    return config


def prompt_missing_config(config: Config) -> Config:
    """Prompt for missing critical configuration."""
    missing = []
    
    if config.provider in ["qwen", "gemini"] and not config.api_key:
        env_vars = {
            "qwen": "QWEN_API_KEY",
            "gemini": "GEMINI_API_KEY",
        }
        env_var = env_vars.get(config.provider)
        if not os.getenv(env_var):
            missing.append(f"API key for {config.provider}")
    
    if missing:
        click.echo("\n[yellow]⚠[/yellow] Missing configuration:")
        for item in missing:
            click.echo(f"  - {item}")
        
        if click.confirm("\nConfigure now?", default=True):
            return interactive_config(config, skip_confirmations=False)
    
    return config

