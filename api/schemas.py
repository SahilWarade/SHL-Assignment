from typing import List
from pydantic import BaseModel, Field, field_validator


class ChatMessage(BaseModel):
    """Schema validating an individual chat message in the request sequence."""
    role: str = Field(..., description="Role of the sender, must be 'user' or 'assistant'")
    content: str = Field(..., description="The message content text")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        """Validates that the role is strictly either 'user' or 'assistant'."""
        role_cleaned = v.strip().lower()
        if role_cleaned not in ["user", "assistant"]:
            raise ValueError("role must be either 'user' or 'assistant'")
        return role_cleaned

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Validates that content is a non-empty string."""
        if not v or not v.strip():
            raise ValueError("content cannot be empty or blank")
        return v.strip()


class ChatRequest(BaseModel):
    """Schema validating the POST /chat input request payload."""
    messages: List[ChatMessage] = Field(..., description="Chronological chat message history")

    @field_validator("messages")
    @classmethod
    def validate_messages(cls, v: List[ChatMessage]) -> List[ChatMessage]:
        """Validates that the list contains at least one chat message."""
        if not v:
            raise ValueError("messages list cannot be empty")
        return v


class RecommendationItem(BaseModel):
    """Schema validating recommended assessment elements returned to the client."""
    name: str = Field(..., description="Assessment Name")
    url: str = Field(..., description="Assessment URL Link")
    test_type: str = Field(..., description="Assessment Test Type / Category")


class ChatResponse(BaseModel):
    """Schema validating the POST /chat response payload."""
    reply: str = Field(..., description="The assistant's text response")
    recommendations: List[RecommendationItem] = Field(
        default_factory=list, 
        description="List of recommendations, empty unless action is completed"
    )
    end_of_conversation: bool = Field(
        ..., 
        description="Flag indicating if the conversation has concluded"
    )
