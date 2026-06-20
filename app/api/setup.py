"""First-run setup wizard API."""

from __future__ import annotations

from flask import Blueprint, request

from app.api.responses import success_response
from app.api.validation import parse_json
from app.schemas.setup import CompleteSetupRequest
from app.services import env_settings_service, setup_service

setup_bp = Blueprint("setup", __name__)


@setup_bp.get("/setup/status")
def setup_status():
    return success_response(setup_service.get_setup_status())


@setup_bp.get("/setup/ollama-recommendation")
def ollama_recommendation():
    ram_gb = request.args.get("ram_gb", default=8.0, type=float)
    return success_response(setup_service.recommend_ollama_model(total_ram_gb=ram_gb))


@setup_bp.post("/setup/complete")
def complete_setup():
    body = parse_json(request, CompleteSetupRequest)

    if body.ollama_self_host:
        provider = body.provider or "ollama"
        env_settings_service.save_llm_settings(
            provider=provider,
            ollama_base_url=body.ollama_base_url or "http://127.0.0.1:11434",
            ollama_model=body.ollama_model,
        )
    elif body.provider:
        env_settings_service.save_llm_settings(provider=body.provider)

    status = setup_service.complete_setup(ollama_self_host=body.ollama_self_host)
    return success_response(status)
