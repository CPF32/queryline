"""User feedback on query responses."""

from typing import Literal, Self

from pydantic import BaseModel

FeedbackRating = Literal["up", "down"]


class QueryFeedback(BaseModel):
    id: str
    query_log_id: str
    user_id: str
    rating: FeedbackRating
    comment: str | None = None
    created_at: str

    def to_dict(self) -> dict:
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        return cls.model_validate(data)
