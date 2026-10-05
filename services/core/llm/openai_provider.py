import json
import logging
from typing import List, Dict, Optional
import httpx
from .provider import (
    LLMProvider, AddressedAlert, QuestionReplies, QuickReply,
    CatchupRecap, PlainLanguageResult, MemoryItem
)
from .rule_fallback import RuleBasedLLMFallback
from ..config import LLMConfig

logger = logging.getLogger(__name__)


class OpenAILocalLLMProvider(LLMProvider):
    """
    Client for local open-weight models served via OpenAI-compatible endpoints
    (Ollama, llama.cpp, vLLM, LocalAI).
    Enforces JSON outputs, strict timeout, and seamless fallback to RuleBasedLLMFallback.
    """
    def __init__(self, config: LLMConfig):
        self.config = config
        self.fallback = RuleBasedLLMFallback()
        self.client = httpx.AsyncClient(timeout=config.timeout_sec)

    async def _call_chat_completion(self, system_prompt: str, user_prompt: str) -> Optional[dict]:
        url = f"{self.config.endpoint.rstrip('/')}/chat/completions"
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": self.config.temperature,
            "response_format": {"type": "json_object"}
        }
        try:
            resp = await self.client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                return json.loads(content)
        except Exception as e:
            logger.debug(f"Local LLM call failed or timed out: {e}; switching to rule fallback.")
        return None

    async def check_addressed_to_me(self, text: str, user_names: List[str]) -> AddressedAlert:
        prompt_sys = (
            "You are an intent classifier for Hearth assistive captioning. "
            f"Detect if the speaker is directly talking TO the user (addressed by any of these names/vocatives: {', '.join(user_names)}) "
            "or talking ABOUT them to someone else in third person. "
            "Output JSON: {\"addressed_to_user\": bool, \"confidence\": float, \"user_vocative_used\": str, \"urgency\": \"low\"|\"medium\"|\"high\", \"reasoning\": str}"
        )
        res = await self._call_chat_completion(prompt_sys, text)
        if res and "addressed_to_user" in res:
            try:
                return AddressedAlert(**res)
            except Exception:
                pass
        return await self.fallback.check_addressed_to_me(text, user_names)

    async def detect_question_and_replies(self, text: str, friend_name: str, tone_profile: str) -> QuestionReplies:
        prompt_sys = (
            f"You are an assistive dialog assistant for {friend_name or 'the user'} whose tone is {tone_profile}. "
            "If the input is a question or requires a response, output JSON with 3 quick natural replies: "
            "{\"is_question\": bool, \"replies\": [{\"label\": str, \"text\": str}]}"
        )
        res = await self._call_chat_completion(prompt_sys, text)
        if res and "is_question" in res:
            try:
                return QuestionReplies(**res)
            except Exception:
                pass
        return await self.fallback.detect_question_and_replies(text, friend_name, tone_profile)

    async def generate_catchup_recap(self, transcript_lines: List[Dict]) -> CatchupRecap:
        prompt_sys = (
            "You are an assistive conversational summarizer. "
            "Given the transcript lines, provide a clear 2-sentence conversational recap highlighting speakers and decisions. "
            "Output JSON: {\"recap\": str, \"key_topic\": str, \"speakers_involved\": [str]}"
        )
        transcript_str = "\n".join(f"[{l.get('speaker', 'Unknown')}]: {l.get('text', '')}" for l in transcript_lines)
        res = await self._call_chat_completion(prompt_sys, transcript_str)
        if res and "recap" in res:
            try:
                return CatchupRecap(**res)
            except Exception:
                pass
        return await self.fallback.generate_catchup_recap(transcript_lines)

    async def simplify_plain_language(self, text: str) -> PlainLanguageResult:
        prompt_sys = (
            "You are an assistive accessibility plain-language translator. "
            "Translate technical or medical terminology into simple, reassuring everyday language without losing dosage/timing details. "
            "Output JSON: {\"original_text\": str, \"plain_text\": str, \"key_terms_explained\": [{\"term\": str, \"simple_meaning\": str}]}"
        )
        res = await self._call_chat_completion(prompt_sys, text)
        if res and "plain_text" in res:
            try:
                res["original_text"] = text
                return PlainLanguageResult(**res)
            except Exception:
                pass
        return await self.fallback.simplify_plain_language(text)

    async def extract_memories(self, transcript_lines: List[Dict]) -> List[MemoryItem]:
        prompt_sys = (
            "Analyze the conversation transcript and extract only actionable commitments, medicines, or appointments. "
            "Output JSON: {\"items\": [{\"category\": str, \"title\": str, \"detail\": str, \"time_or_date\": str}]}"
        )
        transcript_str = "\n".join(f"[{l.get('speaker', 'Unknown')}]: {l.get('text', '')}" for l in transcript_lines)
        res = await self._call_chat_completion(prompt_sys, transcript_str)
        if res and "items" in res:
            try:
                return [MemoryItem(**i) for i in res["items"]]
            except Exception:
                pass
        return await self.fallback.extract_memories(transcript_lines)
