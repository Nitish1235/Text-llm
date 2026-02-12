"""
Modal serverless function for Text/LLM generation service.
Production-ready implementation with error handling, validation, and logging.
Identical behavior to Runpod handler.
"""

import os
import json
import time
import logging
from typing import Dict, Any, Optional
from openai import OpenAI
import modal

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Modal app
app = modal.App("text-llm-generation")

# Environment variables (set via Modal secrets)
MODEL_NAME = os.getenv("MODEL_NAME", "llama-3-8b")
MODEL_REVISION = os.getenv("MODEL_REVISION", "v1")
MODEL_BASE_URL = os.getenv("MODEL_BASE_URL", "https://api.openai.com/v1")
MODEL_API_KEY = os.getenv("MODEL_API_KEY", "")
API_KEY = os.getenv("API_KEY", "")

# Length to token mapping
LENGTH_TO_TOKENS = {
    "20s": 100,
    "30s": 150,
    "45s": 225,
    "60s": 300
}

# Length to word count mapping
LENGTH_TO_WORDS = {
    "20s": "30-50",
    "30s": "45-75",
    "45s": "70-110",
    "60s": "90-150"
}

# Valid enums
VALID_LENGTHS = {"20s", "30s", "45s", "60s"}
VALID_TONES = {"neutral", "curious", "dramatic", "serious", "funny", "inspirational"}
VALID_HOOK_STYLES = {"question", "shock", "bold claim", "story"}


def validate_input(input_data: Dict[str, Any]) -> tuple[bool, Optional[str], Optional[str]]:
    """
    Validate input data strictly.
    Returns: (is_valid, error_message, error_code)
    """
    if not isinstance(input_data, dict):
        return False, "Input must be a dictionary", "VALIDATION_ERROR"
    
    # Required fields
    if "topic" not in input_data or not input_data["topic"]:
        return False, "Field 'topic' is required and cannot be empty", "VALIDATION_ERROR"
    
    if "length" not in input_data:
        return False, "Field 'length' is required", "VALIDATION_ERROR"
    
    if input_data["length"] not in VALID_LENGTHS:
        return False, f"Field 'length' must be one of {VALID_LENGTHS}", "VALIDATION_ERROR"
    
    if "tone" not in input_data:
        return False, "Field 'tone' is required", "VALIDATION_ERROR"
    
    if input_data["tone"] not in VALID_TONES:
        return False, f"Field 'tone' must be one of {VALID_TONES}", "VALIDATION_ERROR"
    
    if "hook_style" not in input_data:
        return False, "Field 'hook_style' is required", "VALIDATION_ERROR"
    
    if input_data["hook_style"] not in VALID_HOOK_STYLES:
        return False, f"Field 'hook_style' must be one of {VALID_HOOK_STYLES}", "VALIDATION_ERROR"
    
    if "max_tokens" not in input_data:
        return False, "Field 'max_tokens' is required", "VALIDATION_ERROR"
    
    max_tokens = input_data["max_tokens"]
    if not isinstance(max_tokens, int) or max_tokens <= 0:
        return False, "Field 'max_tokens' must be a positive integer", "VALIDATION_ERROR"
    
    # Validate max_tokens matches length
    expected_tokens = LENGTH_TO_TOKENS.get(input_data["length"])
    if max_tokens != expected_tokens:
        return False, f"Field 'max_tokens' must be {expected_tokens} for length '{input_data['length']}'", "VALIDATION_ERROR"
    
    return True, None, None


def build_hook_prompt(topic: str, hook_style: str, tone: str) -> str:
    """Build prompt for generating hook based on style."""
    hook_instructions = {
        "question": f"Start with a thought-provoking question about {topic}",
        "shock": f"Open with a surprising or shocking fact about {topic}",
        "bold claim": f"Make a bold, attention-grabbing statement about {topic}",
        "story": f"Begin with a brief, engaging story or anecdote related to {topic}"
    }
    
    return hook_instructions.get(hook_style, hook_instructions["question"])


def build_main_prompt(
    topic: str,
    length: str,
    tone: str,
    hook_style: str,
    word_count: Optional[str],
    brand_name: str = "Autopostai.Video",
    include_branding: bool = True
) -> str:
    """Build the main generation prompt."""
    word_range = word_count or LENGTH_TO_WORDS.get(length, "30-50")
    
    tone_instructions = {
        "neutral": "Use a balanced, informative tone",
        "curious": "Maintain a sense of wonder and curiosity",
        "dramatic": "Use dramatic language and emphasis",
        "serious": "Keep a serious, authoritative tone",
        "funny": "Include humor and light-heartedness",
        "inspirational": "Be uplifting and motivational"
    }
    
    hook_prompt = build_hook_prompt(topic, hook_style, tone)
    
    branding_text = ""
    if include_branding:
        branding_text = f"\n- Naturally mention '{brand_name}' once in the content if it fits organically"
    
    prompt = f"""Generate a {length} video script about: {topic}

Requirements:
- {hook_prompt}
- Maintain a {tone_instructions.get(tone, 'neutral')} tone throughout
- Target word count: {word_range} words
- Format: Start with the hook, then continue with the main content
- Make it engaging, clear, and suitable for video narration
- Keep sentences concise and punchy
{branding_text}

Output only the script text, starting with the hook line, then the main content."""

    return prompt


