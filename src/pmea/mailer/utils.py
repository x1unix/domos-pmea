import re
import email
from email import message

UID_RX_LINE = re.compile(r'^\d+\s+FETCH\s+\(UID\s+(\d+)\)$')
"""Parses UID from FETCH response line (e.g. 'x FETCH (UID x)')"""
def uid_from_fetch_line(line: bytes) -> int | None:
    try:
        line_str = line.decode("utf-8", errors="replace")
    except Exception:
        return None
    match = UID_RX_LINE.match(line_str)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None

def mail_from_msg_data(msg_data: list[bytes]) -> message.Message | None:
        # msg_data is list which looks like this: [b'x FETCH (UID x RFC822 {...})', <bytearray>, b')', b'Success']
        # TODO: check if there is a better way to parse emails.
        if len(msg_data) < 2:
            return None

        email_content_candidate = msg_data[1]
        raw_email: bytes | None = None

        if isinstance(email_content_candidate, bytearray):
            raw_email = bytes(email_content_candidate)
        elif isinstance(email_content_candidate, bytes):
            raw_email = email_content_candidate
        else:
            return None
        if not raw_email:  # Handles None or empty bytes
            return None

        return email.message_from_bytes(raw_email)

def parse_msg_payload(msg: message.Message) -> str | None:
    if not msg.is_multipart():
        return msg.get_payload(decode=True).decode('utf-8')

    # Multipart messages provide same contents in different formats.
    for part in msg.get_payload():
        content_type = part.get_content_type()
        if content_type == 'text/plain':
            return part.get_payload(decode=True).decode('utf-8')
    return None