from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AgentAction(str, Enum):
    """Supported agent actions/intents."""
    CLARIFY = "clarification"
    RECOMMEND = "recommendation"
    REFINE = "refinement"
    COMPARE = "comparison"
    REFUSE = "refusal"
    UNKNOWN = "unknown"


class Message(BaseModel):
    """Represents a chat message in the conversation history."""
    role: str = Field(..., description="Role of the sender: 'user' or 'assistant'")
    content: str = Field(..., description="The text content of the message")


class HiringConstraints(BaseModel):
    """Structured candidate hiring constraints extracted from user prompts."""
    job_role: Optional[str] = Field(None, description="The targeted job profile or role name")
    programming_language: Optional[str] = Field(None, description="Technical programming languages specified (e.g. Java, Python)")
    experience_level: Optional[str] = Field(None, description="Level of experience required (e.g. entry-level, graduate, senior)")
    assessment_type: Optional[str] = Field(None, description="Targeted category type (e.g. Cognitive Ability, Personality & Behavior)")
    personality_required: Optional[bool] = Field(None, description="Flag indicating if a personality/behavioral questionnaire is required")
    cognitive_required: Optional[bool] = Field(None, description="Flag indicating if a cognitive ability test is required")
    technical_required: Optional[bool] = Field(None, description="Flag indicating if a technical skills/coding simulator is required")
    industry: Optional[str] = Field(None, description="Target industry sector (e.g. Finance, Healthcare)")
    language: Optional[str] = Field(None, description="Languages requested (e.g. English, Spanish)")
    duration: Optional[str] = Field(None, description="Test duration constraints (e.g. 30 minutes, 1 hour)")


class ConversationState(BaseModel):
    """The analyzed conversation state indicators before choosing planning actions."""
    intent: AgentAction = Field(..., description="The categorized user intent")
    collected_information: Dict[str, Any] = Field(default_factory=dict, description="Extracted constraints state")
    missing_information: List[str] = Field(default_factory=list, description="List of required parameters that are still missing")
    retrieval_required: bool = Field(default=False, description="Flag indicating if vector search is needed")
    comparison_requested: bool = Field(default=False, description="Flag indicating if side-by-side comparison is requested")
    refusal_required: bool = Field(default=False, description="Flag indicating if the prompt is out of scope")
    is_complete: bool = Field(default=False, description="Flag indicating if we have sufficient info to make recommendations")


class AgentResponse(BaseModel):
    """The structured agent output response payload."""
    action: AgentAction = Field(..., description="The primary action chosen by the agent for this turn")
    reply: str = Field(..., description="The text reply message to display to the user")
    recommendations: List[Dict[str, Any]] = Field(default_factory=list, description="List of recommended assessments, if action is recommendation or refinement")
    end_of_conversation: bool = Field(default=False, description="Flag indicating if recommendations are finalized and dialog has concluded")
