from ..mailer import Message

SYSTEM_PROMPT = """
You're Domos, an automated property management assistant which respond to tenant.
You're responsible for responding to tenant inquiries and requests.
Keep your tone formal and professional.

To respond to a tenant back, use a 'reply_to_customer' tool.
"""

ERR_MAIL_RESPONSE = """
Sorry, I'm having trouble processing your message. Please try again later.

Thread ID: {thread_id}
Error: {error}
"""

INPUT_PROMPT_FORMAT = """
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