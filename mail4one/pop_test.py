import unittest
import asyncio
import logging
from .pop3 import create_pop_server


class TestPop3(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        logging.basicConfig(level=logging.CRITICAL)

    async def asyncSetUp(self):
        pop_server = await create_pop_server(host='127.0.0.1',
                                             port=7995,
                                             mails_path='w.tmp',
                                             users=[])
        self.task = asyncio.create_task(pop_server.serve_forever())

    async def test_QUIT(self):
        reader, writer = await asyncio.open_connection('127.0.0.1', 7995)
        dialog = """
        S: +OK Server Ready
        C: QUIT
        S: +OK Bye
        """
        await self.dialog_checker(reader, writer, dialog)

    async def test_BAD(self):
        reader, writer = await asyncio.open_connection('127.0.0.1', 7995)
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
        await self.dialog_checker(reader, writer, dialog)
        # TODO fix
        # self.assertTrue(reader.at_eof(), "server should close the connection")

    async def test_CAPA(self):
        reader, writer = await asyncio.open_connection('127.0.0.1', 7995)
        dialog = """
        S: +OK Server Ready
        C: CAPA
        S: +OK Following are supported
        S: USER
        S: .
        C: QUIT
        S: +OK Bye
        """
        await self.dialog_checker(reader, writer, dialog)

    async def asyncTearDown(self):
        self.task.cancel("test done")

    async def dialog_checker(self, reader: asyncio.StreamReader,
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
