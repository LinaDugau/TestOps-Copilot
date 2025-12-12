import os
from openai import AsyncOpenAI
from typing import List, Dict
from dotenv import load_dotenv
import traceback

load_dotenv()

DEFAULT_MODEL = "Qwen/Qwen3-Next-80B-A3B-Instruct"

api_key = (
    os.getenv("CLOUD_RU_API_KEY") or
    os.getenv("API_KEY") or
    os.getenv("OPENAI_API_KEY")
)

if not api_key:
    raise OSError("Static API Key не найден! Сгенерируй в Cloud.ru Console → API Keys (Bearer token)")

client = AsyncOpenAI(
    api_key=api_key,
    base_url="https://foundation-models.api.cloud.ru/v1",
    timeout=90.0,
    max_retries=3,  
    default_headers={"Authorization": f"Bearer {api_key}"},  
)

async def call_evolution(
    messages: List[Dict[str, str]],
    temperature: float = 0.0,
    max_tokens: int = 2000,
    model: str | None = None,
) -> str:
    """
    Вызов Cloud.ru Evolution Foundation Model (Qwen 3 Next 80B).
    OpenAI-compatible API по документации.
    """
    target_model = model or os.getenv("CLOUD_RU_MODEL") or DEFAULT_MODEL

    try:
        print(f"Вызов модели: {target_model} (Static API Key: {'найден' if api_key else 'НЕ НАЙДЕН'})")

        response = await client.chat.completions.create(
            model=target_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=0.95,
            presence_penalty=0.0,
            frequency_penalty=0.0,
        )
        content = response.choices[0].message.content
        if content is None:
            raise ValueError("Пустой ответ от модели")
        return content.strip()
    except ValueError:
        raise
    except Exception as e:
        error_msg = f"Cloud.ru API error: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        if "model" in str(e).lower() and target_model != DEFAULT_MODEL:
            print(f"Fallback на {DEFAULT_MODEL}...")
            return await call_evolution(messages, temperature, max_tokens, model=DEFAULT_MODEL)
        raise Exception(error_msg)