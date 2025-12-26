"""CLI interface for Mega-Prompt Generator."""

import json
import sys
from pathlib import Path

import click
import yaml

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
    type=click.Choice(["markdown", "json", "yaml"], case_sensitive=False),
    default="markdown",
    help="Output format (default: markdown)",
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
    # Read input
    if input_source == "-":
        user_prompt = sys.stdin.read()
    else:
        input_path = Path(input_source)
        if not input_path.exists():
            click.echo(f"Error: Input file not found: {input_source}", err=True)
            sys.exit(1)
        user_prompt = input_path.read_text(encoding="utf-8")

    if not user_prompt.strip():
        click.echo("Error: Input is empty", err=True)
        sys.exit(1)

    # Initialize pipeline
    try:
        pipeline = MegaPromptPipeline(
            provider=provider,
            base_url=base_url,
            model=model,
            temperature=temperature,
            seed=seed,
            api_key=api_key,
        )
    except Exception as e:
        click.echo(f"Error initializing pipeline: {e}", err=True)
        sys.exit(1)

    # Generate mega-prompt
    try:
        mega_prompt_text, intermediate_outputs = pipeline.generate(
            user_prompt, verbose=verbose
        )

        # Format output
        if output_format.lower() == "json":
            # For JSON, include intermediate outputs if verbose
            output_data = {"mega_prompt": mega_prompt_text}
            if verbose:
                output_data["intermediate"] = intermediate_outputs
            output_text = json.dumps(output_data, indent=2)
        elif output_format.lower() == "yaml":
            # For YAML, include intermediate outputs if verbose
            output_data = {"mega_prompt": mega_prompt_text}
            if verbose:
                output_data["intermediate"] = intermediate_outputs
            output_text = yaml.dump(output_data, default_flow_style=False, sort_keys=False)
        else:  # markdown
            output_text = mega_prompt_text
            if verbose:
                output_text += "\n\n---\n\n# Intermediate Outputs\n\n"
                output_text += f"```json\n{json.dumps(intermediate_outputs, indent=2)}\n```"

        # Write output
        if output:
            output_path = Path(output)
            output_path.write_text(output_text, encoding="utf-8")
            if verbose:
                click.echo(f"\nOutput written to: {output_path}", err=True)
        else:
            click.echo(output_text)

    except Exception as e:
        click.echo(f"Error generating mega-prompt: {e}", err=True)
        if verbose:
            import traceback

            click.echo(traceback.format_exc(), err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

