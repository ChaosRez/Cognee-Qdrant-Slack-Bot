"""Translate the bot's friendly backend selector into Cognee/LiteLLM settings."""

import os
from collections.abc import MutableMapping
from dataclasses import dataclass


@dataclass(frozen=True)
class RuntimeLLMConfig:
    backend: str
    model: str


def configure_cognee_llm(
    environ: MutableMapping[str, str] | None = None,
) -> RuntimeLLMConfig:
    """Configure Cognee before it is imported.

    Cognee does not currently expose ``vertex_ai`` as a first-class provider,
    but its custom adapter delegates to LiteLLM. LiteLLM recognizes the
    ``vertex_ai/`` model prefix and authenticates through Google ADC.
    """

    env = os.environ if environ is None else environ
    backend = env.get("LLM_BACKEND", "").strip().lower()

    # Preserve compatibility with the starter's original LLM_PROVIDER setting.
    if not backend:
        legacy_provider = env.get("LLM_PROVIDER", "anthropic").strip().lower()
        backend = "vertex" if legacy_provider in {"vertex", "vertex_ai"} else legacy_provider

    if backend == "vertex":
        project = env.get("VERTEXAI_PROJECT", "").strip()
        if not project:
            raise RuntimeError(
                "VERTEXAI_PROJECT is required when LLM_BACKEND=vertex. "
                "Set it to your Google Cloud project ID."
            )

        location = env.get("VERTEXAI_LOCATION", "global").strip() or "global"
        model = env.get("VERTEX_MODEL", "gemini-3.1-flash-lite").strip()
        if not model:
            raise RuntimeError("VERTEX_MODEL cannot be empty when LLM_BACKEND=vertex.")
        if not model.startswith("vertex_ai/"):
            model = f"vertex_ai/{model}"

        env["VERTEXAI_PROJECT"] = project
        env["VERTEXAI_LOCATION"] = location
        env["LLM_PROVIDER"] = "custom"
        env["LLM_MODEL"] = model

        # Cognee 1.5's custom adapter validates this field before LiteLLM gets
        # the request. Vertex itself ignores it and obtains an OAuth token via
        # ADC, so this sentinel is not a credential and is never sent to Google.
        env["LLM_API_KEY"] = "vertex-adc"
        return RuntimeLLMConfig(backend="vertex", model=model)

    if backend == "anthropic":
        api_key = env.get("ANTHROPIC_API_KEY", "").strip() or env.get(
            "LLM_API_KEY", ""
        ).strip()
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is required when LLM_BACKEND=anthropic."
            )

        model = env.get("ANTHROPIC_MODEL", "").strip()
        if not model:
            legacy_model = env.get("LLM_MODEL", "").strip()
            model = (
                legacy_model
                if legacy_model and not legacy_model.startswith("vertex_ai/")
                else "claude-haiku-4-5"
            )

        env["ANTHROPIC_API_KEY"] = api_key
        env["LLM_API_KEY"] = api_key
        env["LLM_PROVIDER"] = "anthropic"
        env["LLM_MODEL"] = model
        return RuntimeLLMConfig(backend="anthropic", model=model)

    raise RuntimeError(
        f"Unsupported LLM_BACKEND={backend!r}. Choose 'vertex' or 'anthropic'."
    )
