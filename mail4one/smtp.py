import asyncio
import io
import logging
import mailbox
import ssl
import uuid
import shutil
from functools import partial
from pathlib import Path
from typing import Callable
from . import config
from email.message import Message
import email.policy
from email.generator import BytesGenerator
import tempfile
import random

from aiosmtpd.handlers import Mailbox, AsyncMessage
from aiosmtpd.smtp import SMTP, DATA_SIZE_DEFAULT
from aiosmtpd.smtp import SMTP as SMTPServer
from aiosmtpd.smtp import Envelope as SMTPEnvelope
from aiosmtpd.smtp import Session as SMTPSession

logger = logging.getLogger("smtp")


class MyHandler(AsyncMessage):

    def __init__(self, mails_path: Path, mbox_finder: Callable[[str],
                                                               list[str]]):
        super().__init__()
        self.mails_path = mails_path
        self.mbox_finder = mbox_finder

    async def handle_DATA(self, server: SMTPServer, session: SMTPSession,
                          envelope: SMTPEnvelope) -> str:
        self.rcpt_tos = envelope.rcpt_tos
        self.peer = session.peer
        return await super().handle_DATA(server, session, envelope)

    async def handle_message(self, m: Message):  # type: ignore[override]
        all_mboxes: set[str] = set()
        for addr in self.rcpt_tos:
            for mbox in self.mbox_finder(addr.lower()):
                all_mboxes.add(mbox)
        if not all_mboxes:
            logger.warning(f"dropping message from: {self.peer}")
            return
        for mbox in all_mboxes:
            for sub in ("new", "tmp", "cur"):
                sub_path = self.mails_path / mbox / sub
                sub_path.mkdir(mode=0o755, exist_ok=True, parents=True)
        with tempfile.TemporaryDirectory() as tmpdir:
            filename = f"{uuid.uuid4()}.eml"
            temp_email_path = Path(tmpdir) / filename
            with open(temp_email_path, "wb") as fp:
                gen = BytesGenerator(fp, policy=email.policy.SMTP)
                gen.flatten(m)
            for mbox in all_mboxes:
                shutil.copy(temp_email_path, self.mails_path / mbox / "new")
            logger.info(
                f"Saved mail at {filename} addrs: {','.join(self.rcpt_tos)}, mboxes: {','.join(all_mboxes)} peer: {self.peer}"
            )


def protocol_factory_starttls(mails_path: Path,
                              mbox_finder: Callable[[str], list[str]],
                              context: ssl.SSLContext):
    logger.info("Got smtp client cb starttls")
    try:
        handler = MyHandler(mails_path, mbox_finder)
        smtp = SMTP(
            handler=handler,
            require_starttls=True,
            tls_context=context,
            enable_SMTPUTF8=True,
        )
    except Exception as e:
        logger.error("Something went wrong", e)
        raise
    return smtp


def protocol_factory(mails_path: Path, mbox_finder: Callable[[str],
                                                             list[str]]):
    logger.info("Got smtp client cb")
    try:
        handler = MyHandler(mails_path, mbox_finder)
        smtp = SMTP(handler=handler, enable_SMTPUTF8=True)
    except Exception as e:
        logger.error("Something went wrong", e)
        raise
    return smtp


async def create_smtp_server_starttls(
    host: str,
    port: int,
    mails_path: Path,
    mbox_finder: Callable[[str], list[str]],
    ssl_context: ssl.SSLContext,
) -> asyncio.Server:
    logging.info(
        f"Starting SMTP STARTTLS server {host=}, {port=}, {mails_path=}, {ssl_context != None=}"
    )
    loop = asyncio.get_event_loop()
    return await loop.create_server(
        partial(protocol_factory_starttls, mails_path, mbox_finder,
                ssl_context),
        host=host,
        port=port,
        start_serving=False,
    )


async def create_smtp_server(
    host: str,
    port: int,
    mails_path: Path,
    mbox_finder: Callable[[str], list[str]],
    ssl_context: ssl.SSLContext | None = None,
) -> asyncio.Server:
    logging.info(
        f"Starting SMTP server {host=}, {port=}, {mails_path=}, {ssl_context != None=}"
    )
    loop = asyncio.get_event_loop()
    return await loop.create_server(
        partial(protocol_factory, mails_path, mbox_finder),
        host=host,
        port=port,
        ssl=ssl_context,
        start_serving=False,
    )


async def a_main(*args, **kwargs):
    server = await create_smtp_server_starttls(*args, **kwargs)
    await server.serve_forever()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    asyncio.run(a_main(Path("/tmp/mails"), 9995))
