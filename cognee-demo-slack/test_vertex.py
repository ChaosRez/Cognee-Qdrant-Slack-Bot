"""Make one inexpensive Vertex AI call through Cognee's configured LLM client."""

import asyncio
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel

from llm_provider import configure_cognee_llm

load_dotenv()
runtime_config = configure_cognee_llm()

if runtime_config.backend != "vertex":
    raise SystemExit("Set LLM_BACKEND=vertex in .env before running this smoke test.")


class SmokeResponse(BaseModel):
    status: Literal["vertex-ok"]


async def main() -> None:
    from cognee.infrastructure.llm.structured_output_framework.litellm_instructor.llm.get_llm_client import (
        get_llm_client,
    )

    client = get_llm_client()
    response = await client.acreate_structured_output(
        "Confirm that the model is reachable.",
        "Return the requested status value.",
        SmokeResponse,
    )
    if response.status != "vertex-ok":
        raise RuntimeError(f"Unexpected Vertex response: {response!r}")
    print(f"Vertex AI is ready via {runtime_config.model}: vertex-ok")


if __name__ == "__main__":
    asyncio.run(main())
