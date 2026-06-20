"""Standard JSON response helpers."""

from __future__ import annotations

from flask import jsonify


def success_response(data, status: int = 200):
    return jsonify({"data": data}), status


def list_response(data: list, *, total: int, limit: int | None = None, offset: int | None = None):
    meta: dict = {"total": total}
    if limit is not None:
        meta["limit"] = limit
    if offset is not None:
        meta["offset"] = offset
    return jsonify({"data": data, "meta": meta}), 200


def error_response(code: str, message: str, *, status: int, details: object | None = None):
    payload = {"error": {"code": code, "message": message, "details": details}}
    return jsonify(payload), status
