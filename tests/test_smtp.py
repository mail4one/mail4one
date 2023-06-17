import asyncio
import logging
import unittest
import smtplib
import tempfile
import contextlib
import os

from pathlib import Path

from mail4one.smtp import create_smtp_server

TEST_MBOX = 'foobar_mails'
MAILS_PATH: Path


def setUpModule() -> None:
    global MAILS_PATH
    logging.basicConfig(level=logging.CRITICAL)
    td = tempfile.TemporaryDirectory(prefix="m41.smtp.")
    unittest.addModuleCleanup(td.cleanup)
    MAILS_PATH = Path(td.name)
    os.mkdir(MAILS_PATH / TEST_MBOX)
    for md in ('new', 'cur', 'tmp'):
        os.mkdir(MAILS_PATH / TEST_MBOX / md)


class TestSMTP(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        smtp_server = await create_smtp_server(
            host="127.0.0.1",
            port=7996,
            mails_path=MAILS_PATH,
            mbox_finder=lambda addr: [TEST_MBOX])
        self.task = asyncio.create_task(smtp_server.serve_forever())

    async def test_send_mail(self) -> None:
        msg = b"""From: foo@sender.com
        To: "foo@bar.com"

        Hello world
        Byee
        """
        msg = b"".join(l.strip() + b"\r\n" for l in msg.splitlines())

        def send_mail():
            with contextlib.closing(smtplib.SMTP(host="127.0.0.1",
                                                 port=7996)) as client:
                client.sendmail("foo@sender.com", "foo@bar.com", msg)
                _, local_port = client.sock.getsockname()
                return local_port

        local_port = await asyncio.to_thread(send_mail)
        expected = f"""From: foo@sender.com
        To: "foo@bar.com"
        X-Peer: ('127.0.0.1', {local_port})
        X-MailFrom: foo@sender.com
        X-RcptTo: foo@bar.com

        Hello world
        Byee
        """
        expected = "".join(l.strip() + "\r\n" for l in expected.splitlines())
        mails = list((MAILS_PATH / TEST_MBOX / 'new').glob("*"))
        self.assertEqual(len(mails), 1)
        self.assertEqual(mails[0].read_bytes(), expected.encode())

    async def asyncTearDown(self) -> None:
        logging.debug("at teardown")
        self.task.cancel("test done")


if __name__ == "__main__":
    unittest.main()
