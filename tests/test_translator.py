"""Tests for translation batch logic (mocked API calls)."""

import json
from unittest.mock import patch, MagicMock

import pytest


# ──────────────────────────────────────────────────────────────
# Helpers: mock API responses
# ──────────────────────────────────────────────────────────────

def _gemini_response(translations: list[str]):
    """Build a fake Gemini response object (google-genai SDK)."""
    resp = MagicMock()
    resp.text = json.dumps(translations, ensure_ascii=False)
    return resp


def _openai_response(translations: list[str]):
    """Build a fake OpenAI response object."""
    resp = MagicMock()
    resp.choices = [MagicMock()]
    resp.choices[0].message.content = json.dumps(translations, ensure_ascii=False)
    return resp


# ──────────────────────────────────────────────────────────────
# translate_batch — Gemini provider (google-genai SDK)
# ──────────────────────────────────────────────────────────────

class TestTranslateGemini:
    @patch("app.services.translator.TRANSLATION_PROVIDER", "gemini")
    @patch("app.services.translator.GEMINI_API_KEY", "fake-key")
    @patch("app.services.translator.OPENAI_API_KEY", "")
    @patch("app.services.translator.genai")
    def test_basic_translation(self, mock_genai):
        from app.services.translator import translate_batch

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = _gemini_response(["你好", "世界"])
        mock_genai.Client.return_value = mock_client

        result = translate_batch(["Hello", "World"], source_lang="en")
        assert result == ["你好", "世界"]
        mock_genai.Client.assert_called_once_with(api_key="fake-key")

    @patch("app.services.translator.TRANSLATION_PROVIDER", "gemini")
    @patch("app.services.translator.GEMINI_API_KEY", "fake-key")
    @patch("app.services.translator.OPENAI_API_KEY", "")
    @patch("app.services.translator.genai")
    def test_count_mismatch_raises(self, mock_genai):
        """If API returns wrong number of translations, raise ValueError."""
        from app.services.translator import translate_batch

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = _gemini_response(["only_one"])
        mock_genai.Client.return_value = mock_client

        with pytest.raises(ValueError, match="Translation count mismatch"):
            translate_batch(["A", "B", "C"])

    @patch("app.services.translator.TRANSLATION_PROVIDER", "gemini")
    @patch("app.services.translator.GEMINI_API_KEY", "fake-key")
    @patch("app.services.translator.OPENAI_API_KEY", "backup-key")
    @patch("app.services.translator.genai")
    @patch("app.services.translator.OpenAI")
    def test_fallback_to_openai(self, mock_openai_cls, mock_genai):
        """Gemini fails → falls back to OpenAI if OPENAI_API_KEY is set."""
        from app.services.translator import translate_batch

        # Gemini raises
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = RuntimeError("Gemini down")
        mock_genai.Client.return_value = mock_client

        # OpenAI succeeds
        mock_openai_client = MagicMock()
        mock_openai_client.chat.completions.create.return_value = _openai_response(["你好"])
        mock_openai_cls.return_value = mock_openai_client

        result = translate_batch(["Hello"])
        assert result == ["你好"]

    @patch("app.services.translator.TRANSLATION_PROVIDER", "gemini")
    @patch("app.services.translator.GEMINI_API_KEY", "fake-key")
    @patch("app.services.translator.OPENAI_API_KEY", "")
    @patch("app.services.translator.genai")
    def test_gemini_fails_no_fallback_raises(self, mock_genai):
        """Gemini fails and no OpenAI key → re-raises exception."""
        from app.services.translator import translate_batch

        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = RuntimeError("API error")
        mock_genai.Client.return_value = mock_client

        with pytest.raises(RuntimeError, match="API error"):
            translate_batch(["Test"])

    @patch("app.services.translator.TRANSLATION_PROVIDER", "gemini")
    @patch("app.services.translator.GEMINI_API_KEY", "fake-key")
    @patch("app.services.translator.OPENAI_API_KEY", "")
    @patch("app.services.translator.genai")
    def test_markdown_fenced_response(self, mock_genai):
        """Gemini sometimes wraps JSON in markdown code fences."""
        from app.services.translator import translate_batch

        mock_client = MagicMock()
        resp = MagicMock()
        resp.text = '```json\n["翻译1", "翻译2"]\n```'
        mock_client.models.generate_content.return_value = resp
        mock_genai.Client.return_value = mock_client

        result = translate_batch(["Hello", "World"])
        assert result == ["翻译1", "翻译2"]


