"""
Hearth Profile Management
Provides local domain-specific profiles (Family, Work, Clinic, Default)
to bias ASR vocabulary, protect terminology during MT translation,
and configure personalized alert triggers without hardcoding personal data.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel, Field


class Profile(BaseModel):
    id: str
    name: str
    description: str
    vocabulary: List[str] = Field(default_factory=list)
    protected_terms: List[str] = Field(default_factory=list)
    vocative_triggers: List[str] = Field(default_factory=list)
    preferred_source_lang: Optional[str] = "en"
    preferred_target_lang: Optional[str] = "es"

    def get_prompt_biasing_string(self) -> str:
        """Returns comma-separated string for ASR prompt biasing."""
        return ", ".join(self.vocabulary)

    def protect_terms_in_text(self, text: str) -> Tuple[str, Dict[str, str]]:
        """Replaces protected terms with placeholder tokens before translation."""
        import re
        placeholders = {}
        processed_text = text
        for idx, term in enumerate(self.protected_terms):
            token = f"__TERM_{idx}__"
            pattern = re.compile(re.escape(term), re.IGNORECASE)
            if pattern.search(processed_text):
                placeholders[token] = term
                processed_text = pattern.sub(token, processed_text)
        return processed_text, placeholders

    def restore_protected_terms(self, text: str, placeholders: Dict[str, str]) -> str:
        """Restores protected terms from placeholder tokens after translation."""
        restored = text
        for token, term in placeholders.items():
            restored = restored.replace(token, term)
        return restored


DEFAULT_PROFILES = {
    "default": Profile(
        id="default",
        name="Default (General)",
        description="Everyday conversational speech with standard vocabulary.",
        vocabulary=[
            "Hello", "Thank you", "Please", "Welcome", "Excuse me", "Yes", "No",
            "Tomorrow", "Today", "Meeting", "Family", "Coffee", "Water"
        ],
        protected_terms=[],
        vocative_triggers=["hey", "listen", "excuse me"],
        preferred_source_lang="en",
        preferred_target_lang="es",
    ),
    "family": Profile(
        id="family",
        name="Family Table",
        description="Tailored for family dinners, household conversations, and relatives.",
        vocabulary=[
            "Grandma", "Grandpa", "Uncle", "Aunt", "Mom", "Dad", "Brother", "Sister",
            "Dinner", "Recipe", "Tea", "Chai", "Water", "Plate", "Dessert", "Medicine"
        ],
        protected_terms=["Grandma", "Grandpa", "Chai"],
        vocative_triggers=["grandpa", "grandma", "dad", "mom", "listen"],
        preferred_source_lang="en",
        preferred_target_lang="hi",
    ),
    "work": Profile(
        id="work",
        name="Workplace / Meeting",
        description="Technical discussions, product syncs, engineering and office terminology.",
        vocabulary=[
            "Sprint", "Standup", "API", "Frontend", "Backend", "Pull Request",
            "Deployment", "Kubernetes", "Database", "Latency", "Architecture", "Roadmap"
        ],
        protected_terms=["API", "Kubernetes", "Hearth", "WebSocket"],
        vocative_triggers=["hey", "question", "quick question"],
        preferred_source_lang="en",
        preferred_target_lang="de",
    ),
    "clinic": Profile(
        id="clinic",
        name="Medical / Clinic Visit",
        description="Doctor consultations, prescription dosages, vitals and diagnoses.",
        vocabulary=[
            "Blood pressure", "Hypertension", "Presbycusis", "Hearing loss", "Edema",
            "Prescription", "Metformin", "Atorvastatin", "Dosage", "Milligrams", "Cardiologist"
        ],
        protected_terms=["Metformin", "Atorvastatin", "Telmisartan", "mg", "BP"],
        vocative_triggers=["doctor", "nurse", "patient"],
        preferred_source_lang="en",
        preferred_target_lang="es",
    ),
}


class ProfileManager:
    def __init__(self, profiles_dir: str = "profiles"):
        self.profiles_dir = Path(profiles_dir)
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        self.profiles: Dict[str, Profile] = {}
        self.active_profile_id: str = "default"
        self._init_profiles()

    def _init_profiles(self):
        # Save default templates if they don't exist
        for pid, pobj in DEFAULT_PROFILES.items():
            pfile = self.profiles_dir / f"{pid}.yaml"
            if not pfile.exists():
                with open(pfile, "w", encoding="utf-8") as f:
                    yaml.dump(pobj.model_dump(), f, sort_keys=False)

        # Load all profiles from disk
        self.load_all()

    def load_all(self):
        self.profiles = {}
        for pfile in self.profiles_dir.glob("*.yaml"):
            try:
                with open(pfile, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    prof = Profile(**data)
                    self.profiles[prof.id] = prof
            except Exception:
                pass

        if not self.profiles:
            self.profiles = dict(DEFAULT_PROFILES)

        if self.active_profile_id not in self.profiles:
            self.active_profile_id = next(iter(self.profiles.keys()), "default")

    def get_active_profile(self) -> Profile:
        return self.profiles.get(self.active_profile_id, DEFAULT_PROFILES["default"])

    def set_active_profile(self, profile_id: str) -> bool:
        if profile_id in self.profiles:
            self.active_profile_id = profile_id
            return True
        return False

    def list_profiles(self) -> List[Dict]:
        return [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "vocab_count": len(p.vocabulary),
                "is_active": p.id == self.active_profile_id,
            }
            for p in self.profiles.values()
        ]

    def add_word_to_active_profile(self, word: str) -> bool:
        prof = self.get_active_profile()
        if word and word not in prof.vocabulary:
            prof.vocabulary.append(word)
            pfile = self.profiles_dir / f"{prof.id}.yaml"
            with open(pfile, "w", encoding="utf-8") as f:
                yaml.dump(prof.model_dump(), f, sort_keys=False)
            return True
        return False
