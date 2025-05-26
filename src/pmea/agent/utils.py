def sanitize_session_id(session_id: str) -> str:
    """
    Replaces dashes with underscores in session ID.

    See https://github.com/langchain-ai/langchain-redis/issues/67 for context.
    """
    return session_id.replace("-", "_")