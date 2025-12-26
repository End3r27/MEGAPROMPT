"""CLI interface for Mega-Prompt Generator."""

import glob
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import click
import yaml

from megaprompt.cli.formatters import OutputFormatter, estimate_cost, estimate_tokens
from megaprompt.cli.interactive import (
    confirm_overwrite,
    interactive_config,
    prompt_missing_config,
)
from megaprompt.core.config import Config
from megaprompt.core.pipeline import MegaPromptPipeline


@click.group()
@click.version_option()
def main():
    """
    Mega-Prompt Generator - Transform messy prompts into structured mega-prompts.
    
    A 5-stage pipeline that progressively refines user prompts into structured,
    deterministic mega-prompts optimized for AI execution.
    
    Supported LLM Providers:
      - Ollama (local, requires running Ollama server)
      - Qwen AI (DashScope API, requires QWEN_API_KEY)
      - Google AI Gemini (free tier, requires GEMINI_API_KEY, auto-opens browser if missing)
    
    Use 'megaprompt generate --help' for detailed usage information.
    """
    pass


@main.command()
@click.argument("input_source", type=click.Path(exists=False))
@click.option(
    "--output",
    "-o",
    type=click.Path(writable=True),
    default=None,
    help="Output file (default: stdout)",
)
@click.option(
    "--provider",
    "-p",
    type=click.Choice(["ollama", "qwen", "gemini", "auto"], case_sensitive=False),
    default="auto",
    help="LLM provider (default: auto - auto-detect)",
)
@click.option(
    "--model",
    "-m",
    default=None,
    help="Model name (provider-specific: Ollama default: llama3.1, Qwen default: qwen-plus, Gemini default: gemini-2.5-flash)",
)
@click.option(
    "--temperature",
    "-t",
    type=float,
    default=0.0,
    help="Temperature for generation (default: 0.0 for determinism)",
)
@click.option(
    "--seed",
    "-s",
    type=int,
    default=None,
    help="Random seed for determinism",
)
@click.option(
    "--verbose/--no-verbose",
    "-v/--no-v",
    default=True,
    help="Show intermediate stage outputs (default: enabled, use --no-verbose to disable)",
)
@click.option(
    "--format",
    "-f",
    "output_format",
    default="markdown",
    help="Output format(s), comma-separated: markdown,json,yaml (default: markdown). Can specify multiple formats.",
)
@click.option(
    "--stats/--no-stats",
    default=True,
    help="Show generation statistics (default: enabled)",
)
@click.option(
    "--color/--no-color",
    default=None,
    help="Force colored output (default: auto-detect)",
)
@click.option(
    "--base-url",
    default=None,
    help="Base URL (provider-specific: Ollama default: http://localhost:11434, Qwen default: DashScope API, not used for Gemini)",
)
@click.option(
    "--api-key",
    default=None,
    help="API key (for Qwen or Gemini provider, or use QWEN_API_KEY/GEMINI_API_KEY env var)",
)
@click.option(
    "--resume/--no-resume",
    default=False,
    help="Resume from last checkpoint if available",
)
@click.option(
    "--checkpoint-dir",
    type=click.Path(),
    default=None,
    help="Directory for checkpoints (default: ~/.megaprompt/checkpoints)",
)
@click.option(
    "--cache-dir",
    type=click.Path(),
    default=None,
    help="Directory for cache (default: ~/.megaprompt/cache)",
)
@click.option(
    "--no-cache",
    is_flag=True,
    default=False,
    help="Disable caching",
)
@click.option(
    "--config",
    type=click.Path(exists=True),
    default=None,
    help="Path to configuration file (YAML or JSON)",
)
@click.option(
    "--batch",
    is_flag=True,
    default=False,
    help="Process multiple input files (use with glob patterns or multiple files)",
)
@click.option(
    "--workers",
    "-w",
    type=int,
    default=None,
    help="Number of parallel workers for batch processing (default: number of CPUs)",
)
@click.option(
    "--output-dir",
    type=click.Path(),
    default=None,
    help="Output directory for batch processing (default: same as input files)",
)
@click.option(
    "--interactive",
    "-i",
    is_flag=True,
    default=False,
    help="Interactive mode: prompt for missing config, confirm stages, preview output",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    default=False,
    help="Skip confirmations in interactive mode",
)
def generate(
    input_source: str,
    output: str | None,
    provider: str,
    model: str | None,
    temperature: float,
    seed: int | None,
    verbose: bool,
    output_format: str,
    base_url: str | None,
    api_key: str | None,
    resume: bool,
    checkpoint_dir: str | None,
    cache_dir: str | None,
    no_cache: bool,
    config: str | None,
    stats: bool,
    color: bool | None,
    batch: bool,
    workers: int | None,
    output_dir: str | None,
    interactive: bool,
    yes: bool,
):
    """
    Generate mega-prompt from input file or stdin.

    Transform messy human prompts into structured, deterministic mega-prompts
    optimized for AI execution through a 5-stage pipeline:
    
    1. Intent Extraction - Removes fluff, extracts core intent
    2. Project Decomposition - Breaks project into orthogonal systems
    3. Domain Expansion - Expands each system with detailed specifications
    4. Risk Analysis - Identifies unknowns and risk points
    5. Constraint Enforcement - Applies technical constraints

    INPUT_SOURCE can be a file path or '-' for stdin.

    Examples:
    
      # Generate from file with auto-detected provider
      megaprompt generate input.txt -o output.md
      
      # Use specific provider
      megaprompt generate input.txt --provider gemini --api-key YOUR_KEY
      
      # Generate from stdin
      echo "Build a todo app" | megaprompt generate - -o output.md
    """
    # Load configuration
    cli_config = {
        "provider": provider,
        "model": model,
        "temperature": temperature,
        "seed": seed,
        "base_url": base_url,
        "api_key": api_key,
        "verbose": verbose,
        "output_format": output_format,
        "checkpoint_dir": checkpoint_dir,
        "cache_dir": cache_dir,
    }

    # Remove None values
    cli_config = {k: v for k, v in cli_config.items() if v is not None}

    config_obj = Config.load(cli_config)

    # Override with explicit config file if provided
    if config:
        config_path = Path(config)
        if config_path.exists():
            config_obj._load_file(config_path, config_obj)

    # Handle batch processing
    if batch or "*" in input_source or "?" in input_source:
        _process_batch(
            input_source,
            output_dir,
            workers,
            config_obj,
            checkpoint_path,
            cache_path,
            no_cache,
            resume,
            output_format,
            stats,
            color,
            verbose,
        )
        return

    # Interactive mode: prompt for missing configuration
    if interactive:
        config_obj = interactive_config(config_obj, skip_confirmations=yes)
    else:
        # Still prompt for critical missing config
        config_obj = prompt_missing_config(config_obj)

    # Read input
    if input_source == "-":
        user_prompt = sys.stdin.read()
    else:
        input_path = Path(input_source)
        if not input_path.exists():
            click.echo(f"Error: Input file not found: {input_source}", err=True)
            click.echo(f"  Current directory: {Path.cwd()}", err=True)
            click.echo(f"  Tip: Use absolute path or check file exists", err=True)
            sys.exit(1)
        user_prompt = input_path.read_text(encoding="utf-8")

    if not user_prompt.strip():
        click.echo("Error: Input is empty", err=True)
        click.echo("  Tip: Check that the file contains text or stdin has data", err=True)
        sys.exit(1)

    # Setup checkpoint and cache directories
    checkpoint_path = None
    if resume or checkpoint_dir:
        if checkpoint_dir:
            checkpoint_path = Path(checkpoint_dir)
        else:
            checkpoint_path = config_obj.get_checkpoint_dir()

    cache_path = None
    if not no_cache:
        if cache_dir:
            cache_path = Path(cache_dir)
        else:
            cache_path = config_obj.get_cache_dir()

    # Initialize pipeline
    try:
        pipeline = MegaPromptPipeline(
            provider=config_obj.provider,
            base_url=config_obj.base_url,
            model=config_obj.model,
            temperature=config_obj.temperature,
            seed=config_obj.seed,
            api_key=config_obj.api_key,
            checkpoint_dir=checkpoint_path,
            cache_dir=cache_path,
            use_cache=not no_cache,
        )
    except Exception as e:
        click.echo(f"Error initializing pipeline: {e}", err=True)
        click.echo(f"\nTroubleshooting:", err=True)
        click.echo(f"  - Provider: {config_obj.provider}", err=True)
        if config_obj.provider == "ollama":
            click.echo(f"  - Check that Ollama is running at {config_obj.base_url or 'http://localhost:11434'}", err=True)
            click.echo(f"  - Verify model is available: ollama list", err=True)
        elif config_obj.provider in ["qwen", "gemini"]:
            click.echo(f"  - Check API key is set correctly", err=True)
            click.echo(f"  - Verify network connection", err=True)
        sys.exit(1)

    # Initialize formatter
    formatter = OutputFormatter(use_rich=True, force_color=color if color is not None else False)

    # Interactive mode: confirm before proceeding
    if interactive and not yes:
        if not click.confirm("Proceed with generation?", default=True):
            click.echo("Generation cancelled.")
            sys.exit(0)

    # Generate mega-prompt
    start_time = time.time()
    try:
        mega_prompt_text, intermediate_outputs = pipeline.generate(
            user_prompt, verbose=config_obj.verbose, resume=resume
        )
        elapsed_time = time.time() - start_time

        # Calculate statistics
        total_tokens = estimate_tokens(user_prompt + mega_prompt_text)
        estimated_cost = estimate_cost(total_tokens, config_obj.provider, config_obj.model)

        stats_data = {
            "time_taken": f"{elapsed_time:.2f}s",
            "input_tokens": estimate_tokens(user_prompt),
            "output_tokens": estimate_tokens(mega_prompt_text),
            "total_tokens": total_tokens,
            "provider": config_obj.provider,
            "model": config_obj.model or "default",
        }
        if estimated_cost is not None:
            stats_data["estimated_cost"] = f"${estimated_cost:.4f}"

        # Parse output formats (support multiple)
        formats = [f.strip().lower() for f in output_format.split(",")]
        if not formats:
            formats = ["markdown"]

        # Prepare output data
        output_data = {"mega_prompt": mega_prompt_text}
        if config_obj.verbose:
            output_data["intermediate"] = intermediate_outputs

        # Write outputs in requested formats
        output_paths = []
        for idx, fmt in enumerate(formats):
            if fmt == "json":
                output_text = formatter.format_json(output_data)
            elif fmt == "yaml":
                output_text = yaml.dump(output_data, default_flow_style=False, sort_keys=False)
            else:  # markdown (default)
                output_text = mega_prompt_text
                if config_obj.verbose:
                    output_text += "\n\n---\n\n# Intermediate Outputs\n\n"
                    output_text += f"```json\n{json.dumps(intermediate_outputs, indent=2)}\n```"

            # Determine output file
            if output:
                output_path = Path(output)
                # If multiple formats, append extension
                if len(formats) > 1:
                    if fmt == "json":
                        output_path = output_path.with_suffix(".json")
                    elif fmt == "yaml":
                        output_path = output_path.with_suffix(".yaml")
                    else:
                        output_path = output_path.with_suffix(".md")
                else:
                    # Single format - use original extension or add appropriate one
                    if fmt == "json" and not output_path.suffix == ".json":
                        output_path = output_path.with_suffix(".json")
                    elif fmt == "yaml" and not output_path.suffix in [".yaml", ".yml"]:
                        output_path = output_path.with_suffix(".yaml")
                    elif fmt == "markdown" and not output_path.suffix == ".md":
                        output_path = output_path.with_suffix(".md")
                
                output_path.write_text(output_text, encoding="utf-8")
                output_paths.append(output_path)
            else:
                # Only print first format to stdout
                if idx == 0:
                    if fmt == "markdown":
                        formatter.print_markdown(output_text)
                    elif fmt == "json":
                        formatter.print_json(output_data)
                    else:
                        click.echo(output_text)

        # Show statistics
        if stats:
            formatter.print_stats(stats_data)

        # Interactive mode: preview before saving
        if interactive and not yes and output:
            formatter.print_info("Preview of generated mega-prompt:")
            formatter.print_markdown(mega_prompt_text[:500] + "..." if len(mega_prompt_text) > 500 else mega_prompt_text)
            if not click.confirm("Save output?", default=True):
                click.echo("Output not saved.")
                return

        # Show output paths
        if output_paths:
            if config_obj.verbose:
                formatter.print_success(f"Output written to {len(output_paths)} file(s):")
                for path in output_paths:
                    click.echo(f"  - {path}")

    except Exception as e:
        error_msg = str(e)
        click.echo(f"Error generating mega-prompt: {error_msg}", err=True)

        # Provide helpful context
        if "Validation failed" in error_msg:
            click.echo("\nThis is a validation error. The LLM response didn't match the expected schema.", err=True)
            click.echo("Common solutions:", err=True)
            click.echo("  - Try running again (LLM responses can vary)", err=True)
            click.echo("  - Try a different model or provider", err=True)
            click.echo("  - Check the error details above for specific field issues", err=True)
        elif "not found" in error_msg.lower() or "404" in error_msg:
            click.echo("\nModel or resource not found.", err=True)
            click.echo("Common solutions:", err=True)
            if config_obj.provider == "ollama":
                click.echo("  - Run: ollama pull <model-name>", err=True)
                click.echo("  - Check available models: ollama list", err=True)
            else:
                click.echo("  - Verify the model name is correct", err=True)
                click.echo("  - Check provider documentation for available models", err=True)
        elif "api" in error_msg.lower() or "key" in error_msg.lower():
            click.echo("\nAPI authentication issue.", err=True)
            click.echo("Common solutions:", err=True)
            click.echo("  - Verify API key is set correctly", err=True)
            click.echo("  - Check API key has required permissions", err=True)
            click.echo("  - Verify network connection", err=True)

        if config_obj.verbose:
            import traceback
            click.echo("\nFull traceback:", err=True)
            click.echo(traceback.format_exc(), err=True)

        sys.exit(1)


