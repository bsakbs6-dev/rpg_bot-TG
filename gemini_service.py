import asyncio
import logging
import re
from typing import List, Dict, Optional
import httpx
from google import genai
from google.genai import types
from google.genai.errors import ServerError, ClientError, APIError

from config import GEMINI_API_KEY, GEMINI_MODELS, OPENROUTER_API_KEY, OPENROUTER_MODELS

logger = logging.getLogger(__name__)

# Initialize Google client
client = genai.Client(api_key=GEMINI_API_KEY)

# Strict Russian language enforcement rule
RUSSIAN_LANGUAGE_RULE = (
    "\n\nЯЗЫКОВОЕ ПРАВИЛО (СТРОГО): Отвечай ИСКЛЮЧИТЕЛЬНО на грамотном русском языке. "
    "Категорически запрещено использовать английские слова, китайские иероглифы, арабскую вязь "
    "или другие иностранные языки. Все фразы, мысли, действия в звездочках и стоны пиши только по-русски!"
)

# Regex to detect unwanted Asian/Arabic scripts
FOREIGN_SCRIPTS_REGEX = re.compile(r'[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af\u0600-\u06ff]')

# Define safety settings allowing maximum roleplay freedom (BLOCK_NONE)
SAFETY_SETTINGS = [
    types.SafetySetting(category='HARM_CATEGORY_HARASSMENT', threshold='BLOCK_NONE'),
    types.SafetySetting(category='HARM_CATEGORY_HATE_SPEECH', threshold='BLOCK_NONE'),
    types.SafetySetting(category='HARM_CATEGORY_SEXUALLY_EXPLICIT', threshold='BLOCK_NONE'),
    types.SafetySetting(category='HARM_CATEGORY_DANGEROUS_CONTENT', threshold='BLOCK_NONE'),
    types.SafetySetting(category='HARM_CATEGORY_CIVIC_INTEGRITY', threshold='BLOCK_NONE'),
]

def sanitize_response(text: str) -> Optional[str]:
    """Checks and cleans response to ensure pure Russian text without foreign scripts."""
    if not text:
        return None
    # If the response contains Chinese/Arabic/Korean characters, reject it
    if FOREIGN_SCRIPTS_REGEX.search(text):
        logger.warning("Detected foreign script (Chinese/Arabic) in response, rejecting...")
        return None
    return text.strip()

async def _call_openrouter(
    system_instruction: str,
    history: List[Dict[str, str]],
    user_message: str
) -> Optional[str]:
    """Fallback to OpenRouter for uncensored 18+ content or when Gemini is overloaded."""
    if not OPENROUTER_API_KEY:
        return None

    full_system = system_instruction + RUSSIAN_LANGUAGE_RULE

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://t.me/role_hnt_bot",
        "X-Title": "Roleplay Bot",
        "Content-Type": "application/json"
    }

    messages = [{"role": "system", "content": full_system}]
    # OpenRouter free models work best with up to 60 recent messages
    recent_history = history[-60:] if len(history) > 60 else history
    for h in recent_history:
        role = "assistant" if h["role"] == "model" else "user"
        messages.append({"role": role, "content": h["content"]})
    messages.append({"role": "user", "content": user_message})

    async with httpx.AsyncClient(timeout=20.0) as http_client:
        for model_name in OPENROUTER_MODELS:
            try:
                logger.info(f"Generating roleplay with OpenRouter model: {model_name}")
                payload = {
                    "model": model_name,
                    "messages": messages,
                    "temperature": 0.85
                }
                response = await http_client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=payload
                )
                if response.status_code == 200:
                    data = response.json()
                    choices = data.get("choices", [])
                    if choices and choices[0].get("message", {}).get("content"):
                        reply = choices[0]["message"]["content"]
                        clean_reply = sanitize_response(reply)
                        if clean_reply:
                            return clean_reply
                else:
                    logger.warning(f"OpenRouter model {model_name} returned {response.status_code}: {response.text[:100]}")
            except Exception as e:
                logger.warning(f"OpenRouter exception on {model_name}: {e}")
                await asyncio.sleep(0.5)
                continue

    return None

async def generate_roleplay_reply(
    system_instruction: str,
    history: List[Dict[str, str]],
    user_message: str
) -> Optional[str]:
    """
    Generates a roleplay reply.
    1. Tries Google Gemini API first.
    2. If Gemini blocks (SAFETY filter) or returns error (503/429/400),
       it immediately falls back to OpenRouter (Uncensored).
    """
    full_system = system_instruction + RUSSIAN_LANGUAGE_RULE

    # Build contents list for Gemini
    contents: List[types.Content] = []
    for item in history:
        role = "user" if item["role"] == "user" else "model"
        contents.append(
            types.Content(
                role=role,
                parts=[types.Part.from_text(text=item["content"])]
            )
        )
    contents.append(
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=user_message)]
        )
    )

    config = types.GenerateContentConfig(
        system_instruction=full_system,
        safety_settings=SAFETY_SETTINGS,
        temperature=0.85
    )

    # 1. Attempt Gemini models
    for model_name in GEMINI_MODELS:
        try:
            logger.info(f"Generating roleplay with Gemini model: {model_name}")
            response = await client.aio.models.generate_content(
                model=model_name,
                contents=contents,
                config=config
            )

            # Check for candidate finish reason (e.g. SAFETY block)
            if response.candidates and response.candidates[0].finish_reason:
                reason = str(response.candidates[0].finish_reason)
                if "SAFETY" in reason:
                    logger.info("Gemini hit SAFETY filter. Falling back to OpenRouter for uncensored RP...")
                    or_reply = await _call_openrouter(system_instruction, history, user_message)
                    if or_reply:
                        return or_reply

            if response.text and response.text.strip():
                clean = sanitize_response(response.text)
                if clean:
                    return clean
            
            if response.candidates and response.candidates[0].content:
                parts = response.candidates[0].content.parts or []
                extracted = "".join(p.text for p in parts if getattr(p, "text", None))
                clean = sanitize_response(extracted)
                if clean:
                    return clean

        except (ServerError, ClientError, APIError) as e:
            logger.warning(f"Error with Gemini {model_name}: {e}. Retrying next...")
            await asyncio.sleep(0.3)
            continue
        except Exception as e:
            logger.exception(f"Unexpected error with Gemini {model_name}: {e}")
            await asyncio.sleep(0.3)
            continue

    # 2. If Gemini models failed or blocked, fall back to OpenRouter
    logger.info("Gemini unavailable. Switching to OpenRouter (Uncensored)...")
    or_reply = await _call_openrouter(system_instruction, history, user_message)
    if or_reply:
        return or_reply

    return None
