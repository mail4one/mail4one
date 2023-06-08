import unittest
import asyncio
import logging
from .pop3 import create_pop_server
from .config import User


class TestPop3(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        logging.basicConfig(level=logging.CRITICAL)

    async def asyncSetUp(self):
        test_hash = "".join((l.strip() for l in """
        AFTY5EVN7AX47ZL7UMH3BETYWFBTAV3XHR73CEFAJBPN2NIHPWD
        ZHV2UQSMSPHSQQ2A2BFQBNC77VL7F2UKATQNJZGYLCSU6C43UQD
        AQXWXSWNGAEPGIMG2F3QDKBXL3MRHY6K2BPID64ZR6LABLPVSF
        """.splitlines()))
        users = [
            User(username="foobar", password_hash=test_hash, mbox="mails")
        ]
        pop_server = await create_pop_server(host='127.0.0.1',
                                             port=7995,
                                             mails_path='w.tmp',
                                             users=users)
        self.task = asyncio.create_task(pop_server.serve_forever())
        self.reader, self.writer = await asyncio.open_connection('127.0.0.1', 7995)

    async def test_QUIT(self):
        dialog = """
        S: +OK Server Ready
        C: QUIT
        S: +OK Bye
        """
        await self.dialog_checker(dialog)

    async def test_BAD(self):
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

    async def test_AUTH(self):
        dialog = """
        S: +OK Server Ready
        C: USER foobar
        S: +OK Welcome
        C: PASS helloworld
        S: +OK Login successful
        C: QUIT
        S: +OK Bye
        """
        await self.dialog_checker(dialog)

    async def test_dupe_AUTH(self):
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

    async def test_CAPA(self):
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

    async def asyncTearDown(self):
        self.writer.close()
        await self.writer.wait_closed()
        self.task.cancel("test done")

    async def dialog_checker(self, dialog: str):
        await self.dialog_checker_impl(self.reader, self.writer, dialog)

    async def dialog_checker_impl(self, reader: asyncio.StreamReader,
                             writer: asyncio.StreamWriter, dialog: str):
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
