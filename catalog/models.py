import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, HttpUrl


class AssessmentModel(BaseModel):
    """
    Data model representing a normalized SHL Assessment Solution.
    Validates field constraints and enforces defaults for missing information.
    """
    id: str = Field(
        ..., 
        description="Stable slug identifier for the assessment (e.g. 'verify-g')"
    )
    name: str = Field(
        ..., 
        description="Official name of the assessment"
    )
    url: str = Field(
        ..., 
        description="Absolute URL of the assessment page"
    )
    category: Optional[str] = Field(
        default=None, 
        description="Category of test (e.g. Cognitive, Personality, Skills)"
    )
    description: str = Field(
        ..., 
        description="Full descriptive text of the assessment"
    )
    assessment_type: Optional[str] = Field(
        default=None, 
        description="Type of test format (e.g. Multiple Choice, Interactive, Simulation)"
    )
    duration: Optional[str] = Field(
        default=None, 
        description="Normalized duration (e.g. '30 minutes')"
    )
    skills: List[str] = Field(
        default_factory=list, 
        description="List of skills measured"
    )
    competencies: List[str] = Field(
        default_factory=list, 
        description="List of behavioral competencies measured"
    )
    job_roles: List[str] = Field(
        default_factory=list, 
        description="List of targeted job roles"
    )
    languages: List[str] = Field(
        default_factory=list, 
        description="Available languages for the assessment"
    )
    remote_testing: Optional[bool] = Field(
        default=None, 
        description="Whether the assessment can be taken remotely"
    )
    adaptive: Optional[bool] = Field(
        default=None, 
        description="Whether the assessment uses computer-adaptive testing (CAT)"
    )
    test_level: Optional[str] = Field(
        default=None, 
        description="Intended job levels (e.g. Entry Level, Managerial, Graduate)"
    )
    industry: List[str] = Field(
        default_factory=list, 
        description="Industries targeted by this assessment"
    )
    tags: List[str] = Field(
        default_factory=list, 
        description="Associated tags or descriptors"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Arbitrary additional key-value metadata"
    )

    @field_validator("id")
    @classmethod
    def validate_id_slug(cls, v: str) -> str:
        """Enforces slug format: lowercase alphanumeric characters and hyphens."""
        if not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", v):
            raise ValueError(
                f"ID '{v}' must be in slug format (lowercase alphanumeric and hyphens, no trailing/leading hyphens)"
            )
        return v

    @field_validator("url")
    @classmethod
    def validate_absolute_url(cls, v: str) -> str:
        """Enforces that URLs are absolute and valid HTTP/HTTPS links."""
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError(f"URL '{v}' must be absolute (start with http:// or https://)")
        return v

    @field_validator("name", "description")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        """Ensures that required string fields are not blank."""
        if not v or not v.strip():
            raise ValueError("Field cannot be empty or whitespace-only")
        return v.strip()
