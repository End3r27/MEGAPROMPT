# Mega-Prompt Generator

Transform messy human prompts into structured, deterministic mega-prompts optimized for AI execution.

## Overview

Mega-Prompt Generator implements a 5-stage pipeline that progressively refines a user prompt:

```
User Prompt → Intent Extraction → Project Decomposition → Domain Expansion 
→ Risk Analysis → Constraint Enforcement → Mega-Prompt Assembly
```

Each stage uses specialized AI prompts with structured JSON outputs validated by Pydantic models.

## Installation

```bash
pip install -e .
```

## Requirements

- Python 3.10+
- **One of the following LLM providers:**
  - **Ollama**: Running locally at `http://localhost:11434` (or set `OLLAMA_BASE_URL`)
  - **Qwen AI**: API key from Alibaba Cloud DashScope (set `QWEN_API_KEY`)
  - **Google AI Gemini**: Free API key from Google AI Studio (set `GEMINI_API_KEY`)

## Usage

```bash
# Generate from stdin (auto-detect provider)
echo "I want to build a civilization simulator" | megaprompt generate -

# Generate from file
megaprompt generate input.txt -o output.md

# Use specific provider
megaprompt generate input.txt -o output.md --provider ollama --model llama3.1
megaprompt generate input.txt -o output.md --provider qwen --model qwen-plus
megaprompt generate input.txt -o output.md --provider gemini --model gemini-2.5-flash

# With all options
megaprompt generate input.txt -o output.md --provider auto --model qwen-plus --verbose --format json
```

## Options

- `--provider/-p`: LLM provider - `ollama`, `qwen`, `gemini`, or `auto` (default: `auto` - auto-detects available provider)
- `--output/-o`: Output file (default: stdout)
- `--model/-m`: Model name (provider-specific defaults: Ollama: `llama3.1`, Qwen: `qwen-plus`, Gemini: `gemini-2.5-flash`)
- `--temperature/-t`: Temperature (default: 0 for determinism)
- `--seed/-s`: Random seed for determinism
- `--verbose/-v`: Show intermediate stage outputs
- `--format/-f`: Output format: `markdown`, `json`, or `yaml`
- `--base-url`: Base URL (provider-specific, not used for Gemini)
- `--api-key`: API key for Qwen or Gemini provider (or use `QWEN_API_KEY`/`GEMINI_API_KEY` env var)

## Environment Variables

### Ollama Provider
- `OLLAMA_BASE_URL`: Ollama API base URL (default: `http://localhost:11434`)
- `OLLAMA_MODEL`: Default Ollama model (default: `llama3.1`)

### Qwen Provider
- `QWEN_API_KEY`: Qwen AI API key from DashScope (required for Qwen provider)
  - Get your key from: https://dashscope.aliyuncs.com/
  - **Format**: Keys typically start with `sk-` (e.g., `sk-xxxxx`)
  - The key is automatically formatted as `Authorization: Bearer <key>` (no need to add "Bearer" prefix)
  - **Common issues**: 
    - Remove quotes if you copied with quotes: `QWEN_API_KEY="sk-xxx"` → `QWEN_API_KEY=sk-xxx`
    - Remove extra spaces before/after the key
    - Ensure you're using the full key (not truncated)
- `QWEN_API_BASE`: Qwen API base URL (default: `https://dashscope.aliyuncs.com/compatible-mode/v1`)
  - **Important**: Use the exact endpoint `https://dashscope.aliyuncs.com/compatible-mode/v1` for DashScope
  - Alternative for international users: `https://dashscope-intl.aliyuncs.com/api/v1`
- `QWEN_MODEL`: Default Qwen model (default: `qwen-plus`)
  - Supported models: `qwen-plus`, `qwen-turbo`, `qwen-max`, `qwen-max-longcontext`

### Gemini Provider
- `GEMINI_API_KEY`: Google AI Gemini API key (required for Gemini provider)
  - Get your **free** API key from: https://aistudio.google.com/app/apikey
  - **Auto-browser opening**: If the key is missing, megaprompt will automatically open Google AI Studio in your browser
  - **Common issues**: 
    - Remove quotes if you copied with quotes: `GEMINI_API_KEY="key"` → `GEMINI_API_KEY=key`
    - Remove extra spaces before/after the key
    - Ensure you're using the full key (not truncated)
- `GEMINI_MODEL`: Default Gemini model (default: `gemini-2.5-flash`)
  - Supported models: `gemini-2.5-flash` (recommended, free tier, fast, text-out), `gemini-3-flash` (newer, text-out), `gemini-2.5-flash-lite` (lighter version)

## Provider Selection

The tool supports auto-detection of available providers:

- **Auto mode** (default): Automatically selects the first available provider:
  1. Checks for `QWEN_API_KEY` → uses Qwen
  2. Checks for `GEMINI_API_KEY` → uses Gemini
  3. Checks if Ollama is running → uses Ollama
  4. Raises error if none are available

- **Manual selection**: Use `--provider ollama`, `--provider qwen`, or `--provider gemini` to force a specific provider

### Qwen AI Setup

1. Get an API key from [Alibaba Cloud DashScope](https://dashscope.aliyuncs.com/)
2. Set the environment variable:
   ```bash
   export QWEN_API_KEY="your-api-key-here"
   ```
3. Use Qwen provider:
   ```bash
   megaprompt generate input.txt --provider qwen
   ```

### Google AI Gemini Setup

1. Get a **free** API key from [Google AI Studio](https://aistudio.google.com/app/apikey)
   - **Auto-browser opening**: If you don't have a key set, megaprompt will automatically open Google AI Studio in your browser!
2. Set the environment variable:
   ```bash
   # Windows PowerShell
   $env:GEMINI_API_KEY="your-api-key-here"
   
   # Windows CMD
   set GEMINI_API_KEY=your-api-key-here
   
   # Linux/Mac
   export GEMINI_API_KEY="your-api-key-here"
   ```
3. Use Gemini provider:
   ```bash
   megaprompt generate input.txt --provider gemini
   ```
   
   Or let auto-detection find it:
   ```bash
   megaprompt generate input.txt  # Auto-detects Gemini if GEMINI_API_KEY is set
   ```

#### DashScope API Troubleshooting

If you encounter authentication or connection errors with DashScope, check the following:

**Common Issues:**

1. **401 Unauthorized Error**
   - **Invalid API key**: Verify your `QWEN_API_KEY` is correct and complete
   - **API key format**: 
     - Keys should start with `sk-` (e.g., `sk-xxxxx`)
     - The key is automatically sent as `Authorization: Bearer <key>` (handled automatically)
     - Remove quotes if you set it as `QWEN_API_KEY="sk-xxx"` → use `QWEN_API_KEY=sk-xxx`
     - Remove extra spaces before/after the key
   - **IP restrictions**: Check if your API key has IP whitelist restrictions in the DashScope console
   - **Rate limits**: Verify you haven't exceeded your API quota
   - **Key activation**: New keys may take 5-10 minutes to activate
   - **Wrong endpoint**: Ensure the endpoint is exactly `https://dashscope.aliyuncs.com/compatible-mode/v1`

2. **404 Model Not Found**
   - **Invalid model name**: Use one of the supported models:
     - `qwen-plus` (recommended for most tasks)
     - `qwen-turbo` (faster, lower cost)
     - `qwen-max` (highest quality)
     - `qwen-max-longcontext` (for long contexts)
   - Set model with: `--model qwen-plus` or `QWEN_MODEL=qwen-plus`

3. **Network/Connection Errors**
   - Check your internet connection
   - Verify firewall settings allow connections to `dashscope.aliyuncs.com`
   - Try increasing timeout if requests are slow

4. **API Key Format**
   - DashScope API keys typically start with `sk-` (e.g., `sk-xxxxx`)
   - The library automatically formats the key as `Authorization: Bearer <key>` in the Authorization header
   - **Common mistakes to avoid**:
     - Don't include quotes: `QWEN_API_KEY="sk-xxx"` ❌ → `QWEN_API_KEY=sk-xxx` ✅
     - Don't add "Bearer" prefix manually (it's added automatically)
     - Don't truncate the key - use the full key from DashScope console
     - Remove any trailing/leading whitespace

**Verification Steps:**

```bash
# Verify your API key is set
echo $QWEN_API_KEY

# Test with explicit endpoint
megaprompt generate input.txt --provider qwen --base-url https://dashscope.aliyuncs.com/compatible-mode/v1

# Test with specific model
megaprompt generate input.txt --provider qwen --model qwen-plus
```

**Getting Help:**

- DashScope Console: https://dashscope.aliyuncs.com/
- Check API key status and restrictions in the DashScope console
- Verify service status and quotas

### Ollama Setup

1. Install and run Ollama: https://ollama.ai/
2. Pull a model:
   ```bash
   ollama pull llama3.1
   ```
3. Use Ollama provider (or let auto-detection find it):
   ```bash
   megaprompt generate input.txt --provider ollama
   ```

## Architecture

The tool consists of:

1. **Intent Extractor**: Removes fluff, extracts core intent
2. **Project Decomposer**: Breaks project into orthogonal systems
3. **Domain Expander**: Expands each system with detailed specifications
4. **Risk Analyzer**: Identifies unknowns and risk points
5. **Constraint Enforcer**: Applies technical constraints
6. **Prompt Assembler**: Combines all outputs into final mega-prompt

## License

MIT