@main.group()
def config():
    """Configuration management commands."""
    pass


@config.command("export")
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=None,
    help="Output file path (default: stdout)",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["yaml", "json"], case_sensitive=False),
    default="yaml",
    help="Output format (default: yaml)",
)
def config_export(output: str | None, format: str):
    """Export current configuration to file."""
    config_obj = Config.load()

    if output:
        output_path = Path(output)
        config_obj.save(output_path, format=format)
        click.echo(f"Configuration exported to: {output_path}")
    else:
        if format == "yaml":
            content = yaml.dump(config_obj.to_dict(), default_flow_style=False, sort_keys=False)
        else:
            content = json.dumps(config_obj.to_dict(), indent=2)
        click.echo(content)


@config.command("import")
@click.argument("config_file", type=click.Path(exists=True))
def config_import(config_file: str):
    """Import configuration from file."""
    config_path = Path(config_file)
    config_obj = Config()
    config_obj._load_file(config_path, config_obj)

    # Save to user config
    user_config_path = Path.home() / ".megaprompt" / "config.yaml"
    config_obj.save(user_config_path, format="yaml")
    click.echo(f"Configuration imported and saved to: {user_config_path}")


# _interactive_config is now imported from megaprompt.cli.interactive


def _process_single_file(
    input_file: Path,
    output_dir: Path | None,
    config_obj: Config,
    checkpoint_path: Path | None,
    cache_path: Path | None,
    no_cache: bool,
    resume: bool,
    output_format: str,
    stats: bool,
    color: bool | None,
    verbose: bool,
) -> dict[str, Any]:
    """Process a single file in batch mode."""
    try:
        user_prompt = input_file.read_text(encoding="utf-8")
        if not user_prompt.strip():
            return {"file": str(input_file), "status": "skipped", "error": "Empty file"}

        # Setup pipeline
        pipeline = MegaPromptPipeline(
            provider=config_obj.provider,
            base_url=config_obj.base_url,
            model=config_obj.model,
            temperature=config_obj.temperature,
            seed=config_obj.seed,
            api_key=config_obj.api_key,
            checkpoint_dir=checkpoint_path,
            cache_dir=cache_path,
            use_cache=not no_cache,
        )

        # Generate
        start_time = time.time()
        mega_prompt_text, intermediate_outputs = pipeline.generate(
            user_prompt, verbose=False, resume=resume
        )
        elapsed_time = time.time() - start_time

        # Determine output path
        if output_dir:
            output_path = output_dir / f"{input_file.stem}_output.md"
        else:
            output_path = input_file.parent / f"{input_file.stem}_output.md"

        # Write output
        formats = [f.strip().lower() for f in output_format.split(",")]
        for fmt in formats:
            if fmt == "json":
                output_data = {"mega_prompt": mega_prompt_text, "intermediate": intermediate_outputs}
                output_path = output_path.with_suffix(".json")
                output_path.write_text(json.dumps(output_data, indent=2), encoding="utf-8")
            elif fmt == "yaml":
                output_data = {"mega_prompt": mega_prompt_text, "intermediate": intermediate_outputs}
                output_path = output_path.with_suffix(".yaml")
                output_path.write_text(yaml.dump(output_data, default_flow_style=False), encoding="utf-8")
            else:
                output_path = output_path.with_suffix(".md")
                output_path.write_text(mega_prompt_text, encoding="utf-8")

        return {
            "file": str(input_file),
            "status": "success",
            "output": str(output_path),
            "time": f"{elapsed_time:.2f}s",
        }
    except Exception as e:
        return {"file": str(input_file), "status": "error", "error": str(e)}


