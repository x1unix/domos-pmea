from textwrap import dedent
from ..mailer import Message

def build_error_response(thread_id: str, e: Exception) -> str:
    msg = f"""
    Sorry, I'm having trouble processing your message. Please try again later.

    Thread ID: {thread_id}
    Error: {e}
    """

    return dedent(msg)


def message_to_prompt(m: Message) -> str:
    prompt = f"""
    Subject: {m.subject}

    {m.body}
    """

    return dedent(prompt)