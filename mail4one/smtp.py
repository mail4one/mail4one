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

from aiosmtpd.handlers import Mailbox, AsyncMessage
from aiosmtpd.smtp import SMTP, DATA_SIZE_DEFAULT
from aiosmtpd.smtp import SMTP as SMTPServer
from aiosmtpd.smtp import Envelope as SMTPEnvelope
from aiosmtpd.smtp import Session as SMTPSession


class MyHandler(AsyncMessage):

    def __init__(self, mails_path: Path, mbox_finder: Callable[[str], [str]]):
        super().__init__()
        self.mails_path = mails_path
        self.mbox_finder = mbox_finder

    async def handle_DATA(self, server: SMTPServer, session: SMTPSession,
                          envelope: SMTPEnvelope) -> str:
        self.rcpt_tos = envelope.rcpt_tos
        return await super().handle_DATA(server, session, envelope)

    async def handle_message(self, m: Message):  # type: ignore[override]
        all_mboxes: set[str] = set()
        for addr in self.rcpt_tos:
            for mbox in self.mbox_finder(addr):
                all_mboxes.add(mbox)
        if not all_mboxes:
            return
        for mbox in all_mboxes:
            for sub in ('new', 'tmp', 'cur'):
                sub_path = self.mails_path / mbox / sub
                sub_path.mkdir(mode=0o755, exist_ok=True, parents=True)
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_email_path = Path(tmpdir) / f"{uuid.uuid4()}.eml"
            with open(temp_email_path, "wb") as fp:
                gen = BytesGenerator(fp, policy=email.policy.SMTP)
                gen.flatten(m)
            for mbox in all_mboxes:
                shutil.copy2(temp_email_path, self.mails_path / mbox / 'new')


def protocol_factory_starttls(mails_path: Path,
                              mbox_finder: Callable[[str], [str]],
                              context: ssl.SSLContext | None = None):
    logging.info("Got smtp client cb starttls")
    try:
        handler = MyHandler(mails_path, mbox_finder)
        smtp = SMTP(handler=handler,
                    require_starttls=True,
                    tls_context=context,
                    enable_SMTPUTF8=True)
    except Exception as e:
        logging.error("Something went wrong", e)
        raise
    return smtp


def protocol_factory(mails_path: Path, mbox_finder: Callable[[str], [str]]):
    logging.info("Got smtp client cb")
    try:
        handler = MyHandler(mails_path, mbox_finder)
        smtp = SMTP(handler=handler, enable_SMTPUTF8=True)
    except Exception as e:
        logging.error("Something went wrong", e)
        raise
    return smtp


async def create_smtp_server_starttls(host: str,
                                      port: int,
                                      mails_path: Path,
                                      mbox_finder: Callable[[str], [str]],
                                      context: ssl.SSLContext | None = None):
    loop = asyncio.get_event_loop()
    return await loop.create_server(partial(protocol_factory_starttls,
                                            mails_path, mbox_finder, context),
                                    host=host,
                                    port=port,
                                    start_serving=False)


async def create_smtp_server_tls(host: str,
                                 port: int,
                                 mails_path: Path,
                                 mbox_finder: Callable[[str], [str]],
                                 context: ssl.SSLContext | None = None):
    loop = asyncio.get_event_loop()
    return await loop.create_server(partial(protocol_factory, mails_path, mbox_finder),
                                    host=host,
                                    port=port,
                                    ssl=context,
                                    start_serving=False)


async def a_main(*args, **kwargs):
    server = await create_smtp_server_starttls(*args, **kwargs)
    await server.serve_forever()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    asyncio.run(a_main(Path("/tmp/mails"), 9995))