def _process_batch(
    input_pattern: str,
    output_dir: str | None,
    workers: int | None,
    config_obj: Config,
    checkpoint_path: Path | None,
    cache_path: Path | None,
    no_cache: bool,
    resume: bool,
    output_format: str,
    stats: bool,
    color: bool | None,
    verbose: bool,
) -> None:
    """Process multiple files in batch mode."""
    formatter = OutputFormatter(use_rich=True, force_color=color if color is not None else False)

    # Find input files
    if input_pattern == "-":
        click.echo("Error: Batch mode requires file patterns, not stdin", err=True)
        sys.exit(1)

    # Expand glob pattern
    input_files = [Path(f) for f in glob.glob(input_pattern) if Path(f).is_file()]
    if not input_files:
        click.echo(f"Error: No files found matching pattern: {input_pattern}", err=True)
        sys.exit(1)

    formatter.print_info(f"Found {len(input_files)} file(s) to process")

    # Setup output directory
    output_path = Path(output_dir) if output_dir else None
    if output_path:
        output_path.mkdir(parents=True, exist_ok=True)

    # Determine number of workers
    num_workers = workers or os.cpu_count() or 1

    # Process files in parallel
    results = []
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = {
            executor.submit(
                _process_single_file,
                input_file,
                output_path,
                config_obj,
                checkpoint_path,
                cache_path,
                no_cache,
                resume,
                output_format,
                stats,
                color,
                verbose,
            ): input_file
            for input_file in input_files
        }

        completed = 0
        for future in as_completed(futures):
            completed += 1
            result = future.result()
            results.append(result)
            if verbose:
                status_icon = "✓" if result["status"] == "success" else "✗"
                formatter.print_info(f"[{completed}/{len(input_files)}] {status_icon} {Path(result['file']).name}")

    # Generate summary report
    successful = [r for r in results if r["status"] == "success"]
    failed = [r for r in results if r["status"] == "error"]
    skipped = [r for r in results if r["status"] == "skipped"]

    formatter.print_success(f"\nBatch processing complete:")
    formatter.print_info(f"  Successful: {len(successful)}")
    if failed:
        formatter.print_error(f"  Failed: {len(failed)}")
    if skipped:
        formatter.print_warning(f"  Skipped: {len(skipped)}")

    if failed and verbose:
        formatter.print_error("\nFailed files:")
        for result in failed:
            formatter.print_error(f"  - {Path(result['file']).name}: {result.get('error', 'Unknown error')}")


@main.command()
def ui():
    """
    Launch interactive desktop GUI.
    
    Opens a user-friendly desktop application with access to all MEGAPROMPT functions.
    Features a black OLED theme with smooth rounded corners and system tray support.
    
    The GUI provides:
      - Generate mega-prompts with full configuration options
      - Batch processing for multiple files
      - Configuration management
      - Checkpoint viewing and management
      - Cache statistics and management
      - Help and documentation
    """
    try:
        from megaprompt.cli.gui_app import run_gui
        run_gui()
    except ImportError as e:
        click.echo(
            "Error: CustomTkinter is required for UI mode. Install it with:\n"
            "  pip install 'megaprompt[ui]'",
            err=True
        )
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error launching UI: {e}", err=True)
        if "--verbose" in sys.argv or "-v" in sys.argv:
            import traceback
            click.echo(traceback.format_exc(), err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

