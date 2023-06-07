import asyncio
import io
import logging
import mailbox
import ssl
from functools import partial
from pathlib import Path

from aiosmtpd.handlers import Mailbox
from aiosmtpd.smtp import SMTP, DATA_SIZE_DEFAULT


class MaildirCRLF(mailbox.Maildir):
    _append_newline = True

    def _dump_message(self, message, target, mangle_from_=False):
        temp_buffer = io.BytesIO()
        super()._dump_message(message, temp_buffer, mangle_from_=mangle_from_)
        temp_buffer.seek(0)
        data = temp_buffer.read()
        data = data.replace(b'\n', b'\r\n')
        target.write(data)


class MailboxCRLF(Mailbox):

    def __init__(self, mail_dir: Path):
        super().__init__(mail_dir)
        for sub in ('new', 'tmp', 'cur'):
            sub_path = mail_dir / sub
            sub_path.mkdir(mode=0o755, exist_ok=True, parents=True)
        self.mailbox = MaildirCRLF(mail_dir)


def protocol_factory_starttls(dirpath: Path, context: ssl.SSLContext | None = None):
    logging.info("Got smtp client cb")
    try:
        handler = MailboxCRLF(dirpath)
        smtp = SMTP(handler=handler,
                    require_starttls=True,
                    tls_context=context,
                    data_size_limit=DATA_SIZE_DEFAULT,
                    enable_SMTPUTF8=True)
    except Exception as e:
        logging.error("Something went wrong", e)
        raise
    return smtp


def protocol_factory(dirpath: Path):
    logging.info("Got smtp client cb")
    try:
        handler = MailboxCRLF(dirpath)
        smtp = SMTP(handler=handler,
                    data_size_limit=DATA_SIZE_DEFAULT,
                    enable_SMTPUTF8=True)
    except Exception as e:
        logging.error("Something went wrong", e)
        raise
    return smtp


async def create_smtp_server_starttls(dirpath: Path,
                                      port: int,
                                      host="",
                                      context: ssl.SSLContext | None= None):
    loop = asyncio.get_event_loop()
    return await loop.create_server(partial(protocol_factory_starttls, dirpath,
                                            context),
                                    host=host,
                                    port=port,
                                    start_serving=False)


async def create_smtp_server_tls(dirpath: Path,
                                 port: int,
                                 host="",
                                 context: ssl.SSLContext | None= None):
    loop = asyncio.get_event_loop()
    return await loop.create_server(partial(protocol_factory, dirpath),
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
