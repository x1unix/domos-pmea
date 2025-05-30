from itertools import batched
import re
import email
from email import message
from typing import Generator, Optional

from pmea.mailer.types import MessageHeaders

RE_UID_RX_LINE = re.compile(r'^\d+\s+FETCH\s+\(UID\s+(\d+)')
RE_UIDNEXT_RX_LINE = re.compile(r"^OK \[UIDNEXT (\d+)\]")
RE_SERVER_PUSH_EXISTS_LINE = re.compile(r"^[\d]+ EXISTS$")
RE_FETCH_FLAGS_LINE = re.compile(r"^[\d]+ FETCH \(UID [\d]+ FLAGS")

MAIL_RSP_LINES_COUNT = 3

def uid_from_fetch_line(line: bytes) -> int | None:
    """Parses UID from FETCH response line (e.g. 'x FETCH (UID x)')"""
    try:
        line_str = line.decode("utf-8", errors="replace")
    except Exception:
        return None
    match = RE_UID_RX_LINE.match(line_str)
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

def cut_fetch_flags_suffix(lines: list[bytes]) -> list[bytes]:
    skip_count = 0
    for line in reversed(lines):
        if isinstance(line, bytearray):
            break
        line_str = line.decode("utf-8", errors="replace")
        if RE_FETCH_FLAGS_LINE.match(line_str):
            skip_count += 1
            continue
        break
    return lines if not skip_count else lines[:-skip_count]

# A list contains combined contents of all messages + enclosing 'Success' line.
def iter_messages(msgs_response: list[bytes]) -> Generator[tuple[int, message.Message], None]:
    """Returns an async iterator to traverse over batch messages response"""
    if not msgs_response:
        return

    # Last element should be 'Success' line.
    # Rest: there are 2 potential cases:
    # 1. If done outside of IDLE loop: 
    #    header: 'x FETCH (UID y RFC8222 {size})'
    #    payload: <bytearray>
    #    ending:')'
    # 2. After IDLE loop:
    #    header: 'x FETCH (UID y RFC8222 {size})'
    #    payload: <bytearray>
    #    ending: ' FLAGS (\Seen)'
    #    ...
    #    flags for each message before 'Success' line:
    #    'x FETCH (UID y FLAGS (\Seen))'  - for each message at bottom
    last_line = msgs_response[-1]
    if not last_line.startswith(b'Success'):
        raise Exception(f"unexpected response end: {last_line}")

    # Trim 'Success' line.
    msgs_response = msgs_response[:-1]

    # Check for second case - trim 'x FETCH' suffixes.
    # Flags there allow checking if message is seen but atm they're not needed.
    msgs_response = cut_fetch_flags_suffix(msgs_response)

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

def uidnext_from_select_response(lines: list[bytes]) -> Optional[int]:
    """Parses UIDNEXT from SELECT response line (e.g. 'x FETCH (UID x)')"""
    if not lines:
        return None
    for line in lines:
        if not line.startswith(b'OK'):
            continue
        match = RE_UIDNEXT_RX_LINE.match(line.decode("utf-8", errors="replace"))
        if match:
            return int(match.group(1))
    return None

def is_server_push_exists_result(lines: list[bytes]) -> bool:
    if not lines:
        return False
    return RE_SERVER_PUSH_EXISTS_LINE.match(lines[0].decode("utf-8", errors="replace")) is not None

def assert_ok(code: str, msg: str) -> None:
    if code != "OK":
        raise Exception(f"{msg}: {code}")