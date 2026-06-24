"""Translation service using Gemini (primary) / OpenAI (fallback)"""

import json
import google.generativeai as genai
from openai import OpenAI

from app.config import (
    TRANSLATION_PROVIDER,
    GEMINI_API_KEY,
    OPENAI_API_KEY,
)

TRANSLATION_PROMPT = """你是专业影视字幕翻译专家。

要求：
1 保留人物语气
2 保留动漫/影视术语
3 不要解释，只输出翻译
4 返回 JSON 数组，保持顺序一致
5 每条翻译不超过15个中文字符
6 如果原文是语气词/感叹词，翻译成对应的中文语气词

输入：
{input_json}

返回格式：["翻译1", "翻译2", ...]"""


def translate_batch(texts: list[str], source_lang: str = "ja") -> list[str]:
    """
    Batch translate texts to Chinese.
    Falls back to secondary provider on failure.
    """
    if TRANSLATION_PROVIDER == "gemini":
        try:
            return _translate_gemini(texts, source_lang)
        except Exception as e:
            if OPENAI_API_KEY:
                return _translate_openai(texts, source_lang)
            raise
    elif TRANSLATION_PROVIDER == "openai" and OPENAI_API_KEY:
        try:
            return _translate_openai(texts, source_lang)
        except Exception as e:
            if GEMINI_API_KEY:
                return _translate_gemini(texts, source_lang)
            raise
    else:
        raise ValueError(f"Unsupported translation provider: {TRANSLATION_PROVIDER}")


def _translate_gemini(texts: list[str], source_lang: str) -> list[str]:
    """Translate using Gemini API."""
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.5-flash")

    lang_map = {"ja": "日语", "en": "英语", "ko": "韩语"}
    lang_name = lang_map.get(source_lang, source_lang)

    prompt = TRANSLATION_PROMPT.format(
        input_json=json.dumps(texts, ensure_ascii=False)
    )
    prompt = prompt.replace("字幕翻译专家", f"字幕翻译专家，将{lang_name}翻译为中文")

    response = model.generate_content(prompt)
    result_text = response.text.strip()

    # Parse JSON from response
    if result_text.startswith("```"):
        result_text = result_text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    translations = json.loads(result_text)

    if len(translations) != len(texts):
        raise ValueError(
            f"Translation count mismatch: expected {len(texts)}, got {len(translations)}"
        )

    return translations


def _translate_openai(texts: list[str], source_lang: str) -> list[str]:
    """Translate using OpenAI API."""
    client = OpenAI(api_key=OPENAI_API_KEY)

    lang_map = {"ja": "日语", "en": "英语", "ko": "韩语"}
    lang_name = lang_map.get(source_lang, source_lang)

    prompt = TRANSLATION_PROMPT.format(
        input_json=json.dumps(texts, ensure_ascii=False)
    )
    prompt = prompt.replace("字幕翻译专家", f"字幕翻译专家，将{lang_name}翻译为中文")

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )

    result_text = response.choices[0].message.content.strip()
    if result_text.startswith("```"):
        result_text = result_text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    translations = json.loads(result_text)

    if len(translations) != len(texts):
        raise ValueError(
            f"Translation count mismatch: expected {len(texts)}, got {len(translations)}"
        )

    return translations
