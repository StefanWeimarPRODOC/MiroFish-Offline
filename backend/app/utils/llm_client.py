"""
LLM Client Wrapper
Unified OpenAI format API calls with token counting and call logging.
Supports Ollama num_ctx parameter to prevent prompt truncation.
"""

import json
import logging
import os
import re
import time
from typing import Optional, Dict, Any, List
from openai import OpenAI

from ..config import Config

logger = logging.getLogger('mirofish.llm')


class LLMClient:
    """LLM Client with token counting and call logging."""

    # Global token counters (accumulated across all instances)
    _token_counts = {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "call_count": 0,
    }
    _phase_snapshots: Dict[str, dict] = {}

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 300.0
    ):
        self.api_key = api_key or Config.LLM_API_KEY
        self.base_url = base_url or Config.LLM_BASE_URL
        self.model = model or Config.LLM_MODEL_NAME

        if not self.api_key:
            raise ValueError("LLM_API_KEY not configured")

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=timeout,
        )

        # Ollama context window size — prevents prompt truncation.
        # Read from env OLLAMA_NUM_CTX, default 8192 (Ollama default is only 2048).
        self._num_ctx = int(os.environ.get('OLLAMA_NUM_CTX', '8192'))

    def _is_ollama(self) -> bool:
        """Check if we're talking to an Ollama server."""
        return '11434' in (self.base_url or '')

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[Dict] = None
    ) -> str:
        """
        Send chat request

        Args:
            messages: Message list
            temperature: Temperature parameter
            max_tokens: Max token count
            response_format: Response format (e.g., JSON mode)

        Returns:
            Model response text
        """
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if response_format:
            kwargs["response_format"] = response_format

        # For Ollama: pass num_ctx via extra_body to prevent prompt truncation,
        # and keep_alive so the model stays in RAM between calls (avoids re-load
        # latency when embedding requests evict it under LRU pressure).
        if self._is_ollama() and self._num_ctx:
            kwargs["extra_body"] = {
                "options": {"num_ctx": self._num_ctx},
                "keep_alive": Config.OLLAMA_KEEP_ALIVE,
            }

        start_time = time.monotonic()
        response = self.client.chat.completions.create(**kwargs)
        duration_ms = int((time.monotonic() - start_time) * 1000)

        content = response.choices[0].message.content

        # Track token usage
        prompt_tok = 0
        completion_tok = 0
        if response.usage:
            prompt_tok = response.usage.prompt_tokens or 0
            completion_tok = response.usage.completion_tokens or 0
            LLMClient._token_counts["prompt_tokens"] += prompt_tok
            LLMClient._token_counts["completion_tokens"] += completion_tok
            LLMClient._token_counts["total_tokens"] += response.usage.total_tokens or 0
            LLMClient._token_counts["call_count"] += 1
        else:
            LLMClient._token_counts["call_count"] += 1
            logger.warning("Missing usage data in LLM response")

        # Strip thinking tags from various model formats
        thinking_stripped = False
        if content and ('<think>' in content or '<|channel>thought' in content):
            thinking_stripped = True
        content = re.sub(r'<think>[\s\S]*?</think>', '', content).strip()
        content = re.sub(r'<\|channel>thought[\s\S]*?<channel\|>', '', content).strip()

        # Call logging
        logger.debug(
            "model=%s temp=%.1f duration=%dms p=%dtok c=%dtok chars=%d thinking_stripped=%s",
            self.model, temperature, duration_ms,
            prompt_tok, completion_tok, len(content) if content else 0,
            str(thinking_stripped).lower()
        )

        if not content:
            logger.warning("Empty response from LLM (model=%s)", self.model)

        return content

    def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096
    ) -> Dict[str, Any]:
        """
        Send chat request and return JSON

        Args:
            messages: Message list
            temperature: Temperature parameter
            max_tokens: Max token count

        Returns:
            Parsed JSON object
        """
        response = self.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"}
        )
        # Clean markdown code block markers
        cleaned_response = response.strip()
        cleaned_response = re.sub(r'^```(?:json)?\s*\n?', '', cleaned_response, flags=re.IGNORECASE)
        cleaned_response = re.sub(r'\n?```\s*$', '', cleaned_response)
        cleaned_response = cleaned_response.strip()

        try:
            parsed = json.loads(cleaned_response)
        except json.JSONDecodeError:
            logger.warning("JSON parse failed (model=%s, chars=%d)", self.model, len(cleaned_response))
            raise ValueError(f"Invalid JSON format from LLM: {cleaned_response}")

        # Some models produce keys with leading/trailing whitespace or newlines
        if isinstance(parsed, dict):
            parsed = {k.strip(): v for k, v in parsed.items()}
        return parsed

    # --- Token counting API ---

    @classmethod
    def get_token_counts(cls) -> dict:
        """Return current accumulated token counts."""
        return dict(cls._token_counts)

    @classmethod
    def reset_token_counts(cls):
        """Reset all token counters to zero."""
        cls._token_counts = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "call_count": 0,
        }
        cls._phase_snapshots = {}

    @classmethod
    def record_usage(cls, usage):
        """Record token usage from an external OpenAI-compatible response."""
        if usage:
            cls._token_counts["prompt_tokens"] += usage.prompt_tokens or 0
            cls._token_counts["completion_tokens"] += usage.completion_tokens or 0
            cls._token_counts["total_tokens"] += usage.total_tokens or 0
        cls._token_counts["call_count"] += 1

    # --- Phase tracking ---

    @classmethod
    def start_phase(cls, phase_name: str):
        """Snapshot token counts at phase start."""
        cls._phase_snapshots[phase_name] = dict(cls._token_counts)

    @classmethod
    def end_phase(cls, phase_name: str) -> dict:
        """Calculate tokens consumed during phase."""
        start = cls._phase_snapshots.pop(phase_name, None)
        if not start:
            return {}
        return {
            "prompt_tokens": cls._token_counts["prompt_tokens"] - start["prompt_tokens"],
            "completion_tokens": cls._token_counts["completion_tokens"] - start["completion_tokens"],
            "total_tokens": cls._token_counts["total_tokens"] - start["total_tokens"],
            "call_count": cls._token_counts["call_count"] - start["call_count"],
        }
