from typing import Any, Dict
from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    """
    Schema representing a matched assessment from the semantic search retrieval query.
    """
    id: str = Field(
        ..., 
        description="The stable slug identifier of the matching assessment"
    )
    name: str = Field(
        ..., 
        description="The official name of the matching assessment"
    )
    similarity_score: float = Field(
        ..., 
        description="Cosine similarity score between the query and the assessment document"
    )
    url: str = Field(
        ..., 
        description="Absolute URL of the matching assessment on the live SHL catalog"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Full metadata payload containing tags, job roles, skills, and formats"
    )
