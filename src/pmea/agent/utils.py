from typing import TypedDict
from langchain_core.messages import BaseMessage

class InferenceResult(TypedDict):
    input: str | None
    history: list[BaseMessage] | None
    output: str | None

def output_from_inference_result(result: InferenceResult | None) -> str | None:
    if result is None or result.get("output") is None:
        return None
    return result["output"]

def sanitize_session_id(session_id: str) -> str:
    """
    Replaces dashes with underscores in session ID.

    See https://github.com/langchain-ai/langchain-redis/issues/67 for context.
    """
    return session_id.replace("-", "_")
