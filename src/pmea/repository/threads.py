import uuid
import redis.asyncio as aioredis
from redis.commands.core import AsyncScript
from typing import Optional, Set

REDIS_KEY_PREFIX_THREAD = "thread:"
REDIS_KEY_PREFIX_MSG_ID = "msg:"
REDIS_KEY_PREFIX_LAST_UID = "last_uid:"

MAX_UID_LUA = """
local current = redis.call('GET', KEYS[1])
if (not current) or (tonumber(ARGV[1]) > tonumber(current)) then
  redis.call('SET', KEYS[1], ARGV[1])
  return ARGV[1]
else
  return current
end
"""

class ThreadsRepository:
    """Repository for keeping track of email message-to-thread mappings."""
    _redis_client: aioredis.Redis
    _max_uid_script: AsyncScript

    def __init__(self, redis_client: aioredis.Redis):
        self._redis_client = redis_client
        self._max_uid_script = self._redis_client.register_script(MAX_UID_LUA)

    async def set_last_uid(self, email: str, uid: int) -> None:
        """Updates last processed message UID for a given email."""
        key = f"{REDIS_KEY_PREFIX_LAST_UID}{email}"
        await self._max_uid_script(keys=[key], args=[uid])

    async def get_last_uid(self, email: str) -> Optional[int]:
        """Returns last processed message UID for a given email."""
        key = f"{REDIS_KEY_PREFIX_LAST_UID}{email}"
        value = await self._redis_client.get(key)
        return int(value) if value else None

    async def get_message_thread_id(self, message_id: str) -> Optional[str]:
        """
        Retrieves the thread ID associated with a given message ID.
        Returns None if the message ID is not found or not linked to any thread.
        """
        key = f"{REDIS_KEY_PREFIX_MSG_ID}{message_id}"
        ok = await self._redis_client.exists(key)
        if not ok:
            return None
        value = await self._redis_client.get(key)
        return value.decode('utf-8') if value else None
    
    async def lookup_thread_id(self, message_ids: list[str]) -> Optional[str]:
        """
        Checks if at-least one of the messages has a thread ID.
        Used to find a thread ID in a list of referenced messages.
        """
        if not message_ids:
            return None
        values = await self._redis_client.mget(*[f"{REDIS_KEY_PREFIX_MSG_ID}{m}" for m in message_ids])
        parent_tid = next((v.decode()                     # first non-None
                   for v in values if v), None)
        return parent_tid

    def new_thread_id(self) -> str:
        """
        Generates a new unique thread ID.
        """
        return str(uuid.uuid4())

    async def add_thread_message(self, message_id: str, thread_id: str) -> None:
        """
        Links a message ID to a thread ID in Redis.
        This involves two operations:
        1. Storing the mapping from message_id to thread_id (msg:<message_id> -> thread_id).
        2. Adding the message_id to the set of messages for the thread (thread:<thread_id> -> {message_id, ...}).
        """
        msg_key = f"{REDIS_KEY_PREFIX_MSG_ID}{message_id}"
        thread_key = f"{REDIS_KEY_PREFIX_THREAD}{thread_id}"
        async with self._redis_client.pipeline(transaction=True) as p:
            p.set(msg_key, thread_id)
            p.sadd(thread_key, message_id)
            await p.execute()

    async def get_thread_messages(self, thread_id: str) -> Set[str]:
        """
        Retrieves all message IDs belonging to a specific thread.
        Returns an empty set if the thread does not exist or has no messages.
        """
        key = f"{REDIS_KEY_PREFIX_THREAD}{thread_id}"
        result = await self._redis_client.smembers(key)
        return result or set()