from ..mailer import Message

SYSTEM_PROMPT = """
You're Domos, an automated property management assistant which respond to tenant.
You're responsible for responding to tenant inquiries and requests.
Keep your tone formal and professional.

If you want to respond to a tenant back, just call 'reply_to_customer' tool.
Do not write response into output.
"""

ERR_MAIL_RESPONSE = """
Sorry, I'm having trouble processing your message. Please try again later.

Thread ID: {thread_id}
Error: {error}
"""

INPUT_PROMPT_FORMAT = """
Client Name: {client_name}
Client Email: {client_email}
Subject: {subject}

{body}
"""

def build_error_response(thread_id: str, e: Exception) -> str:
    return ERR_MAIL_RESPONSE.format(thread_id=thread_id, error=e)

def message_to_prompt(thread_id: str, m: Message) -> str:
    return INPUT_PROMPT_FORMAT.format(
        thread_id=thread_id,
        client_name=m.sender.name,
        client_email=m.sender.email,
        subject=m.subject,
        body=m.body,
    )