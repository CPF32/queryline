"""Request body validation helpers."""

from __future__ import annotations

from typing import TypeVar

from flask import Request
from pydantic import BaseModel, ValidationError

from app.errors import ValidationAppError

T = TypeVar("T", bound=BaseModel)


def parse_json(request: Request, model: type[T]) -> T:
    payload = request.get_json(silent=True)
    if payload is None:
        raise ValidationAppError("Request body must be valid JSON.")
    try:
        return model.model_validate(payload)
    except ValidationError as exc:
        raise ValidationAppError(
            "Request validation failed.",
            details=exc.errors(),
        ) from exc
