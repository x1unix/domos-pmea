from ..mailer import Message

SYSTEM_PROMPT = """
You're Domos, an automated property management assistant which respond to tenant.
You're responsible for responding to tenant inquiries and requests.

Output of your response will be sent back to the tenant as a reply.
"""

ERR_MAIL_RESPONSE = """
Sorry, I'm having trouble processing your message. Please try again later.

Thread ID: {thread_id}
Error: {error}
"""

INPUT_PROMPT_FORMAT = """
Thread ID: {thread_id}
From: {from_addr}
Subject: {subject}

{body}
"""

def build_error_response(thread_id: str, e: Exception) -> str:
    return ERR_MAIL_RESPONSE.format(thread_id=thread_id, error=e)

def message_to_prompt(thread_id: str, m: Message) -> str:
    return INPUT_PROMPT_FORMAT.format(
        thread_id=thread_id,
        from_addr=m.sender.to_addr(),
        subject=m.subject,
        body=m.body,
    )