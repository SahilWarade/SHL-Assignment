from typing import Any, Dict, List, Optional
from agent import config
from agent.constraint_extractor import ConstraintExtractor
from agent.intent_classifier import IntentClassifier
from agent.models import AgentAction, ConversationState, Message
from agent.utils import logger


class ConversationStateAnalyzer:
    """
    Orchestrates intent classification and constraint extraction to construct 
    a rich representation of the current conversation state.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.intent_classifier = IntentClassifier(api_key=api_key)
        self.constraint_extractor = ConstraintExtractor(api_key=api_key)

    def analyze_state(self, messages: List[Message]) -> ConversationState:
        """
        Extracts intents and constraints from the message sequence
        and returns a validated ConversationState model.
        """
        # 1. Extract Constraints
        constraints = self.constraint_extractor.extract_constraints(messages)
        collected_info = constraints.model_dump(exclude_none=True)

        # 2. Check completeness & identify missing info
        missing_info = []
        if not constraints.job_role:
            missing_info.append("Job Role")
        if not constraints.experience_level:
            missing_info.append("Experience Level")
        if not constraints.assessment_type:
            missing_info.append("Assessment Type")

        is_complete = len(missing_info) == 0 or (constraints.job_role is not None and constraints.assessment_type is not None)

        # Determine default intent fallback based on completeness
        user_turns = sum(1 for m in messages if m.role == "user")
        if is_complete or user_turns >= config.MAX_TURNS - 1:
            default_intent = AgentAction.RECOMMEND
        else:
            default_intent = AgentAction.CLARIFY

        # 3. Classify Intent
        intent = self.intent_classifier.classify_intent(messages, default_intent)

        # 4. Check for refinement trigger
        # If intent classified was recommendation but we detected it's a refinement
        if intent == AgentAction.RECOMMEND and len(messages) >= 3:
            # Check refinement keywords or overrides in the latest message
            latest_text = [m.content for m in messages if m.role == "user"][-1].lower()
            refine_keywords = ["actually", "instead", "change to", "also", "include", "rather than", "prefer", "add"]
            if any(w in latest_text for w in refine_keywords):
                intent = AgentAction.REFINE

        # 5. Populate state flags
        retrieval_required = intent in [AgentAction.RECOMMEND, AgentAction.REFINE]
        comparison_requested = intent == AgentAction.COMPARE
        refusal_required = intent == AgentAction.REFUSE

        state = ConversationState(
            intent=intent,
            collected_information=collected_info,
            missing_information=missing_info,
            retrieval_required=retrieval_required,
            comparison_requested=comparison_requested,
            refusal_required=refusal_required,
            is_complete=is_complete
        )

        logger.info(f"Analyzed state: {state.model_dump()}")
        return state
