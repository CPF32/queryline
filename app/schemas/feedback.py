"""Feedback request schemas."""

from typing import Literal

from pydantic import BaseModel, Field

FeedbackRating = Literal["up", "down"]


class SubmitFeedbackRequest(BaseModel):
    rating: FeedbackRating
    comment: str | None = Field(default=None, max_length=2000)
