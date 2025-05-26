import redis.asyncio as aioredis
import uuid
from typing import Optional, Set
from ..config import RedisConfig

REDIS_THREAD_KEY_PREFIX = "thread:"
REDIS_MSG_ID_KEY_PREFIX = "msg:"

class ThreadsRepository:
    """Repository for keeping track of email message-to-thread mappings."""
    _redis_client: aioredis.Redis
    def __init__(self, redis_client: aioredis.Redis):
        self._redis_client = redis_client
        # self._redis_client = aioredis.Redis.from_url(cfg.dsn, decode_responses=True)

    async def get_message_thread_id(self, message_id: str) -> Optional[str]:
        """
        Retrieves the thread ID associated with a given message ID.
        Returns None if the message ID is not found or not linked to any thread.
        """
        key = f"{REDIS_MSG_ID_KEY_PREFIX}{message_id}"
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
        values = await self._redis_client.mget(*[f"{REDIS_MSG_ID_KEY_PREFIX}{m}" for m in message_ids])
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
        msg_key = f"{REDIS_MSG_ID_KEY_PREFIX}{message_id}"
        thread_key = f"{REDIS_THREAD_KEY_PREFIX}{thread_id}"
        async with self._redis_client.pipeline(transaction=True) as p:
            p.set(msg_key, thread_id)
            p.sadd(thread_key, message_id)
            await p.execute()

    async def get_thread_messages(self, thread_id: str) -> Set[str]:
        """
        Retrieves all message IDs belonging to a specific thread.
        Returns an empty set if the thread does not exist or has no messages.
        """
        key = f"{REDIS_THREAD_KEY_PREFIX}{thread_id}"
        result = await self._redis_client.smembers(key)
        return result or set()