def build_voice_script_prompt(
    topic: str,
    tone: str,
    voice_script_style: Optional[str],
    brand_name: str = "Autopostai.Video",
    include_branding: bool = True
) -> str:
    """Build prompt for voice script generation."""
    tone_instructions = {
        "neutral": "conversational and clear",
        "curious": "wondering and engaging",
        "dramatic": "dramatic and expressive",
        "serious": "authoritative and clear",
        "funny": "light-hearted and natural",
        "inspirational": "uplifting and warm"
    }
    
    style_instruction = voice_script_style or "narration"
    
    branding_text = ""
    if include_branding:
        branding_text = f"\n- Naturally mention '{brand_name}' once if it fits organically"
    
    prompt = f"""Generate a voice narration script about: {topic}

Requirements:
- Optimized for voice/narration (more conversational and natural-sounding)
- Use {tone_instructions.get(tone, 'conversational and clear')} tone
- Style: {style_instruction}
- Include natural pauses indicated by punctuation (commas, periods)
- Can be slightly longer and more detailed than a standard script
- Make it flow naturally when spoken aloud
{branding_text}

Output only the voice script text."""

    return prompt


def count_words(text: str) -> int:
    """Count words in text."""
    return len(text.split())


def get_client() -> OpenAI:
    """Initialize and return OpenAI-compatible client."""
    return OpenAI(
        api_key=MODEL_API_KEY,
        base_url=MODEL_BASE_URL
    )


def generate_script(
    topic: str,
    length: str,
    tone: str,
    hook_style: str,
    max_tokens: int,
    word_count: Optional[str] = None,
    model: Optional[str] = None,
    brand_name: str = "Autopostai.Video",
    include_branding: bool = True
) -> tuple[str, int]:
    """
    Generate main script using LLM.
    Returns: (script_text, tokens_used)
    """
    client = get_client()
    model_name = model or MODEL_NAME
    
    prompt = build_main_prompt(topic, length, tone, hook_style, word_count, brand_name, include_branding)
    
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are an expert scriptwriter for short-form video content."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.7,
            seed=42  # Deterministic output
        )
        
        script_text = response.choices[0].message.content.strip()
        tokens_used = response.usage.total_tokens
        
        # Enforce token limit strictly
        if tokens_used > max_tokens:
            raise ValueError(f"Generated {tokens_used} tokens, exceeds limit of {max_tokens}")
        
        return script_text, tokens_used
    
    except Exception as e:
        logger.error(f"Error generating script: {str(e)}")
        if "rate limit" in str(e).lower() or "429" in str(e):
            raise Exception("Rate limit exceeded") from e
        raise Exception(f"Model error: {str(e)}") from e


def generate_voice_script(
    topic: str,
    tone: str,
    voice_script_style: Optional[str],
    model: Optional[str] = None,
    brand_name: str = "Autopostai.Video",
    include_branding: bool = True
) -> tuple[str, int]:
    """
    Generate voice script using LLM.
    Returns: (voice_script_text, tokens_used)
    """
    client = get_client()
    model_name = model or MODEL_NAME
    
    prompt = build_voice_script_prompt(topic, tone, voice_script_style, brand_name, include_branding)
    
    # Use higher token limit for voice script (can be more detailed)
    max_tokens = 400
    
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are an expert voice scriptwriter for narration."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.7,
            seed=42  # Deterministic output
        )
        
        voice_script_text = response.choices[0].message.content.strip()
        tokens_used = response.usage.total_tokens
        
        return voice_script_text, tokens_used
    
    except Exception as e:
        logger.error(f"Error generating voice script: {str(e)}")
        if "rate limit" in str(e).lower() or "429" in str(e):
            raise Exception("Rate limit exceeded") from e
        raise Exception(f"Model error: {str(e)}") from e


def extract_hook(script: str) -> str:
    """Extract the first line/sentence as the hook."""
    lines = script.split('\n')
    first_line = lines[0].strip()
    if not first_line:
        # If first line is empty, get first non-empty line
        for line in lines:
            if line.strip():
                first_line = line.strip()
                break
    
    # If still no hook, take first sentence
    if not first_line:
        sentences = script.split('.')
        if sentences:
            first_line = sentences[0].strip() + '.'
    
    return first_line or script[:100]  # Fallback to first 100 chars


def validate_api_key(headers: Dict[str, str]) -> bool:
    """Validate API key from x-api-key header."""
    if not API_KEY:
        # If no API_KEY is set, skip validation
        return True
    
    api_key = headers.get("x-api-key") or headers.get("X-Api-Key")
    return api_key == API_KEY


