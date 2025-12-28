# Mega-Prompt Generator

Transform messy human prompts into structured, deterministic mega-prompts optimized for AI execution.

## Overview

Mega-Prompt Generator provides three powerful capabilities:

1. **Brainstorm**: Transform vague prompts into multiple high-quality, well-structured project ideas
2. **Mega-Prompt Generation**: A 5-stage pipeline that progressively refines user prompts into structured mega-prompts
3. **Codebase Analysis**: Deep analysis of existing codebases to identify system holes, architectural risks, and enhancement opportunities

### Mega-Prompt Generation Pipeline

```
User Prompt → Intent Extraction → Project Decomposition → Domain Expansion 
→ Risk Analysis → Constraint Enforcement → Mega-Prompt Assembly
```

Each stage uses specialized AI prompts with structured JSON outputs validated by Pydantic models.

### Codebase Analysis

The analysis system uses a systems-thinking approach to identify:
- **System Holes**: Missing systems that should exist for the project type
- **Architectural Risks**: Implicit assumptions and design patterns
- **Enhancement Ideas**: Context-aware suggestions that fit the existing architecture
- **Intent Drift**: Discrepancies between original design and implementation

The analysis combines static code scanning (multi-language parsing) with AI-powered architectural inference to provide actionable insights without code rewriting.

### Brainstorm Pipeline

Transform vague or medium prompts into multiple structured project ideas through a multi-stage pipeline:

```
Seed Prompt → Idea Space Expansion → Concept Clustering → Idea Synthesis 
→ Quality Enforcement → Deduplication → Self-Critique → Final Ideas
```

Each idea includes:
- **Core Loop**: Specific, actionable gameplay/interaction steps
- **Key Systems**: Concrete systems required for implementation
- **Unique Twist**: What makes the idea distinctive
- **Technical Challenge**: Main technical complexity
- **Feasibility**: Realistic feasibility assessment (low/medium/high)
- **Potential Failures**: Self-critique identifying realistic failure modes

## Installation

### Option 1: Install from GitHub

Download and install directly from GitHub:

```bash
# Clone the repository
git clone https://github.com/End3r27/MEGAPROMPT.git
cd MEGAPROMPT

# Install in editable mode
pip install -e .
```

Or install directly without cloning:

```bash
pip install git+https://github.com/End3r27/MEGAPROMPT.git
```

### Option 2: Manual Installation

If you've already downloaded the repository:

```bash
cd MEGAPROMPT
pip install -e .
```

After installation, you'll need to configure your LLM provider. See the [Environment Variables](#environment-variables) section for setup instructions.

## Requirements

- Python 3.10+
- **One of the following LLM providers:**
  - **OpenRouter**: Access to many models (GPT-4, Claude, Gemini, etc.) - API key from https://openrouter.ai/keys (set `OPENROUTER_API_KEY`)
  - **Ollama**: Running locally at `http://localhost:11434` (or set `OLLAMA_BASE_URL`)
  - **Qwen AI**: API key from Alibaba Cloud DashScope (set `QWEN_API_KEY`)
  - **Google AI Gemini**: Free API key from Google AI Studio (set `GEMINI_API_KEY`)