# ──────────────────────────────────────────────────────────────
# translate_batch — OpenAI provider
# ──────────────────────────────────────────────────────────────

class TestTranslateOpenAI:
    @patch("app.services.translator.TRANSLATION_PROVIDER", "openai")
    @patch("app.services.translator.GEMINI_API_KEY", "")
    @patch("app.services.translator.OPENAI_API_KEY", "sk-fake")
    @patch("app.services.translator.OpenAI")
    def test_basic_translation(self, mock_openai_cls):
        from app.services.translator import translate_batch

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _openai_response(["你好", "世界"])
        mock_openai_cls.return_value = mock_client

        result = translate_batch(["Hello", "World"], source_lang="en")
        assert result == ["你好", "世界"]

    @patch("app.services.translator.TRANSLATION_PROVIDER", "openai")
    @patch("app.services.translator.GEMINI_API_KEY", "backup-key")
    @patch("app.services.translator.OPENAI_API_KEY", "sk-fake")
    @patch("app.services.translator.OpenAI")
    @patch("app.services.translator.genai")
    def test_fallback_to_gemini(self, mock_genai, mock_openai_cls):
        """OpenAI fails → falls back to Gemini if GEMINI_API_KEY is set."""
        from app.services.translator import translate_batch

        mock_openai_client = MagicMock()
        mock_openai_client.chat.completions.create.side_effect = RuntimeError("OpenAI down")
        mock_openai_cls.return_value = mock_openai_client

        mock_gemini_client = MagicMock()
        mock_gemini_client.models.generate_content.return_value = _gemini_response(["你好"])
        mock_genai.Client.return_value = mock_gemini_client

        result = translate_batch(["Hello"])
        assert result == ["你好"]

    @patch("app.services.translator.TRANSLATION_PROVIDER", "openai")
    @patch("app.services.translator.GEMINI_API_KEY", "")
    @patch("app.services.translator.OPENAI_API_KEY", "sk-fake")
    @patch("app.services.translator.OpenAI")
    def test_count_mismatch_raises(self, mock_openai_cls):
        from app.services.translator import translate_batch

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _openai_response(["one"])
        mock_openai_cls.return_value = mock_client

        with pytest.raises(ValueError, match="Translation count mismatch"):
            translate_batch(["A", "B"])


# ──────────────────────────────────────────────────────────────
# translate_batch — unsupported provider
# ──────────────────────────────────────────────────────────────

class TestUnsupportedProvider:
    @patch("app.services.translator.TRANSLATION_PROVIDER", "azure")
    @patch("app.services.translator.GEMINI_API_KEY", "")
    @patch("app.services.translator.OPENAI_API_KEY", "")
    def test_unsupported_raises(self):
        from app.services.translator import translate_batch

        with pytest.raises(ValueError, match="Unsupported translation provider"):
            translate_batch(["Test"])


# ──────────────────────────────────────────────────────────────
# Source language handling
# ──────────────────────────────────────────────────────────────

class TestSourceLanguage:
    @patch("app.services.translator.TRANSLATION_PROVIDER", "gemini")
    @patch("app.services.translator.GEMINI_API_KEY", "fake-key")
    @patch("app.services.translator.OPENAI_API_KEY", "")
    @patch("app.services.translator.genai")
    def test_japanese_source(self, mock_genai):
        """Japanese source should map to '日语' in the prompt."""
        from app.services.translator import translate_batch

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = _gemini_response(["你好"])
        mock_genai.Client.return_value = mock_client

        translate_batch(["こんにちは"], source_lang="ja")
        prompt_arg = mock_client.models.generate_content.call_args[1]["contents"]
        assert "日语" in prompt_arg

    @patch("app.services.translator.TRANSLATION_PROVIDER", "gemini")
    @patch("app.services.translator.GEMINI_API_KEY", "fake-key")
    @patch("app.services.translator.OPENAI_API_KEY", "")
    @patch("app.services.translator.genai")
    def test_korean_source(self, mock_genai):
        """Korean source should map to '韩语' in the prompt."""
        from app.services.translator import translate_batch

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = _gemini_response(["你好"])
        mock_genai.Client.return_value = mock_client

        translate_batch(["안녕하세요"], source_lang="ko")
        prompt_arg = mock_client.models.generate_content.call_args[1]["contents"]
        assert "韩语" in prompt_arg
