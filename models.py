"""Data models for the inputs and the generated marketing copy."""

from typing import List, Optional

from pydantic import BaseModel, Field


class CopyRequest(BaseModel):
    """Everything the user gives us about the product."""

    product_name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    platform: str
    tone: str
    audience: str = "general audience"


class MarketingCopy(BaseModel):
    """The structure we ask the model to return (JSON)."""

    headline: str = Field(description="A short hook or title")
    body: str = Field(description="The main marketing text")
    call_to_action: str = Field(description="One clear call to action")
    hashtags: List[str] = Field(default_factory=list, description="Hashtags without spaces")
    subject_line: Optional[str] = Field(default=None, description="Email subject (email only)")


class CopyResult(BaseModel):
    """Final result we show and save: the request, the settings and the copy."""

    platform: str
    tone: str
    temperature: float
    top_p: float
    copy_text: MarketingCopy
    char_count: int
    within_limit: bool
