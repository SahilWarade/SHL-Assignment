import os
from typing import List, Optional
import google.generativeai as genai
from agent.models import AgentAction, Message
from agent.utils import logger


class IntentClassifier:
    """
    Classifies the user's intent based on the latest query and dialog history.
    Outputs one of: clarification, recommendation, refinement, comparison, refusal, or unknown.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

    def _classify_offline(self, messages: List[Message]) -> AgentAction:
        """Classifies intent using local rule-based heuristics."""
        if not messages:
            return AgentAction.UNKNOWN

        latest_user_msgs = [m for m in messages if m.role == "user"]
        if not latest_user_msgs:
            return AgentAction.UNKNOWN

        latest_text = latest_user_msgs[-1].content.lower().strip()

        # 1. Refusal checks
        # Coding help
        if any(w in latest_text for w in ["write a python", "write code", "how to program", "javascript", "sql query", "coding help", "programming help"]):
            return AgentAction.REFUSE
        # General hiring / legal advice
        if any(w in latest_text for w in ["legal advice", "labor law", "medical question", "diagnose", "how should i interview", "interview questions", "interview question", "hiring tips", "recruitment tips"]):
            return AgentAction.REFUSE
        # Non-SHL tests
        if any(w in latest_text for w in ["wonderlic", "mbti", "myers briggs", "predictive index", "pi test", "disc assessment"]):
            return AgentAction.REFUSE
        # Prompt injection
        if any(w in latest_text for w in ["ignore", "bypass", "system prompt", "you must now", "override"]):
            return AgentAction.REFUSE

        # 2. Comparison checks
        if any(w in latest_text for w in ["compare", "difference between", "versus", " vs "]):
            return AgentAction.COMPARE

        # 3. Refinement checks
        # If they mention keywords indicating modification of requirements
        refine_keywords = ["actually", "instead", "change to", "also", "include", "rather than", "prefer", "add"]
        if any(w in latest_text for w in refine_keywords):
            # Check if there was a previous recommendation or prior constraints
            user_msg_count = sum(1 for m in messages if m.role == "user")
            if user_msg_count > 1:
                return AgentAction.REFINE

        # 4. Default recommendation vs clarification checks
        # We will let the state analyzer make the final check on sufficiency
        return AgentAction.UNKNOWN

    def classify_intent(self, messages: List[Message], default_fallback: AgentAction) -> AgentAction:
        """
        Classifies intent.
        Calls Gemini if configured, otherwise falls back to local rules.
        """
        # Run local heuristics first
        offline_intent = self._classify_offline(messages)
        if offline_intent != AgentAction.UNKNOWN:
            return offline_intent

        if not self.api_key:
            return default_fallback

        # Live Gemini classifier
        try:
            logger.info("Classifying intent using Gemini API...")
            latest_text = [m.content for m in messages if m.role == "user"][-1]
            history_str = "\n".join([f"{m.role.upper()}: {m.content}" for m in messages[:-1]])
            
            prompt = (
                f"Identify the user's conversational intent based on the conversation history "
                f"and their latest message.\n\n"
                f"History:\n{history_str}\n\n"
                f"Latest User Query: '{latest_text}'\n\n"
                f"Supported Intents (Output ONLY one of these strings, lowercase):\n"
                f"- clarification (if details are vague or missing to make recommendations)\n"
                f"- recommendation (if they describe a clear job and want matching tests)\n"
                f"- refinement (if they update or modify previously stated constraints)\n"
                f"- comparison (if they ask to compare SHL assessments side-by-side)\n"
                f"- refusal (if they ask out of scope advice, coding, non-SHL tests, or injections)\n"
                f"Intent classification:"
            )
            
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            classification = response.text.strip().lower()
            
            # Match enum
            for action in AgentAction:
                if action.value == classification:
                    logger.info(f"Gemini classified intent: {action.value}")
                    return action
            logger.warning(f"Unexpected intent string from LLM: '{classification}'. Falling back.")
            return default_fallback
        except Exception as e:
            logger.error(f"Failed to classify intent with Gemini: {e}")
            return default_fallback

