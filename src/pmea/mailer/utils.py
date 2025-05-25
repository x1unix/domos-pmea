from itertools import batched
import re
import email
from email import message
from typing import Generator

from pmea.mailer.types import MessageHeaders

UID_RX_LINE = re.compile(r'^\d+\s+FETCH\s+\(UID\s+(\d+)')
MAIL_RSP_LINES_COUNT = 3

def uid_from_fetch_line(line: bytes) -> int | None:
    """Parses UID from FETCH response line (e.g. 'x FETCH (UID x)')"""
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

def parse_msg_payload(msg: message.Message) -> str | None:
    if not msg.is_multipart():
        return msg.get_payload(decode=True).decode('utf-8')

    # Multipart messages provide same contents in different formats.
    for part in msg.get_payload():
        content_type = part.get_content_type()
        if content_type == 'text/plain':
            return part.get_payload(decode=True).decode('utf-8')
    return None

# A list contains combined contents of all messages + enclosing 'Success' line.
def iter_messages(msgs_response: list[bytes]) -> Generator[tuple[int, message.Message], None]:
    """Returns an async iterator to traverse over batch messages response"""
    if not msgs_response:
        return

    # Last element should be 'Success' line.
    # Rest is (header, payload, ending) chunk of each message.
    last_line = msgs_response[-1]
    if not last_line.startswith(b'Success'):
        raise Exception(f"unexpected response end: {last_line}")

    msgs_response = msgs_response[:-1]
    if len(msgs_response) % MAIL_RSP_LINES_COUNT != 0:
        raise Exception(f"response lines not divisible by {MAIL_RSP_LINES_COUNT}, got {len(msgs_response)}")

    for header, body, _ in batched(msgs_response, MAIL_RSP_LINES_COUNT):
        uid = uid_from_fetch_line(header)
        if not uid:
            raise Exception(f"failed to parse UID from header: {header}")
        try:
            msg = email.message_from_bytes(body)
            yield uid, msg
        except Exception as e:
            raise Exception(f"failed to message body (uid: {uid})") from e
        
def parse_message_headers(msg: message.Message) -> MessageHeaders:
    references = msg.get('References', '').split()
    return MessageHeaders(
        msg_id=msg.get('Message-ID', ''),
        in_reply_to=msg.get('In-Reply-To', ''),
        references=references if references else None,
    )