> **📝 Setting up API Keys**: See the [Environment Variables](#environment-variables) section below for detailed instructions on setting up API keys for each provider.

## Usage

### Brainstorm Project Ideas

The `brainstorm` command transforms vague prompts into multiple high-quality, well-structured project ideas:

```bash
# Generate 8 ideas from a prompt (default)
megaprompt brainstorm "AI + simulation game" --count 8

# Generate ideas with constraints
megaprompt brainstorm idea.txt --constraints local-ai,offline,deterministic

# Generate with domain bias
megaprompt brainstorm "web application" --domain web --count 12

# Control diversity and depth
megaprompt brainstorm "mobile game" --diversity high --depth high

# Output as JSON for machine processing
megaprompt brainstorm "web app" --format json -o ideas.json

# Generate from stdin
echo "AI-powered productivity tool" | megaprompt brainstorm -
```

The brainstorm pipeline:
1. **Idea Space Expansion** - Identifies concept axes (dimensions of variation) to ensure diversity
2. **Concept Clustering** - Groups axes into idea buckets
3. **Idea Synthesis** - Generates structured ideas per cluster with strict schema validation
4. **Quality Enforcement** - Validates completeness, rejects vague/unbounded ideas
5. **Deduplication** - Removes similar ideas based on core loop, systems, and unique twist
6. **Self-Critique** - Adds realistic failure mode analysis to each idea

### Generate Mega-Prompts

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

# Augment prompt with missing systems from analysis
megaprompt generate idea.txt --augment missing_systems.json

# Generate mega-prompt from a brainstorm idea
megaprompt generate input.txt --from-idea 2 --idea-file ideas.json
```

### Analyze Codebases

The `analyze` command performs deep codebase analysis to identify system holes, architectural risks, and enhancement opportunities:

```bash
# Full analysis
megaprompt analyze ./project --output report.md

# Focus on system holes only
megaprompt analyze ./project --mode holes

# Compare with original design intent
megaprompt analyze ./project --compare-with original.prompt

# Export missing systems for prompt augmentation
megaprompt analyze ./project --export missing.json
megaprompt generate idea.txt --augment missing.json

# JSON output for tool chaining
megaprompt analyze ./project --format json --output analysis.json
```

The analysis pipeline:
1. **Static Code Scanner** - Extracts structural information (modules, APIs, entry points, data models) from 18+ programming languages
   - Multi-language parsing with AST (Python) and regex-based pattern matching (other languages)
   - Markdown context extraction for project documentation
   - Framework and version detection from config files
   - Dependency extraction from package managers
   - Import graph construction for module relationships
   - Build system and CI/CD detection
   - Parallel processing and caching for performance
2. **Intent Classification** - Classifies project intent (executable_utility, base_image, template, etc.) using AI
3. **Architectural Inference** - Infers project type and patterns using AI
4. **Expected Systems Generator** - Generates canonical system checklist for the project type
5. **Presence/Absence Matrix** - Compares expected vs actual systems to find gaps
6. **Enhancement Generator** - Suggests context-aware enhancements
7. **Intent Drift Detection** - Compares original design to implementation (if original prompt provided)

### Supported Languages

The codebase scanner supports **18+ programming languages and documentation formats**:

**Backend Languages:**
- **Python** (.py) - Full AST parsing for modules, classes, functions, data models
- **Java** (.java) - Package detection, Spring annotations, entry points, entities
- **Go** (.go) - Package detection, exported functions, structs, interfaces
- **Rust** (.rs) - Module detection, pub functions, structs, traits, enums
- **C#** (.cs) - Namespace detection, ASP.NET attributes, controllers
- **Ruby** (.rb) - Module/class detection, Rails patterns, controllers
- **PHP** (.php) - Namespace detection, Laravel patterns, controllers
- **C/C++** (.c, .cpp, .h, .hpp) - Functions, structs, headers, entry points
- **Scala** (.scala) - Classes, objects, traits, case classes
- **Elixir** (.ex, .exs) - Modules, functions, macros, GenServers

**Frontend/Web Frameworks:**
- **JavaScript** (.js, .jsx) - ES6 modules, exports, Next.js/Express routes
- **TypeScript** (.ts, .tsx) - Interfaces, types, Next.js API routes
- **Vue** (.vue) - Single File Components, props, exposed methods
- **Svelte** (.svelte) - Components, props, exports

**Mobile Languages:**
- **Swift** (.swift) - Classes, structs, protocols, @main entry points
- **Kotlin** (.kt) - Classes, objects, data classes, Android patterns
- **Dart** (.dart) - Classes, Flutter widgets, entry points

**Documentation/Context:**
- **Markdown** (.md, .markdown) - Project context, architecture docs, API documentation, code examples

The scanner automatically detects file types and extracts:
- **Modules/Namespaces**: Package declarations, module structures
- **Entry Points**: Main functions, application entry points, framework-specific patterns
- **Public APIs**: Exported functions, classes, methods, interfaces
- **Data Models**: Structs, classes, interfaces, types, entities
- **Test Files**: Language-specific test patterns
- **Config Files**: Build files, dependency manifests, framework configs
- **Persistence Patterns**: Database libraries and ORMs
- **Documentation Context**: Project descriptions, architecture notes, setup instructions from Markdown files
- **Dependencies**: Extracted from package managers (npm, pip, maven, gradle, cargo, gem, composer, pub)
- **Import Graph**: Module dependency relationships
- **Build Systems**: Detected build tools (Make, CMake, Gradle, Maven, Cargo, etc.)
- **CI/CD Configs**: GitHub Actions, GitLab CI, Jenkins, Azure Pipelines, CircleCI, Travis CI

### Scanner Features

The codebase scanner includes advanced features for comprehensive analysis:

- **Multi-Language Parsing**: Supports 18+ languages with language-specific pattern recognition
- **Markdown Context Extraction**: Extracts project context, architecture documentation, API docs, and code examples from `.md` files
- **Framework Detection**: Automatically detects frameworks and versions (Next.js, React, Spring Boot, Rails, Laravel, etc.)
- **Dependency Analysis**: Extracts dependencies from all major package managers
- **Import Tracking**: Builds dependency graphs showing module relationships
- **Build System Detection**: Identifies build tools and CI/CD configurations
- **Performance Optimizations**: 
  - Parallel file processing for faster scanning
  - File-based caching to skip unchanged files
  - Incremental scanning option (only scan changed files)
- **Error Handling**: Comprehensive error collection and reporting with detailed logging
- **Complexity Metrics**: Calculates lines of code, file sizes, and basic complexity statistics

## Options

### Brainstorm Command Options

- `--count/-c`: Number of ideas to generate (default: 8)
- `--domain`: Bias the idea space (e.g., 'gamedev', 'web', 'ai')
- `--depth`: How detailed each idea is - `low`, `medium`, `high` (default: `medium`)
- `--diversity`: How far ideas can drift from each other - `low`, `medium`, `high` (default: `medium`)
- `--constraints`: Comma-separated constraints (e.g., 'local-ai,offline,deterministic')
- `--format/-f`: Output format - `markdown` or `json` (default: `markdown`)
- `--output/-o`: Output file (default: stdout)
- `--provider/-p`: LLM provider (same as generate command)
- `--model/-m`: Model name (provider-specific)
- `--temperature/-t`: Temperature for generation (default: 0.7 for creativity)
- `--api-key`: API key (or use environment variables)
- `--base-url`: Base URL (provider-specific)
- `--verbose/-v`: Show progress (default: enabled)

### Generate Command Options

- `--provider/-p`: LLM provider - `openrouter`, `ollama`, `qwen`, `gemini`, or `auto` (default: `auto` - auto-detects available provider)
- `--output/-o`: Output file (default: stdout)
- `--model/-m`: Model name (provider-specific defaults: OpenRouter: `xiaomi/mimo-v2-flash:free`, Ollama: `llama3.1`, Qwen: `qwen-plus`, Gemini: `gemini-2.5-flash`)
- `--temperature/-t`: Temperature (default: 0 for determinism)
- `--seed/-s`: Random seed for determinism
- `--verbose/-v`: Show intermediate stage outputs
- `--format/-f`: Output format: `markdown`, `json`, or `yaml`
- `--base-url`: Base URL (provider-specific, not used for Gemini)
- `--api-key`: API key for OpenRouter, Qwen, or Gemini provider (or use `OPENROUTER_API_KEY`/`QWEN_API_KEY`/`GEMINI_API_KEY` env var)
- `--augment`: Path to missing systems JSON file to augment the prompt with (from `analyze --export`)
- `--from-idea`: Use idea #N from brainstorm JSON file (use with `--idea-file`)
- `--idea-file`: Path to brainstorm JSON output file (required with `--from-idea`)

### Analyze Command Options

- `--mode`: Analysis mode - `systems`, `holes`, `enhancements`, or `full` (default: `full`)
- `--compare-with`: Path to original prompt file for intent drift detection
- `--output/-o`: Output file path (default: stdout)
- `--format/-f`: Output format - `markdown` or `json` (default: `markdown`)
- `--depth`: Scanning depth - `low`, `medium`, or `high` (default: `high`)
- `--export`: Export missing systems as JSON for prompt augmentation
- `--focus`: Focus analysis on specific module/system
- `--provider/-p`: LLM provider (same as generate command)
- `--model/-m`: Model name (same as generate command)
- `--api-key`: API key (same as generate command)
- `--verbose/-v`: Show progress (default: enabled)

## Environment Variables

> **💡 Quick Setup**: After installation, you'll need to set up API keys for your chosen LLM provider. See the provider-specific setup sections below for detailed instructions.

### Setting API Keys

You can set API keys as environment variables:

**Linux/Mac:**
```bash
export OPENROUTER_API_KEY="your-api-key-here"
export QWEN_API_KEY="your-api-key-here"
export GEMINI_API_KEY="your-api-key-here"
```

**Windows PowerShell:**
```powershell
$env:OPENROUTER_API_KEY="your-api-key-here"
$env:QWEN_API_KEY="your-api-key-here"
$env:GEMINI_API_KEY="your-api-key-here"
```

**Windows CMD:**
```cmd
set OPENROUTER_API_KEY=your-api-key-here
set QWEN_API_KEY=your-api-key-here
set GEMINI_API_KEY=your-api-key-here
```

### OpenRouter Provider

- `OPENROUTER_API_KEY`: OpenRouter API key (required for OpenRouter provider)
  - Get your API key from: https://openrouter.ai/keys
  - OpenRouter provides access to many models: GPT-4, Claude, Gemini, Llama, and more
- `OPENROUTER_API_BASE`: OpenRouter API base URL (default: `https://openrouter.ai/api/v1`)
- `OPENROUTER_MODEL`: Default OpenRouter model (default: `xiaomi/mimo-v2-flash:free`)
  - Browse all available models: https://openrouter.ai/models
  - Popular models: `openai/gpt-4o`, `anthropic/claude-3.5-sonnet`, `google/gemini-2.0-flash-exp`

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
  1. Checks for `OPENROUTER_API_KEY` → uses OpenRouter
  2. Checks for `QWEN_API_KEY` → uses Qwen
  3. Checks for `GEMINI_API_KEY` → uses Gemini
  4. Checks if Ollama is running → uses Ollama
  5. Raises error if none are available

- **Manual selection**: Use `--provider openrouter`, `--provider ollama`, `--provider qwen`, or `--provider gemini` to force a specific provider

### OpenRouter Setup

1. Get an API key from [OpenRouter](https://openrouter.ai/keys)
2. Set the environment variable:
   ```bash
   export OPENROUTER_API_KEY="your-api-key-here"
   ```
3. Use OpenRouter provider:
   ```bash
   megaprompt generate input.txt --provider openrouter --model xiaomi/mimo-v2-flash:free
   ```
   
   Or let auto-detection find it:
   ```bash
   megaprompt generate input.txt  # Auto-detects OpenRouter if OPENROUTER_API_KEY is set
   ```

4. Browse available models at https://openrouter.ai/models
   - Popular models: `openai/gpt-4o`, `openai/gpt-4o-mini`, `anthropic/claude-3.5-sonnet`, `google/gemini-2.0-flash-exp`

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

### Mega-Prompt Generation Pipeline

The tool consists of a 5-stage pipeline:

1. **Intent Extractor**: Removes fluff, extracts core intent
2. **Project Decomposer**: Breaks project into orthogonal systems
3. **Domain Expander**: Expands each system with detailed specifications
4. **Risk Analyzer**: Identifies unknowns and risk points
5. **Constraint Enforcer**: Applies technical constraints
6. **Prompt Assembler**: Combines all outputs into final mega-prompt

### Codebase Analysis Pipeline

The analysis system uses a 4-phase pipeline:

1. **Static Code Scanner** (No AI): Extracts structural information via multi-language parsing
   - **Python**: Full AST parsing for modules, classes, functions, data models, imports
   - **Other Languages**: Regex-based pattern matching for modules, entry points, APIs, data models
   - **Markdown**: Context extraction for project documentation, architecture notes, API docs, code examples
   - Detects: Modules/packages, entry points, public APIs, data models, dependencies, imports
   - Identifies: Config files, test files, persistence patterns, framework-specific structures, build systems, CI/CD configs
   - Supports 18+ languages: Python, JavaScript, TypeScript, Java, Go, Rust, C#, Ruby, PHP, Swift, Kotlin, Dart, Vue, Svelte, C/C++, Scala, Elixir, Markdown
   - **Performance**: Parallel processing, file-based caching, incremental scanning
   - **Metadata**: Framework versions, dependency graphs, complexity metrics, import relationships

2. **Intent Classification** (AI): Classifies project intent (executable_utility, base_image, template, etc.)
3. **Architectural Inference** (AI): Determines project type and patterns
   - Infers project type (e.g., "agent-based simulation", "web API")
   - Identifies dominant patterns and implicit assumptions
   - Detects frameworks and architectural style

4. **Expected Systems Generator** (AI): Generates canonical system checklist (contextual to intent)
   - Maps project types to expected system categories
   - Categories: lifecycle, persistence, error_handling, observability, performance, tooling, testing, extensibility, safety

5. **Presence/Absence Matrix** (Logic + AI): Compares expected vs actual with confidence weighting
   - Identifies missing systems
   - Detects partially implemented systems
   - Generates enhancement suggestions aligned with architecture

6. **Intent Drift Detection** (AI, optional): Compares original design to implementation
   - Detects discrepancies between original intent and current state
   - Reports severity of drift items

### Integration

The brainstorm, analysis, and generation systems integrate seamlessly:

```bash
# Brainstorm → Generate workflow
# 1. Generate multiple ideas from a vague prompt
megaprompt brainstorm "AI simulation game" --count 8 -o ideas.json

# 2. Generate mega-prompt from a specific idea
megaprompt generate input.txt --from-idea 2 --idea-file ideas.json -o mega-prompt.md

# Analyze → Generate workflow
# 1. Analyze codebase to find missing systems
megaprompt analyze ./project --export missing.json

# 2. Generate mega-prompt augmented with missing systems
megaprompt generate idea.txt --augment missing.json

# Full workflow: Brainstorm → Analyze → Generate
megaprompt brainstorm "web app" -o ideas.json
megaprompt analyze ./existing-project --export missing.json
megaprompt generate input.txt --from-idea 3 --idea-file ideas.json --augment missing.json
```

This creates a complete ideation-to-execution loop: brainstorm ideas → analyze existing code → generate prompts that bridge gaps.

## License

MIT

