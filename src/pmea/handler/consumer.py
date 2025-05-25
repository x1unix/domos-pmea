import logging
from ..mailer import MailConsumer, Message

class Consumer(MailConsumer):
    _logger: logging.Logger = logging.getLogger(__name__)
    async def consume_mail(self, m: Message):
        self._logger.info(f"New email received: from={m.sender}; to={m.receiver}; dt={m.sent_at}; subj={m.subject};")
        self._logger.info(f"body: {m.body}")