"""Google AI Gemini LLM client wrapper."""

import json
import os
import re
import webbrowser
import warnings
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from typing import Optional

# Try new package first, then fallback to deprecated package
_USE_NEW_API = False
try:
    from google import genai as genai_new
    _USE_NEW_API = True
    genai = genai_new
except ImportError:
    genai_new = None  # type: ignore
    # Fallback to deprecated package for backward compatibility
    try:
        import google.generativeai as genai
        warnings.warn(
            "google.generativeai is deprecated. Please install google-genai instead: "
            "pip install google-genai",
            DeprecationWarning,
            stacklevel=2,
        )
    except ImportError:
        genai = None  # type: ignore

from megaprompt.core.llm_base import LLMClientBase

# Google AI Studio URL for getting API keys
GOOGLE_AI_STUDIO_URL = "https://aistudio.google.com/app/apikey"

# Known valid Gemini model names
GEMINI_MODELS = [
    "gemini-2.5-flash",
    "gemini-3-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash-tts",
    "gemini-robotics-er-1.5-preview",
    "gemma-3-12b",
    "gemma-3-1b",
    "gemma-3-27b",
    "gemma-3-2b",
    "gemma-3-4b",
    "gemini-2.5-flash-native-audio-dialog",
]

# Fallback model order for rate limit handling (text-out models prioritized)
GEMINI_FALLBACK_MODELS = [
    "gemini-2.5-flash",      # Default, best balance
    "gemini-3-flash",        # Newer alternative
    "gemini-2.5-flash-lite", # Lighter version
    "gemma-3-2b",           # Small Gemma model
    "gemma-3-1b",           # Even smaller
]


