import unittest
import asyncio
import logging
import tempfile
import time
import os
from .pop3 import create_pop_server
from .config import User
from pathlib import Path

TEST_HASH = "".join(c for c in """
AFTY5EVN7AX47ZL7UMH3BETYWFBTAV3XHR73CEFAJBPN2NIHPWD
ZHV2UQSMSPHSQQ2A2BFQBNC77VL7F2UKATQNJZGYLCSU6C43UQD
AQXWXSWNGAEPGIMG2F3QDKBXL3MRHY6K2BPID64ZR6LABLPVSF
""" if not c.isspace())

TEST_USER = 'foobar'
TEST_MBOX = 'foobar_mails'

USERS = [User(username=TEST_USER, password_hash=TEST_HASH, mbox=TEST_MBOX)]

MAILS_PATH: Path

TESTMAIL = b"""Message-ID: <N01BwLnh8dGBoD9gVz@msn.com>\r
From: from@msn.com\r
To: MddK0ftkv@outlook.com\r
Subject: hello lorem ipsum foo bar\r
Date: Mon, 24 Oct 2002 00:42:02 +0000\r
MIME-Version: 1.0\r
Content-Type: text/plain;\r
	charset="windows-1251";\r
Content-Transfer-Encoding: 7bit\r
X-Peer: ('2.2.1.9', 64593)\r
X-MailFrom: from@msn.com\r
X-RcptTo: MddK0ftkv@outlook.com\r
\r
Hello bro\r
IlzVOJqu9Zp7twFAtzcV\r
yQVk36B0mGU2gtWxXLr\r
PeF0RtbI0mAuVPLQDHCi\r
\r\n"""


def setUpModule() -> None:
    global MAILS_PATH
    logging.basicConfig(level=logging.CRITICAL)
    td = tempfile.TemporaryDirectory(prefix="m41.pop.")
    unittest.addModuleCleanup(td.cleanup)
    MAILS_PATH = Path(td.name)
    os.mkdir(MAILS_PATH / TEST_MBOX)
    for md in ('new', 'cur', 'tmp'):
        os.mkdir(MAILS_PATH / TEST_MBOX / md)
    with open(MAILS_PATH / TEST_MBOX/ 'new/msg1.eml', 'wb') as f:
        f.write(TESTMAIL)
    with open(MAILS_PATH / TEST_MBOX/ 'new/msg2.eml', 'wb') as f:
        f.write(TESTMAIL)
    print(MAILS_PATH)


def tearDownModule():
    pass


class TestPop3(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        logging.debug("at asyncSetUp")
        pop_server = await create_pop_server(host='127.0.0.1',
                                             port=7995,
                                             mails_path=MAILS_PATH,
                                             users=USERS)
        self.task = asyncio.create_task(pop_server.serve_forever())
        self.reader, self.writer = await asyncio.open_connection(
            '127.0.0.1', 7995)

    async def test_QUIT(self) -> None:
        dialog = """
        S: +OK Server Ready
        C: QUIT
        S: +OK Bye
        """
        await self.dialog_checker(dialog)

    async def test_BAD(self) -> None:
        dialog = """
        S: +OK Server Ready
        C: HELO
        S: -ERR Bad command
        C: HEYA
        S: -ERR Bad command
        C: LIST
        S: -ERR Something went wrong
        C: HELO
        """
        await self.dialog_checker(dialog)
        # TODO fix
        # self.assertTrue(reader.at_eof(), "server should close the connection")

    async def do_login(self) -> None:
        dialog = """
        S: +OK Server Ready
        C: USER foobar
        S: +OK Welcome
        C: PASS helloworld
        S: +OK Login successful
        """
        await self.dialog_checker(dialog)

    async def test_AUTH(self) -> None:
        await self.do_login()
        dialog = """
        C: QUIT
        S: +OK Bye
        """
        await self.dialog_checker(dialog)

    async def test_dupe_AUTH(self) -> None:
        r1, w1 = await asyncio.open_connection('127.0.0.1', 7995)
        r2, w2 = await asyncio.open_connection('127.0.0.1', 7995)
        dialog = """
        S: +OK Server Ready
        C: USER foobar
        S: +OK Welcome
        C: PASS helloworld
        """
        await self.dialog_checker_impl(r1, w1, dialog)
        await self.dialog_checker_impl(r2, w2, dialog)
        d1 = """S: +OK Login successful"""
        d2 = """S: -ERR Auth Failed: Already logged in"""
        await self.dialog_checker_impl(r1, w1, d1)
        await self.dialog_checker_impl(r2, w2, d2)
        end_dialog = """
        C: QUIT
        S: +OK Bye
        """
        await self.dialog_checker_impl(r1, w1, end_dialog)
        await self.dialog_checker_impl(r2, w2, end_dialog)

    async def test_STAT(self) -> None:
        await self.do_login()
        dialog = """
        C: STAT
        S: +OK 2 872
        """
        await self.dialog_checker(dialog)

    async def test_CAPA(self) -> None:
        dialog = """
        S: +OK Server Ready
        C: CAPA
        S: +OK Following are supported
        S: USER
        S: .
        C: QUIT
        S: +OK Bye
        """
        await self.dialog_checker(dialog)

    async def asyncTearDown(self) -> None:
        logging.debug("at teardown")
        self.writer.close()
        await self.writer.wait_closed()
        self.task.cancel("test done")

    async def dialog_checker(self, dialog: str) -> None:
        await self.dialog_checker_impl(self.reader, self.writer, dialog)

    async def dialog_checker_impl(self, reader: asyncio.StreamReader,
                                  writer: asyncio.StreamWriter,
                                  dialog: str) -> None:
        for line in dialog.splitlines():
            line = line.strip()
            if not line:
                continue
            side, data_str = line.split(maxsplit=1)
            data = f"{data_str}\r\n".encode()
            if side == "C:":
                writer.write(data)
            else:
                resp = await reader.readline()
                self.assertEqual(data, resp)


if __name__ == '__main__':
    unittest.main()
