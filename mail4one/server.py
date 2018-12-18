import asyncio
# Though we don't use requests, without the below import, we crash https://stackoverflow.com/a/13057751
# When running on privilege port after dropping privileges.
# noinspection PyUnresolvedReferences
import encodings.idna
import io
import logging
import mailbox
import os
import ssl
import sys
from argparse import ArgumentParser
from functools import partial
from pathlib import Path

from aiosmtpd.controller import Controller
from aiosmtpd.handlers import Mailbox
from aiosmtpd.main import DATA_SIZE_DEFAULT
from aiosmtpd.smtp import SMTP

from .pop3 import a_main as pop3_main


def create_tls_context(certfile, keyfile):
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(certfile=certfile, keyfile=keyfile)
    return context


class STARTTLSController(Controller):
    def __init__(self, *args, tls_context, smtp_args=None, **kwargs):
        self.tls_context = tls_context
        self.smtp_args = smtp_args or {}
        self.has_privileges_dropped: asyncio.Future = None
        if 'ssl_context' in kwargs:
            raise Exception("ssl_context not allowed when using STARTTLS, set tls_context instead")
        Controller.__init__(self, *args, **kwargs)

    async def create_future(self):
        self.has_privileges_dropped = asyncio.get_event_loop().create_future()

    async def wait_for_privileges_to_drop(self):
        await self.has_privileges_dropped

    def factory(self):
        if not self.has_privileges_dropped.done():
            # Ideally  we should await here. But this is callback and not a coroutine
            raise Exception("Client connected too fast before we could drop root privileges")
        return SMTP(self.handler, require_starttls=True, tls_context=self.tls_context, **self.smtp_args)


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


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--certfile')
    parser.add_argument('--keyfile')
    parser.add_argument("mail_dir_path")

    args = parser.parse_args()
    args.mail_dir_path = Path(args.mail_dir_path)

    # Hardcoded args
    args.host = '0.0.0.0'
    args.smtp_port = 25
    args.pop_port = 995
    args.size = DATA_SIZE_DEFAULT
    args.classpath = MailboxCRLF
    args.smtputf8 = True
    args.debug = True
    return args


def setup_logging(args):
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)


def drop_privileges(future_cb):
    try:
        import pwd
    except ImportError:
        logging.error("Cannot import pwd; run as root")
        sys.exit(1)
    nobody = pwd.getpwnam('nobody')
    try:
        os.setgid(nobody.pw_gid)
        os.setuid(nobody.pw_uid)
    except PermissionError:
        logging.error("Cannot setuid nobody; run as root")
        sys.exit(1)
    logging.info("Dropped privileges")
    future_cb().set_result("Go!")
    logging.debug("Signalled! Clients can come in")


def main():
    args = parse_args()
    tls_context = create_tls_context(args.certfile, args.keyfile)
    smtp_args = dict(data_size_limit=args.size, enable_SMTPUTF8=args.smtputf8)
    setup_logging(args)
    handler = args.classpath(args.mail_dir_path)
    loop = asyncio.get_event_loop()
    loop.set_debug(args.debug)
    controller = STARTTLSController(
        handler, tls_context=tls_context, smtp_args=smtp_args, hostname=args.host, port=args.smtp_port, loop=loop)

    loop.create_task(controller.create_future())
    loop.create_task(pop3_main(args.mail_dir_path, args.pop_port,
                               host=args.host, context=tls_context, waiter=controller.wait_for_privileges_to_drop))

    controller.start()
    loop.call_soon_threadsafe(partial(drop_privileges, lambda: controller.has_privileges_dropped))
    logging.info("Server started. Press [ENTER] to stop")
    input()
    controller.stop()
    # loop.create_task(a_main(controller))
    # loop.run_forever()


if __name__ == '__main__':
    main()
