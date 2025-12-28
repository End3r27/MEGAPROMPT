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
      - OpenRouter (access to many models, requires OPENROUTER_API_KEY)
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
    type=click.Choice(["ollama", "qwen", "gemini", "openrouter", "auto"], case_sensitive=False),
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
@click.option(
    "--augment",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    default=None,
    help="Path to missing systems JSON file to augment the prompt with",
)
@click.option(
    "--from-idea",
    type=int,
    default=None,
    help="Use idea #N from last brainstorm JSON file (use with --idea-file)",
)
@click.option(
    "--idea-file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    default=None,
    help="Path to brainstorm JSON output file (required with --from-idea)",
)
@click.option(
    "--log-level",
    default="INFO",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], case_sensitive=False),
    help="Logging level (default: INFO)",
)
@click.option(
    "--log-file",
    type=click.Path(),
    default=None,
    help="Path to log file (default: stderr)",
)
@click.option(
    "--json-logging",
    is_flag=True,
    default=False,
    help="Output logs in JSON format",
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
    log_level: str,
    log_file: str | None,
    json_logging: bool,
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
    augment: str | None,
    from_idea: int | None,
    idea_file: str | None,
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
    # Configure logging first (before other imports that might log)
    from megaprompt.core.logging import configure_logging
    configure_logging(level=log_level, json_output=json_logging, log_file=log_file)
    
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

    # Handle --from-idea flag
    if from_idea is not None:
        if not idea_file:
            click.echo("Error: --idea-file is required when using --from-idea", err=True)
            sys.exit(1)
        
        idea_path = Path(idea_file)
        if not idea_path.exists():
            click.echo(f"Error: Idea file not found: {idea_file}", err=True)
            sys.exit(1)
        
        try:
            from megaprompt.schemas.brainstorm import BrainstormResult
            
            idea_data = json.loads(idea_path.read_text(encoding="utf-8"))
            brainstorm_result = BrainstormResult.model_validate(idea_data)
            
            if from_idea < 1 or from_idea > len(brainstorm_result.ideas):
                click.echo(f"Error: Idea index {from_idea} out of range (1-{len(brainstorm_result.ideas)})", err=True)
                sys.exit(1)
            
            idea = brainstorm_result.ideas[from_idea - 1]  # Convert to 0-based index
            
            # Convert idea to prompt format
            user_prompt = f"{idea.name}\n\n{idea.tagline}\n\n"
            user_prompt += "Core Loop:\n"
            for step in idea.core_loop:
                user_prompt += f"- {step}\n"
            user_prompt += "\nKey Systems:\n"
            for system in idea.key_systems:
                user_prompt += f"- {system}\n"
            user_prompt += f"\nUnique Twist: {idea.unique_twist}\n"
            user_prompt += f"\nTechnical Challenge: {idea.technical_challenge}\n"
            
            if verbose:
                click.echo(f"Using idea #{from_idea}: {idea.name}", err=True)
        except Exception as e:
            click.echo(f"Error loading idea: {e}", err=True)
            sys.exit(1)
    else:
        # Read input normally
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

    # Augment prompt with missing systems if provided
    if augment:
        try:
            augment_path = Path(augment)
            if not augment_path.exists():
                click.echo(f"Warning: Augment file not found: {augment}", err=True)
                click.echo("  Continuing without augmentation", err=True)
            else:
                augment_data = json.loads(augment_path.read_text(encoding="utf-8"))
                missing_systems = augment_data.get("missing_systems", [])
                partial_systems = augment_data.get("partial_systems", [])
                
                if missing_systems or partial_systems:
                    augmentation_text = "\n\n## Missing Systems Analysis\n\n"
                    augmentation_text += "The following systems were identified as missing or incomplete:\n\n"
                    
                    if missing_systems:
                        augmentation_text += "### Missing Systems (Critical)\n\n"
                        for system in missing_systems:
                            augmentation_text += f"- **{system.get('system', 'Unknown')}** ({system.get('category', 'unknown')} category, {system.get('priority', 'medium')} priority)\n"
                            augmentation_text += f"  - {system.get('rationale', 'No rationale provided')}\n"
                    
                    if partial_systems:
                        augmentation_text += "\n### Partial Systems (Needs Completion)\n\n"
                        for system in partial_systems:
                            augmentation_text += f"- **{system.get('system', 'Unknown')}** ({system.get('category', 'unknown')} category, {system.get('priority', 'medium')} priority)\n"
                            augmentation_text += f"  - {system.get('rationale', 'No rationale provided')}\n"
                    
                    user_prompt += augmentation_text
                    if verbose:
                        click.echo(f"Augmented prompt with {len(missing_systems)} missing and {len(partial_systems)} partial systems", err=True)
        except Exception as e:
            click.echo(f"Warning: Failed to augment prompt: {e}", err=True)
            click.echo("  Continuing without augmentation", err=True)

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


@main.command()
@click.argument("input_source", type=click.Path(exists=False))
@click.option(
    "--count",
    "-c",
    type=int,
    default=8,
    help="Number of ideas to generate (default: 8)",
)
@click.option(
    "--domain",
    help="Bias the idea space (e.g., 'gamedev', 'web', 'ai')",
)
@click.option(
    "--depth",
    type=click.Choice(["low", "medium", "high"], case_sensitive=False),
    default="medium",
    help="How detailed each idea is (default: medium)",
)
@click.option(
    "--diversity",
    type=click.Choice(["low", "medium", "high"], case_sensitive=False),
    default="medium",
    help="How far ideas can drift from each other (default: medium)",
)
@click.option(
    "--constraints",
    help="Comma-separated constraints (e.g., 'local-ai,offline,deterministic')",
)
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["markdown", "json"], case_sensitive=False),
    default="markdown",
    help="Output format (default: markdown)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(writable=True),
    default=None,
    help="Output file (default: stdout)",
)
@click.option(
    "--compare-with",
    help="Path to codebase for feasibility analysis (future feature)",
)
@click.option(
    "--persona",
    help="Persona to use (e.g., 'game-designer', 'systems-engineer') (future feature)",
)
@click.option(
    "--provider",
    "-p",
    type=click.Choice(["ollama", "qwen", "gemini", "openrouter", "auto"], case_sensitive=False),
    default="auto",
    help="LLM provider (default: auto)",
)
@click.option(
    "--model",
    "-m",
    default=None,
    help="Model name (provider-specific)",
)
@click.option(
    "--temperature",
    "-t",
    type=float,
    default=0.7,
    help="Temperature for generation (default: 0.7 for creativity)",
)
@click.option(
    "--api-key",
    default=None,
    help="API key (or use environment variables)",
)
@click.option(
    "--base-url",
    default=None,
    help="Base URL (provider-specific)",
)
@click.option(
    "--verbose/--no-verbose",
    "-v/--no-v",
    default=True,
    help="Show progress (default: enabled)",
)
def brainstorm(
    input_source: str,
    count: int,
    domain: str | None,
    depth: str,
    diversity: str,
    constraints: str | None,
    output_format: str,
    output: str | None,
    compare_with: str | None,
    persona: str | None,
    provider: str,
    model: str | None,
    temperature: float,
    api_key: str | None,
    base_url: str | None,
    verbose: bool,
):
    """
    Generate multiple high-quality project ideas from a vague prompt.
    
    Transform a vague or medium prompt into N well-structured project ideas,
    each already decomposed enough to evaluate or immediately compile into a mega-prompt.
    
    INPUT_SOURCE can be a file path or '-' for stdin.
    
    Examples:
    
      # Generate 8 ideas from a prompt
      megaprompt brainstorm "AI + simulation game" --count 8
      
      # Generate ideas with constraints
      megaprompt brainstorm idea.txt --constraints local-ai,offline,deterministic
      
      # Output as JSON for machine processing
      megaprompt brainstorm "web app" --format json -o ideas.json
    """
    from megaprompt.cli.brainstorm_formatters import format_brainstorm_output
    from megaprompt.core.brainstorm_pipeline import BrainstormPipeline

    # Read input
    if input_source == "-":
        seed_prompt = sys.stdin.read()
    else:
        input_path = Path(input_source)
        if not input_path.exists():
            click.echo(f"Error: Input file not found: {input_source}", err=True)
            sys.exit(1)
        seed_prompt = input_path.read_text(encoding="utf-8")

    if not seed_prompt.strip():
        click.echo("Error: Input is empty", err=True)
        sys.exit(1)

    # Parse constraints
    constraints_list = None
    if constraints:
        constraints_list = [c.strip() for c in constraints.split(",") if c.strip()]

    # Create pipeline
    try:
        pipeline = BrainstormPipeline(
            provider=provider,
            model=model,
            temperature=temperature,
            api_key=api_key,
            base_url=base_url,
        )

        # Run brainstorm
        result = pipeline.brainstorm(
            seed_prompt=seed_prompt,
            count=count,
            domain=domain,
            depth=depth,
            diversity=diversity,
            constraints=constraints_list,
            verbose=verbose,
        )

        # Format output
        output_text = format_brainstorm_output(result, output_format)

        # Write output
        if output:
            output_path = Path(output)
            output_path.write_text(output_text, encoding="utf-8")
            if verbose:
                click.echo(f"✓ Ideas written to: {output_path}")
        else:
            click.echo(output_text)

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        if verbose:
            import traceback
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
@click.argument("codebase_path", type=click.Path(exists=False, file_okay=False, dir_okay=True, resolve_path=True))
@click.option(
    "--mode",
    type=click.Choice(["systems", "holes", "enhancements", "full"], case_sensitive=False),
    default="full",
    help="Analysis mode (default: full)",
)
@click.option(
    "--compare-with",
    type=click.Path(exists=False, file_okay=True, dir_okay=False, resolve_path=True),
    default=None,
    help="Path to original prompt file for intent drift detection (can be absolute or relative)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(writable=True),
    default=None,
    help="Output file (default: stdout)",
)
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["markdown", "json"], case_sensitive=False),
    default="markdown",
    help="Output format (default: markdown)",
)
@click.option(
    "--depth",
    type=click.Choice(["low", "medium", "high"], case_sensitive=False),
    default="high",
    help="Scanning depth (default: high)",
)
@click.option(
    "--export",
    type=click.Path(writable=True),
    default=None,
    help="Export missing systems as JSON for prompt augmentation",
)
@click.option(
    "--focus",
    default=None,
    help="Focus analysis on specific module/system",
)
@click.option(
    "--provider",
    "-p",
    type=click.Choice(["ollama", "qwen", "gemini", "openrouter", "auto"], case_sensitive=False),
    default="auto",
    help="LLM provider (default: auto)",
)
@click.option(
    "--model",
    "-m",
    default=None,
    help="Model name (provider-specific)",
)
@click.option(
    "--api-key",
    default=None,
    help="API key (for OpenRouter, Qwen, or Gemini provider)",
)
@click.option(
    "--verbose/--no-verbose",
    "-v/--no-v",
    default=True,
    help="Show progress (default: enabled)",
)
@click.option(
    "--log-level",
    default="INFO",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], case_sensitive=False),
    help="Logging level (default: INFO)",
)
@click.option(
    "--log-file",
    type=click.Path(),
    default=None,
    help="Path to log file (default: stderr)",
)
@click.option(
    "--json-logging",
    is_flag=True,
    default=False,
    help="Output logs in JSON format",
)
def analyze(
    codebase_path: str,
    mode: str,
    compare_with: str | None,
    output: str | None,
    output_format: str,
    depth: str,
    export: str | None,
    focus: str | None,
    provider: str,
    model: str | None,
    api_key: str | None,
    verbose: bool,
    log_level: str,
    log_file: str | None,
    json_logging: bool,
):
    """
    Analyze codebase to identify system holes, architectural risks, and enhancement opportunities.
    
    This command performs deep codebase analysis to detect:
      - Missing systems that should exist for the project type
      - Architectural risks and implicit assumptions
      - Context-aware enhancement suggestions
      - Intent drift (if original prompt provided)
    
    Examples:
    
      # Full analysis
      megaprompt analyze ./project --output report.md
      
      # Focus on system holes only
      megaprompt analyze ./project --mode holes
      
      # Compare with original design intent
      megaprompt analyze ./project --compare-with original.prompt
      
      # Export missing systems for prompt augmentation
      megaprompt analyze ./project --export missing.json
      megaprompt generate idea.txt --augment missing.json
    """
    # Configure logging first
    from megaprompt.core.logging import configure_logging
    configure_logging(level=log_level, json_output=json_logging, log_file=log_file)
    
    from megaprompt.analysis.pipeline import AnalysisPipeline
    from megaprompt.analysis.report_generator import ReportGenerator
    from megaprompt.core.config import Config
    from megaprompt.core.provider_factory import create_client

    # Load configuration
    config = Config.load()
    
    # Override with CLI args
    if provider != "auto":
        config.provider = provider
    if model:
        config.model = model
    if api_key:
        config.api_key = api_key

    # Create LLM client
    try:
        llm_client = create_client(
            provider=config.provider,
            model=config.model,
            temperature=0.0,
            seed=None,
            base_url=config.base_url,
            api_key=config.api_key,
        )
    except Exception as e:
        click.echo(f"Error creating LLM client: {e}", err=True)
        sys.exit(1)

    # Validate codebase path
    codebase_path_obj = Path(codebase_path).expanduser().resolve()
    
    if not codebase_path_obj.exists():
        click.echo(f"Error: Codebase path does not exist: {codebase_path_obj}", err=True)
        click.echo(f"  Provided path: {codebase_path}", err=True)
        click.echo(f"  Current directory: {Path.cwd()}", err=True)
        
        # Smart suggestion: if path starts with ./ and looks like it should be absolute
        if codebase_path.startswith("./") and codebase_path.count("/") >= 2:
            # Remove ./ and try as absolute path
            suggested_abs = "/" + codebase_path[2:]
            suggested_path_obj = Path(suggested_abs).expanduser().resolve()
            if suggested_path_obj.exists():
                click.echo(f"  Tip: Did you mean: {suggested_path_obj} (remove './' and use absolute path)?", err=True)
            else:
                click.echo(f"  Tip: If this should be an absolute path, try: {suggested_abs}", err=True)
                click.echo(f"  Tip: Or use a relative path from current directory, or check the path is correct", err=True)
        elif not Path(codebase_path).is_absolute():
            click.echo(f"  Tip: Use absolute path (e.g., /home/user/path) or check the path is correct", err=True)
        else:
            click.echo(f"  Tip: Check the path is correct", err=True)
        sys.exit(1)
    
    if not codebase_path_obj.is_dir():
        click.echo(f"Error: Codebase path is not a directory: {codebase_path_obj}", err=True)
        click.echo(f"  Tip: Provide a directory path, not a file", err=True)
        sys.exit(1)
    
    # Validate compare_with path if provided
    if compare_with:
        compare_with_obj = Path(compare_with).expanduser().resolve()
        if not compare_with_obj.exists():
            click.echo(f"Error: Original prompt file does not exist: {compare_with_obj}", err=True)
            click.echo(f"  Tip: Check the file path is correct", err=True)
            sys.exit(1)
        if not compare_with_obj.is_file():
            click.echo(f"Error: Original prompt path is not a file: {compare_with_obj}", err=True)
            click.echo(f"  Tip: Provide a file path for --compare-with", err=True)
            sys.exit(1)
        compare_with = str(compare_with_obj)

    # Create analysis pipeline
    pipeline = AnalysisPipeline(
        llm_client=llm_client,
        depth=depth,
        verbose=verbose,
    )

    try:
        # Run analysis
        report = pipeline.analyze(
            codebase_path=str(codebase_path_obj),
            original_prompt_path=compare_with,
        )

        # Filter by mode if needed
        if mode != "full":
            if mode == "holes":
                # Only show holes
                report.enhancements.enhancements = []
                if report.intent_drift:
                    report.intent_drift.drifts = []
            elif mode == "systems":
                # Only show systems analysis
                report.enhancements.enhancements = []
                if report.intent_drift:
                    report.intent_drift.drifts = []
            elif mode == "enhancements":
                # Only show enhancements
                report.holes.missing = []
                report.holes.partial = []
                report.holes.present = []
                if report.intent_drift:
                    report.intent_drift.drifts = []

        # Generate report
        generator = ReportGenerator()
        
        if output_format == "json":
            report_text = generator.generate_json(report)
        else:
            report_text = generator.generate_markdown(report)

        # Export missing systems if requested
        if export:
            try:
                import json
                export_path = Path(export).expanduser().resolve()
                export_path.parent.mkdir(parents=True, exist_ok=True)
                export_data = {
                    "missing_systems": [h.model_dump() for h in report.holes.missing],
                    "partial_systems": [h.model_dump() for h in report.holes.partial],
                }
                export_path.write_text(json.dumps(export_data, indent=2), encoding="utf-8")
                if verbose:
                    click.echo(f"Exported missing systems to: {export_path}", err=True)
            except PermissionError as e:
                click.echo(f"Error: Cannot write to export file: {export}", err=True)
                click.echo(f"  {e}", err=True)
                sys.exit(1)
            except Exception as e:
                click.echo(f"Error exporting missing systems: {e}", err=True)
                sys.exit(1)

        # Write output
        if output:
            try:
                output_path = Path(output).expanduser().resolve()
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(report_text, encoding="utf-8")
                if verbose:
                    click.echo(f"Analysis report written to: {output_path}")
            except PermissionError as e:
                click.echo(f"Error: Cannot write to output file: {output}", err=True)
                click.echo(f"  {e}", err=True)
                sys.exit(1)
            except Exception as e:
                click.echo(f"Error writing output file: {e}", err=True)
                sys.exit(1)
        else:
            click.echo(report_text)

    except ValueError as e:
        # Handle validation errors (e.g., path issues)
        click.echo(f"Error: {e}", err=True)
        if "does not exist" in str(e) or "path" in str(e).lower():
            try:
                resolved = Path(codebase_path).expanduser().resolve()
                click.echo(f"  Provided path: {codebase_path}", err=True)
                click.echo(f"  Resolved path: {resolved}", err=True)
            except Exception:
                click.echo(f"  Provided path: {codebase_path}", err=True)
        sys.exit(1)
    except FileNotFoundError as e:
        click.echo(f"Error: File or directory not found: {e}", err=True)
        click.echo(f"  Provided path: {codebase_path}", err=True)
        sys.exit(1)
    except PermissionError as e:
        click.echo(f"Error: Permission denied accessing path: {e}", err=True)
        try:
            resolved = Path(codebase_path).expanduser().resolve()
            click.echo(f"  Path: {resolved}", err=True)
        except Exception:
            click.echo(f"  Path: {codebase_path}", err=True)
        click.echo(f"  Tip: Check file permissions or run with appropriate access", err=True)
        sys.exit(1)
    except Exception as e:
        # Generic error handling
        click.echo(f"Error during analysis: {e}", err=True)
        if verbose:
            import traceback
            click.echo("\nFull traceback:", err=True)
            traceback.print_exc()
        else:
            click.echo(f"  Tip: Run with --verbose to see full error details", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

