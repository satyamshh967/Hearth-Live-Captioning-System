from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from pydantic import BaseModel


class AddressedAlert(BaseModel):
    addressed_to_user: bool
    confidence: float
    user_vocative_used: str
    urgency: str = "medium" # low, medium, high
    reasoning: Optional[str] = None


class QuickReply(BaseModel):
    label: str
    text: str


class QuestionReplies(BaseModel):
    is_question: bool
    replies: List[QuickReply] = []


class CatchupRecap(BaseModel):
    recap: str
    key_topic: str
    speakers_involved: List[str] = []


class PlainLanguageResult(BaseModel):
    original_text: str
    plain_text: str
    key_terms_explained: List[Dict[str, str]] = []


class MemoryItem(BaseModel):
    category: str
    title: str
    detail: str
    time_or_date: Optional[str] = None


class LLMProvider(ABC):
    @abstractmethod
    async def check_addressed_to_me(self, text: str, user_names: List[str]) -> AddressedAlert:
        """Check if speech is addressed directly to user vs spoken about them in third person."""
        pass

    @abstractmethod
    async def detect_question_and_replies(self, text: str, friend_name: str, tone_profile: str) -> QuestionReplies:
        """Detect question and generate 3 quick replies in friend's tone."""
        pass

    @abstractmethod
    async def generate_catchup_recap(self, transcript_lines: List[Dict]) -> CatchupRecap:
        """Generate 2-sentence catch-up recap of the last 60-90 seconds."""
        pass

    @abstractmethod
    async def simplify_plain_language(self, text: str) -> PlainLanguageResult:
        """Simplify medical/complex terms for doctor visit mode."""
        pass

    @abstractmethod
    async def extract_memories(self, transcript_lines: List[Dict]) -> List[MemoryItem]:
        """Extract actionable things to remember (medicines, dates, appointments)."""
        pass
