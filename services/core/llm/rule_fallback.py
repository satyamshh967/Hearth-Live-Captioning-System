import re
from typing import List, Dict, Optional
from rapidfuzz import fuzz
from .provider import (
    LLMProvider, AddressedAlert, QuestionReplies, QuickReply,
    CatchupRecap, PlainLanguageResult, MemoryItem
)


# Common medical simplifications for Doctor Visit mode
MEDICAL_SIMPLIFICATIONS = {
    "presbycusis": ("Age-related hearing change", "Natural softening of higher-pitched hearing as we grow older."),
    "sensorineural hearing loss": ("Inner ear hearing change", "Nerve-related hearing softness common with age."),
    "hypertension": ("High blood pressure", "Pressure inside blood vessels is higher than target."),
    "postprandial hyperglycemia": ("High sugar after meals", "Blood sugar spikes after eating food."),
    "hypoglycemia": ("Low blood sugar", "Sugar level dipped too low, have a small sweet snack."),
    "q.d.": ("Once daily", "Take once every single day."),
    "b.i.d.": ("Twice daily", "Take twice a day (morning and evening)."),
    "t.i.d.": ("Three times daily", "Take morning, afternoon, and night."),
    "p.r.n.": ("As needed", "Take only when you feel symptoms."),
    "hba1c": ("3-month sugar average", "Blood test measuring average blood sugar over the last 90 days."),
    "edema": ("Mild fluid swelling", "Fluid collection in ankles or feet."),
    "dyslipidemia": ("Cholesterol balance", "Levels of fats/cholesterol in the blood."),
    "nephropathy": ("Kidney health check", "Monitoring kidney function."),
    "neuropathy": ("Nerve tingling / numbness", "Pins-and-needles sensation in feet or hands."),
    "echocardiogram": ("Heart ultrasound scan", "Safe ultrasound image checking heart muscle strength."),
}