class GeminiClient:
    """Client for interacting with Google AI Gemini API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-2.5-flash",
        temperature: float = 0.0,
        seed: Optional[int] = None,
    ):
        """
        Initialize Gemini client.

        Args:
            api_key: Gemini API key (defaults to GEMINI_API_KEY env var)
            model: Model name to use (default: gemini-2.5-flash)
            temperature: Temperature for generation (0.0 for determinism)
            seed: Random seed for determinism (Gemini may not support this)
        """
        if genai is None:
            raise ImportError(
                "google-genai package is required for Gemini support. "
                "Install it with: pip install google-genai\n"
                "Note: google-generativeai is deprecated and will be removed in future versions."
            )

        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        
        # If API key is missing, open browser to Google AI Studio
        if not self.api_key:
            print("\n" + "=" * 60)
            print("Google AI Gemini API key not found!")
            print("=" * 60)
            print(f"\nOpening Google AI Studio in your browser...")
            print(f"URL: {GOOGLE_AI_STUDIO_URL}")
            print("\nSteps to get your free API key:")
            print("1. Sign in with your Google account")
            print("2. Click 'Create API key' or 'Get API key'")
            print("3. Copy your API key")
            print("4. Set it as an environment variable:")
            print("   Windows PowerShell: $env:GEMINI_API_KEY='your-key-here'")
            print("   Windows CMD: set GEMINI_API_KEY=your-key-here")
            print("   Linux/Mac: export GEMINI_API_KEY='your-key-here'")
            print("\nOr pass it directly: --api-key your-key-here")
            print("=" * 60 + "\n")
            
            # Open browser automatically
            try:
                webbrowser.open(GOOGLE_AI_STUDIO_URL)
            except Exception as e:
                print(f"Could not open browser automatically: {e}")
                print(f"Please visit: {GOOGLE_AI_STUDIO_URL}")
            
            raise ValueError(
                "GEMINI_API_KEY environment variable is required for Gemini provider. "
                f"Get your free API key from: {GOOGLE_AI_STUDIO_URL}"
            )

        # Clean and validate API key format
        self.api_key = self.api_key.strip().strip('"').strip("'")
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY cannot be empty. Please provide a valid API key from "
                f"{GOOGLE_AI_STUDIO_URL}"
            )

        self.original_model = model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self.model = self.original_model
        self.temperature = temperature
        self.seed = seed
        self.api_key_value = self.api_key  # Store for re-initialization
        self.fallback_attempts = []  # Track which models we've tried

        # Validate model name
        if self.model not in GEMINI_MODELS:
            warnings.warn(
                f"Model '{self.model}' may not be available. "
                f"Common models: {', '.join(GEMINI_MODELS[:3])}",
                UserWarning,
            )

        self._initialize_client()

    def _initialize_client(self):
        """Initialize or re-initialize the client with current model."""
        # Initialize client based on API version
        if _USE_NEW_API:
            # New google.genai API - Client automatically reads GEMINI_API_KEY from env
            # But we can also pass api_key explicitly
            self.client = genai.Client(api_key=self.api_key_value)
            self.use_new_api = True
        else:
            # Old google.generativeai API
            genai.configure(api_key=self.api_key_value)
            generation_config = {
                "temperature": self.temperature,
            }
            if self.seed is not None:
                # Note: Gemini may not support seed parameter in all models
                generation_config["seed"] = self.seed
            
            self.client = genai.GenerativeModel(
                model_name=self.model,
                generation_config=generation_config,
            )
            self.use_new_api = False

    def _get_next_fallback_model(self, current_model: str) -> Optional[str]:
        """Get the next fallback model to try, excluding the current model."""
        # Get list of models to try (original + fallbacks)
        models_to_try = [self.original_model] + [
            m for m in GEMINI_FALLBACK_MODELS if m != self.original_model
        ]
        
        # Find next model we haven't tried yet (excluding current)
        attempted = set(self.fallback_attempts + [current_model])
        for model in models_to_try:
            if model not in attempted:
                return model
        return None

    def _switch_to_fallback_model(self) -> bool:
        """Switch to a fallback model. Returns True if switched, False if no more models."""
        # Track current model as attempted
        current_model = self.model
        if current_model not in self.fallback_attempts:
            self.fallback_attempts.append(current_model)
        
        # Get next model to try
        next_model = self._get_next_fallback_model(current_model)
        if next_model:
            self.model = next_model
            self._initialize_client()
            return True
        return False

    def generate(
        self,
        prompt: str,
        max_retries: int = 3,
        timeout: int = 120,
    ) -> str:
        """
        Generate response from Gemini API.

        Args:
            prompt: Input prompt
            max_retries: Maximum number of retry attempts
            timeout: Request timeout in seconds (not directly supported by SDK)

        Returns:
            Generated text response

        Raises:
            RuntimeError: If API call fails after retries
        """
        def _make_api_call():
            """Helper function to make the API call (for timeout support)."""
            if self.use_new_api:
                # New API: client.models.generate_content(model=..., contents=...)
                # The contents parameter should be a string or list of content parts
                # Build config dict only if we have parameters to set
                config_params = {}
                if self.temperature is not None:
                    config_params["temperature"] = self.temperature
                if self.seed is not None:
                    config_params["seed"] = self.seed
                
                # Call the API - contents should be the prompt as a string
                # The API expects contents to be the user message
                if config_params:
                    response = self.client.models.generate_content(
                        model=self.model,
                        contents=prompt,
                        config=config_params,
                    )
                else:
                    response = self.client.models.generate_content(
                        model=self.model,
                        contents=prompt,
                    )
                return response
            else:
                # Old API: client.generate_content(prompt)
                return self.client.generate_content(prompt)
        
        def _extract_response_text(response):
            """Helper function to extract text from response."""
            if not response:
                return ""
            
            if self.use_new_api:
                # New API response handling - try multiple ways to extract text
                # Method 1: Direct text attribute
                if hasattr(response, 'text') and response.text:
                    return str(response.text).strip()
                
                # Method 2: Candidates with content.parts
                if hasattr(response, 'candidates') and response.candidates:
                    for candidate in response.candidates:
                        if hasattr(candidate, 'content') and candidate.content:
                            if hasattr(candidate.content, 'parts') and candidate.content.parts:
                                for part in candidate.content.parts:
                                    if hasattr(part, 'text') and part.text:
                                        text = str(part.text).strip()
                                        if text:  # Only return non-empty text
                                            return text
                
                # Method 3: Try to get text from response directly
                if hasattr(response, 'content') and response.content:
                    if hasattr(response.content, 'parts') and response.content.parts:
                        for part in response.content.parts:
                            if hasattr(part, 'text') and part.text:
                                text = str(part.text).strip()
                                if text:
                                    return text
                
                # Method 4: Try string conversion
                try:
                    text = str(response).strip()
                    # Don't return if it looks like the input prompt
                    if text and len(text) > 10 and text != prompt[:min(len(text), len(prompt))]:
                        return text
                except Exception:
                    pass
            else:
                # Old API response handling
                if hasattr(response, 'text') and response.text:
                    return str(response.text).strip()
            
            return ""
        
        for attempt in range(max_retries):
            try:
                # Use ThreadPoolExecutor to add timeout support
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(_make_api_call)
                    try:
                        response = future.result(timeout=timeout)
                    except FutureTimeoutError:
                        raise TimeoutError(
                            f"Gemini API call timed out after {timeout} seconds. "
                            f"Try increasing the timeout or check your network connection."
                        )
                
                # Extract response text
                result = _extract_response_text(response)
                
                # Check if result is just the input prompt (API might be echoing it)
                if result and result.strip() == prompt.strip():
                    if attempt == max_retries - 1:
                        # Try to inspect the response object for debugging
                        response_str = f"Response type: {type(response)}"
                        if hasattr(response, '__dict__'):
                            response_str += f", Attributes: {list(response.__dict__.keys())}"
                        if hasattr(response, 'text'):
                            response_str += f", text attr: {type(response.text)}"
                        raise RuntimeError(
                            f"Gemini API returned the input prompt instead of generating a response. "
                            f"This may indicate an API configuration issue. Model: {self.model}\n"
                            f"Response info: {response_str}"
                        )
                    # Continue to retry
                    continue
                
                if result:
                    return result
                
                # If we got here, response was empty - might be an issue
                if attempt == max_retries - 1:
                    # Try to get more info about the response for debugging
                    response_info = f"Response type: {type(response)}"
                    if hasattr(response, '__dict__'):
                        response_info += f", Attributes: {list(response.__dict__.keys())}"
                    if hasattr(response, 'text'):
                        response_info += f", text value: {repr(getattr(response, 'text', None))}"
                    raise RuntimeError(
                        f"Gemini API returned empty response after {max_retries} attempts. "
                        f"Model: {self.model}, Prompt length: {len(prompt)}. "
                        f"{response_info}"
                    )

            except (TimeoutError, FutureTimeoutError) as e:
                # Re-raise timeout errors immediately
                raise RuntimeError(
                    f"Gemini API call timed out after {timeout} seconds. "
                    f"Try increasing the timeout or check your network connection."
                ) from e
            except Exception as e:
                error_msg = str(e)
                error_lower = error_msg.lower()
                
                # Handle rate limit errors immediately - try to switch models before retrying
                if "quota" in error_lower or "rate limit" in error_lower or "429" in error_msg:
                    # Try to switch to a fallback model automatically
                    if self._switch_to_fallback_model():
                        # Silently retry with fallback model (don't raise error)
                        # The retry loop will continue with the new model
                        continue
                    else:
                        # No more fallback models available - only raise error on last attempt
                        if attempt == max_retries - 1:
                            raise RuntimeError(
                                f"Gemini API rate limit or quota exceeded. Tried all available models: {', '.join(self.fallback_attempts + [self.model])}.\n\n"
                                f"Possible causes:\n"
                                f"1. Free tier quota exceeded - Check your usage in Google AI Studio\n"
                                f"2. Rate limit hit - Too many requests in a short time\n"
                                f"3. API key restrictions - Check key settings in Google AI Studio\n\n"
                                f"Troubleshooting:\n"
                                f"- Check usage and quotas: {GOOGLE_AI_STUDIO_URL}\n"
                                f"- Wait before retrying\n"
                                f"- Consider upgrading your API plan if needed\n"
                                f"- Original error: {error_msg}"
                            ) from e
                        # Continue to retry even if no fallback available
                        continue
                
                # Handle other errors only on last attempt
                if attempt == max_retries - 1:
                    # Provide helpful error messages
                    if "401" in error_msg or "unauthorized" in error_lower or "invalid" in error_lower and "api" in error_lower and "key" in error_lower:
                        raise RuntimeError(
                            f"Gemini API authentication failed (401 Unauthorized).\n\n"
                            f"Possible causes:\n"
                            f"1. Invalid API key - Check your GEMINI_API_KEY environment variable\n"
                            f"2. API key format - Remove quotes if you set it as GEMINI_API_KEY=\"key\"\n"
                            f"3. API key restrictions - Check key restrictions in Google AI Studio\n"
                            f"4. Rate limits - You may have exceeded your API quota\n\n"
                            f"Troubleshooting:\n"
                            f"- Get a new API key from: {GOOGLE_AI_STUDIO_URL}\n"
                            f"- Verify key in Google AI Studio console\n"
                            f"- Check for IP or usage restrictions\n"
                            f"- Original error: {error_msg}"
                        ) from e
                    elif "404" in error_msg or "not found" in error_lower or "model" in error_lower and ("not found" in error_lower or "invalid" in error_lower):
                        available_models = ", ".join(GEMINI_MODELS)
                        raise RuntimeError(
                            f"Gemini model '{self.model}' not found (404).\n\n"
                            f"Available Gemini models:\n"
                            f"  {available_models}\n\n"
                            f"Common models:\n"
                            f"  - gemini-2.5-flash (recommended, free tier, fast, text-out)\n"
                            f"  - gemini-3-flash (newer, text-out)\n"
                            f"  - gemini-2.5-flash-lite (lighter version)\n\n"
                            f"Set model with: --model gemini-2.5-flash\n"
                            f"Or set GEMINI_MODEL environment variable.\n\n"
                            f"Original error: {error_msg}"
                        ) from e
                    else:
                        raise RuntimeError(
                            f"Failed to generate response from Gemini API after {max_retries} attempts.\n"
                            f"Error: {error_msg}\n\n"
                            f"Troubleshooting:\n"
                            f"- Verify API key: {GOOGLE_AI_STUDIO_URL}\n"
                            f"- Check model name: {self.model}\n"
                            f"- Check Google AI Studio for service status\n"
                        ) from e
                # Continue to retry

        raise RuntimeError(f"Failed to generate response after {max_retries} attempts")

    def extract_json(self, text: str) -> dict:
        """
        Extract JSON from AI response, handling markdown code blocks.

        Args:
            text: Raw response text that may contain JSON

        Returns:
            Parsed JSON as dictionary

        Raises:
            ValueError: If no valid JSON is found
        """
        # Try to find JSON in markdown code blocks first
        json_block_pattern = r"```(?:json)?\s*(\{.*?\})\s*```"
        match = re.search(json_block_pattern, text, re.DOTALL)
        if match:
            json_str = match.group(1)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass

        # Try to find JSON object directly
        json_object_pattern = r"\{.*\}"
        match = re.search(json_object_pattern, text, re.DOTALL)
        if match:
            json_str = match.group(0)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass

        # Try parsing the entire text as JSON
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            pass

        raise ValueError(f"Could not extract valid JSON from response: {text[:200]}...")

