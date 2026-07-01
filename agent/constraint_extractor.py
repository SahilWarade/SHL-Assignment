import json
import os
import re
from typing import Any, Dict, List, Optional
import google.generativeai as genai
from agent.models import HiringConstraints, Message
from agent.utils import logger


class ConstraintExtractor:
    """
    Extracts structured constraints (Job Role, Programming Language, Experience Level, 
    Assessment Type, Personality, Cognitive, Technical, Language, Duration) from conversation.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

        # Heuristic keywords
        self.role_keywords = ["java", "developer", "engineer", "sales", "manager", "accountant", "customer service", "agent", "analyst", "trainee", "graduate", "consultant"]
        self.level_keywords = ["entry", "senior", "graduate", "manager", "executive", "professional", "junior"]
        self.lang_keywords = ["english", "french", "german", "spanish", "japanese", "mandarin", "chinese", "italian", "dutch"]

    def _extract_offline(self, messages: List[Message]) -> HiringConstraints:
        """Heuristics to extract hiring constraints locally without LLM."""
        constraints = HiringConstraints()

        for msg in messages:
            if msg.role != "user":
                continue
            text = msg.content.lower()

            # Job Role & Programming Language
            if "java" in text:
                constraints.programming_language = "Java"
                if any(w in text for w in ["developer", "engineer", "programmer"]):
                    constraints.job_role = "Java Developer"
                else:
                    constraints.job_role = "Java Developer"  # Default
            elif "python" in text:
                constraints.programming_language = "Python"
                if any(w in text for w in ["developer", "engineer", "programmer"]):
                    constraints.job_role = "Python Developer"
                else:
                    constraints.job_role = "Python Developer"
            else:
                for kw in self.role_keywords:
                    if kw in text:
                        constraints.job_role = kw.title()
                        break

            # Experience Level (explicit keywords or year-based extraction)
            extracted_level = False
            for kw in self.level_keywords:
                if kw in text:
                    constraints.experience_level = kw.title()
                    extracted_level = True
                    break
            
            if not extracted_level:
                year_match = re.search(r"(\d+)\s*(?:year|years|yr|yrs)", text)
                if year_match:
                    years = int(year_match.group(1))
                    if years >= 5:
                        constraints.experience_level = "Senior"
                    elif years >= 2:
                        constraints.experience_level = "Professional"
                    else:
                        constraints.experience_level = "Graduate"

            # Default assessment type inferences based on job role
            if constraints.job_role:
                role_lower = constraints.job_role.lower()
                if any(w in role_lower for w in ["developer", "engineer", "programmer", "java", "python"]):
                    constraints.assessment_type = "Technical Skills"
                    constraints.technical_required = True

            # Override/Specific Test Types / Flags if explicitly mentioned
            if any(w in text for w in ["coding", "technical", "skills", "simulation", "programming"]):
                constraints.assessment_type = "Technical Skills"
                constraints.technical_required = True
            elif any(w in text for w in ["opq", "personality", "motivation", "mq", "behavioral"]):
                constraints.assessment_type = "Personality & Behavior"
                constraints.personality_required = True
            elif any(w in text for w in ["cognitive", "numerical", "verbal", "deductive", "inductive", "reasoning"]):
                constraints.assessment_type = "Cognitive Ability"
                constraints.cognitive_required = True
            elif any(w in text for w in ["sjt", "situational"]):
                constraints.assessment_type = "Personality & Behavior"
                constraints.personality_required = True
            elif any(w in text for w in ["language", "spoken", "svar"]):
                constraints.assessment_type = "Technical Skills"
                constraints.technical_required = True

            # Language
            for kw in self.lang_keywords:
                if kw in text:
                    constraints.language = kw.title()
                    break

            # Duration
            duration_match = re.search(r"\b(\d+)\s*(?:min|minute|mins|minutes|hr|hour|hours|hrs)\b", text)
            if duration_match:
                constraints.duration = duration_match.group(0)

        return constraints

    def extract_constraints(self, messages: List[Message]) -> HiringConstraints:
        """
        Extracts structured constraints from messages history.
        Uses Gemini if configured, otherwise falls back to local rules.
        """
        if not self.api_key:
            return self._extract_offline(messages)

        try:
            logger.info("Extracting constraints using Gemini JSON mode...")
            
            history_str = "\n".join([f"{m.role.upper()}: {m.content}" for m in messages])
            
            prompt = (
                f"Analyze the following conversation history and extract the structured hiring constraints. "
                f"Output your result strictly as a valid JSON object matching the schema below.\n\n"
                f"Schema fields:\n"
                f"- job_role: String or null\n"
                f"- programming_language: String or null (e.g. 'Java', 'Python')\n"
                f"- experience_level: String or null (e.g. 'Graduate', 'Senior')\n"
                f"- assessment_type: String or null (must be one of: 'Cognitive Ability', 'Personality & Behavior', 'Technical Skills')\n"
                f"- personality_required: Boolean or null\n"
                f"- cognitive_required: Boolean or null\n"
                f"- technical_required: Boolean or null\n"
                f"- industry: String or null\n"
                f"- language: String or null\n"
                f"- duration: String or null\n\n"
                f"Conversation History:\n{history_str}\n\n"
                f"JSON Output:"
            )
            
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            
            data = json.loads(response.text.strip())
            constraints = HiringConstraints(**data)
            logger.info(f"Gemini extracted constraints: {constraints.model_dump()}")
            return constraints
            
        except Exception as e:
            logger.error(f"Failed to extract constraints with Gemini: {e}")
            return self._extract_offline(messages)