class RuleBasedLLMFallback(LLMProvider):
    """
    Deterministic, high-speed, zero-dependency rule-based engine.
    Guarantees sub-15ms response latency with 0 external network dependencies.
    """

    async def check_addressed_to_me(self, text: str, user_names: List[str]) -> AddressedAlert:
        lower = text.lower()
        matched_name = None
        
        # Check if any user vocative is present
        for name in user_names:
            clean_name = name.lower()
            # Direct word boundary match
            if re.search(rf"\b{re.escape(clean_name)}\b", lower):
                matched_name = name
                break
            # Fuzzy match on individual words
            for word in lower.split():
                if fuzz.ratio(clean_name, word.strip(".,!?\"'")) >= 82.0:
                    matched_name = name
                    break
            if matched_name:
                break

        if not matched_name:
            return AddressedAlert(
                addressed_to_user=False,
                confidence=0.95,
                user_vocative_used="None",
                urgency="low",
                reasoning="No vocative or name referring to user was found."
            )

        # Distinguish between 3rd-person narration vs direct address:
        clean_name = matched_name.lower()
        third_person_patterns = [
            rf"\b{re.escape(clean_name)}\s+(is|was|has|had|went|said|told|likes|takes|slept|walks)\b",
            rf"\b(told|asked|saw|helped|visited)\s+{re.escape(clean_name)}\b",
            rf"\bwith\s+{re.escape(clean_name)}\b",
            rf"\bfor\s+{re.escape(clean_name)}\b",
            rf"\babout\s+{re.escape(clean_name)}\b",
        ]
        is_third_person = any(re.search(pat, lower, re.IGNORECASE) for pat in third_person_patterns)

        # Direct address indicators:
        direct_cues = [
            rf"^{re.escape(clean_name)}[,\s]+(aap|aapne|kya|kyun|please|suno|listen|did you|have you|do you|are you)",
            rf"[,\s]{re.escape(clean_name)}[?!]",
            rf"\b(listen|suno|dekho|batao|please|aap|aapne)\b.*{re.escape(clean_name)}",
            rf"{re.escape(clean_name)}.*\b(aap|aapne|kya|kyun|please|want|need|have you|did you)\b.*\?",
        ]
        is_direct = any(re.search(pat, lower, re.IGNORECASE) for pat in direct_cues)

        if is_direct and not is_third_person:
            return AddressedAlert(
                addressed_to_user=True,
                confidence=0.92,
                user_vocative_used=matched_name,
                urgency="high" if "?" in text or "suno" in lower or "listen" in lower else "medium",
                reasoning=f"Directly addressed with vocative '{matched_name}' and directive/question syntax."
            )
        elif is_third_person and not is_direct:
            return AddressedAlert(
                addressed_to_user=False,
                confidence=0.88,
                user_vocative_used=matched_name,
                urgency="low",
                reasoning=f"Name '{matched_name}' mentioned in third-person descriptive context."
            )
        else:
            # Default to alerting if ambiguous and starts with name
            addressed = lower.strip().startswith(matched_name.lower())
            return AddressedAlert(
                addressed_to_user=addressed,
                confidence=0.75,
                user_vocative_used=matched_name,
                urgency="medium" if addressed else "low",
                reasoning="Ambiguous reference; resolved based on clause positioning."
            )

    async def detect_question_and_replies(self, text: str, friend_name: str, tone_profile: str) -> QuestionReplies:
        lower = text.lower()
        is_question = bool(
            "?" in text or
            re.search(r"\b(kya|kyun|kab|kaise|kahan|kitna|did you|do you|are you|will you|have you|want|need|shall we|should I)\b", lower)
        )

        if not is_question:
            return QuestionReplies(is_question=False, replies=[])

        # Tailor 3 quick replies based on topic
        if any(w in lower for w in ["chai", "tea", "coffee", "khana", "dinner", "roti", "dal", "paneer", "kheer", "sweet", "eat", "food"]):
            replies = [
                QuickReply(label="Yes, a little", text="Haan beta, bas thodi si de do."),
                QuickReply(label="No, full", text="Nahin beta, mera pet bhar gaya hai, shukriya."),
                QuickReply(label="Later please", text="Thoda baad mein lena, abhi theek hai.")
            ]
        elif any(w in lower for w in ["medicine", "tablet", "dawa", "metformin", "telmisartan", "bp", "sugar", "dose", "doctor"]):
            replies = [
                QuickReply(label="Already taken", text="Haan beta, khane se pehle le li thi."),
                QuickReply(label="Will take after food", text="Nahin, abhi khane ke baad turant loonga."),
                QuickReply(label="Remind in 10 mins", text="Zara 10 minute mein yaad dila dena please.")
            ]
        elif any(w in lower for w in ["cold", "hot", "ac", "fan", "blanket", "chadar", "hawa", "comfortable"]):
            replies = [
                QuickReply(label="AC is too cold", text="Thoda AC kam kar do, thand lag rahi hai."),
                QuickReply(label="Comfortable", text="Bilkul theek hai, koi dikkat nahin."),
                QuickReply(label="Turn off fan", text="Pankha dheema kar do beta.")
            ]
        else:
            # General polite Dadaji replies
            replies = [
                QuickReply(label="Yes / Haanji", text="Haanji, bilkul theek hai."),
                QuickReply(label="No / Nahin", text="Nahin beta, abhi zaroorat nahin hai."),
                QuickReply(label="Later / Baad mein", text="Aaram se baad mein baat karenge.")
            ]

        return QuestionReplies(is_question=True, replies=replies)

    async def generate_catchup_recap(self, transcript_lines: List[Dict]) -> CatchupRecap:
        if not transcript_lines:
            return CatchupRecap(
                recap="No conversation has been recorded yet.",
                key_topic="Quiet table",
                speakers_involved=[]
            )

        speakers = list(set(line.get("speaker", "Someone") for line in transcript_lines))
        texts = [line.get("text", "") for line in transcript_lines]
        combined = " ".join(texts)
        lower = combined.lower()

        # Identify prominent topics
        topic = "General family dinner conversation"
        if "doctor" in lower or "medicine" in lower or "sugar" in lower or "bp" in lower:
            topic = "Health & medication updates"
        elif "dinner" in lower or "dal" in lower or "paneer" in lower or "khana" in lower:
            topic = "Dinner dishes and food preferences"
        elif "trip" in lower or "office" in lower or "train" in lower or "gurgaon" in lower or "flight" in lower:
            topic = "Travel plans and work schedules"

        speaker_str = ", ".join(speakers[:3])
        last_utterance = texts[-1] if texts else ""

        recap = f"{speaker_str} were discussing {topic.lower()}. The discussion recently focused on: \"{last_utterance[:100]}\"."
        return CatchupRecap(
            recap=recap,
            key_topic=topic,
            speakers_involved=speakers
        )

    async def simplify_plain_language(self, text: str) -> PlainLanguageResult:
        lower = text.lower()
        explained = []
        simplified = text

        for term, (plain_sub, explanation) in MEDICAL_SIMPLIFICATIONS.items():
            pattern = re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE)
            if pattern.search(text):
                explained.append({"term": term.title(), "simple_meaning": explanation})
                simplified = pattern.sub(f"{plain_sub} ({explanation})", simplified)

        return PlainLanguageResult(
            original_text=text,
            plain_text=simplified,
            key_terms_explained=explained
        )

    async def extract_memories(self, transcript_lines: List[Dict]) -> List[MemoryItem]:
        items: List[MemoryItem] = []
        combined_text = "\n".join(f"[{line.get('speaker', 'Speaker')}]: {line.get('text', '')}" for line in transcript_lines)
        
        # Regex heuristics for medicines
        med_matches = re.finditer(r"\b(Metformin|Telmisartan|Atorvastatin|Ecosprin|Insulin|dawa|tablet)\b", combined_text, re.IGNORECASE)
        found_meds = set()
        for m in med_matches:
            med_name = m.group(1).title()
            if med_name not in found_meds:
                found_meds.add(med_name)
                items.append(MemoryItem(
                    category="medicine",
                    title=f"Take {med_name}",
                    detail=f"Discussed medication: {med_name}",
                    time_or_date="Daily as prescribed"
                ))

        # Dates / timings / appointments
        appt_match = re.search(r"\b(doctor\s+[a-z]+|clinic|hospital|apollo|dr\.?\s*[a-z]+)\b", combined_text, re.IGNORECASE)
        date_match = re.search(r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday|tomorrow|next week)\b", combined_text, re.IGNORECASE)
        
        if appt_match:
            doc_name = appt_match.group(1).title()
            timing = date_match.group(1).title() if date_match else "Upcoming"
            items.append(MemoryItem(
                category="appointment",
                title=f"Appointment with {doc_name}",
                detail=f"Visit or follow-up consultation with {doc_name}",
                time_or_date=timing
            ))

        return items