# Modal image with dependencies
image = modal.Image.debian_slim(python_version="3.10").pip_install(
    "openai>=1.0.0"
)


@app.function(
    image=image,
    secrets=[
        modal.Secret.from_name("text-llm-secrets", required=False)
    ],
    timeout=60,
    container_idle_timeout=120
)
@modal.web_endpoint(method="POST")
def generate(request: modal.web.Request) -> Dict[str, Any]:
    """
    Modal serverless web endpoint for text generation.
    Expected request body:
    {
        "input": {...}
    }
    Headers: x-api-key (for authentication)
    """
    start_time = time.time()
    
    try:
        # Parse request body
        try:
            event = request.json
        except:
            event = {}
        
        request_id = event.get("id", f"modal-{int(time.time())}")
        
        logger.info(f"Request {request_id}: Received event")
        
        # Extract headers from request
        headers = {}
        try:
            if hasattr(request, "headers"):
                headers = {k.lower(): v for k, v in request.headers.items()}
        except:
            pass
        
        # Also check if headers are in the event body (for compatibility)
        if "headers" in event:
            event_headers = event.get("headers", {})
            if isinstance(event_headers, dict):
                headers.update({k.lower(): v for k, v in event_headers.items()})
            elif isinstance(event_headers, str):
                try:
                    parsed_headers = json.loads(event_headers)
                    headers.update({k.lower(): v for k, v in parsed_headers.items()})
                except:
                    pass
        
        # Validate API key
        if not validate_api_key(headers):
            logger.warning(f"Request {request_id}: Invalid API key")
            return {
                "error": "Invalid API key",
                "code": "AUTH_ERROR"
            }
        
        # Extract input
        input_data = event.get("input", {})
        if not input_data:
            return {
                "error": "Missing 'input' field",
                "code": "VALIDATION_ERROR"
            }
        
        # Validate input
        is_valid, error_msg, error_code = validate_input(input_data)
        if not is_valid:
            logger.warning(f"Request {request_id}: Validation failed - {error_msg}")
            return {
                "error": error_msg,
                "code": error_code
            }
        
        # Extract parameters
        topic = input_data["topic"]
        length = input_data["length"]
        tone = input_data["tone"]
        hook_style = input_data["hook_style"]
        max_tokens = input_data["max_tokens"]
        word_count = input_data.get("word_count")
        model = input_data.get("model")
        brand_name = input_data.get("brand_name", "Autopostai.Video")
        include_branding = input_data.get("include_branding", True)
        generate_voice_script = input_data.get("generate_voice_script", False)
        voice_script_style = input_data.get("voice_script_style")
        
        logger.info(f"Request {request_id}: Generating script for topic='{topic}', length={length}, tone={tone}")
        
        # Generate main script
        script, tokens_used = generate_script(
            topic=topic,
            length=length,
            tone=tone,
            hook_style=hook_style,
            max_tokens=max_tokens,
            word_count=word_count,
            model=model,
            brand_name=brand_name,
            include_branding=include_branding
        )
        
        # Extract hook
        hook = extract_hook(script)
        word_count_actual = count_words(script)
        
        # Build output
        output = {
            "script": script,
            "hook": hook,
            "word_count": word_count_actual,
            "estimated_duration": length,
            "tokens_used": tokens_used
        }
        
        # Generate voice script if requested
        if generate_voice_script:
            logger.info(f"Request {request_id}: Generating voice script")
            try:
                voice_script, voice_tokens = generate_voice_script(
                    topic=topic,
                    tone=tone,
                    voice_script_style=voice_script_style,
                    model=model,
                    brand_name=brand_name,
                    include_branding=include_branding
                )
                output["voice_script"] = voice_script
                output["voice_word_count"] = count_words(voice_script)
                tokens_used += voice_tokens
                output["tokens_used"] = tokens_used
            except Exception as e:
                logger.error(f"Request {request_id}: Voice script generation failed - {str(e)}")
                # Don't fail the entire request, just log the error
                output["voice_script_error"] = str(e)
        
        elapsed_time = time.time() - start_time
        logger.info(f"Request {request_id}: Completed in {elapsed_time:.2f}s, tokens={tokens_used}")
        
        # Modal returns output directly (no wrapping)
        return output
    
    except ValueError as e:
        logger.error(f"Request {request_id}: Validation error - {str(e)}")
        return {
            "error": str(e),
            "code": "VALIDATION_ERROR"
        }
    
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Request {request_id}: Error - {error_msg}")
        
        # Determine error code
        if "rate limit" in error_msg.lower() or "429" in error_msg:
            error_code = "RATE_LIMIT"
        elif "model" in error_msg.lower():
            error_code = "MODEL_ERROR"
        else:
            error_code = "INTERNAL_ERROR"
        
        return {
            "error": error_msg,
            "code": error_code
        }
