import asyncio
import logging
import ssl
from _contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, List, Coroutine
from collections import deque

from .poputils import InvalidCommand, parse_command, err, Command, ClientQuit, ClientError, AuthError, ok, msg, end, \
    MailStorage, Request


@dataclass
class Session:
    reader: asyncio.StreamReader
    writer: asyncio.StreamWriter
    username: str = ""
    read_items: Path = None
    # common state
    all_sessions: ClassVar[List] = []
    mails_path: ClassVar[Path] = Path("")
    wait_for_privileges_to_drop: ClassVar[Coroutine] = None
    pending_request: Request = None

    def pop_request(self):
        request = self.pending_request
        self.pending_request = None
        return request

    async def next_req(self):
        if self.pending_request:
            return self.pop_request()

        for _ in range(InvalidCommand.RETRIES):
            line = await self.reader.readline()
            logging.debug(f"Client: {line}")
            if not line:
                continue
            try:
                request: Request = parse_command(line)
            except InvalidCommand:
                write(err("Bad command"))
            else:
                if request.cmd == Command.QUIT:
                    raise ClientQuit
                return request
        else:
            raise ClientError(f"Bad command {InvalidCommand.RETRIES} times")

    async def expect_cmd(self, *commands: Command, optional=False):
        req = await self.next_req()
        if req.cmd not in commands:
            if not optional:
                logging.error(f"{req.cmd} is not in {commands}")
                raise ClientError
            else:
                self.pending_request = req
                return
        return req


current_session: ContextVar[Session] = ContextVar("session")


def write(data):
    logging.debug(f"Server: {data}")
    session: Session = current_session.get()
    session.writer.write(data)


def validate_user_and_pass(username, password):
    if username != password:
        raise AuthError("Invalid user pass")


async def handle_user_pass_auth(user_cmd):
    session: Session = current_session.get()
    username = user_cmd.arg1
    if not username:
        raise AuthError("Invalid USER command. username empty")
    write(ok("Welcome"))
    cmd = await session.expect_cmd(Command.PASS)
    password = cmd.arg1
    validate_user_and_pass(username, password)
    write(ok("Good"))
    return username, password


async def auth_stage():
    session: Session = current_session.get()
    write(ok("Server Ready"))
    for _ in range(AuthError.RETRIES):
        try:
            req = await session.expect_cmd(Command.USER, Command.CAPA)
            if req.cmd is Command.CAPA:
                write(ok("Following are supported"))
                write(msg("USER"))
                write(end())
            else:
                username, password = await handle_user_pass_auth(req)
                logging.info(f"User: {username} has logged in successfully")
                return username
        except AuthError:
            write(err("Wrong auth"))
        except ClientQuit as c:
            write(ok("Bye"))
            logging.warning("Client has QUIT before auth succeeded")
            raise ClientError from c
    else:
        raise ClientError("Failed to authenticate")


async def transaction_stage():
    session: Session = current_session.get()
    logging.debug(f"Entering transaction stage for {session.username}")
    deleted_message_ids = []
    mailbox = MailStorage(Session.mails_path / 'new')

    with session.read_items.open() as f:
        read_items = set(f.read().splitlines())

    mails_list = mailbox.get_mails_list()
    mails_map = {str(entry.nid): entry for entry in mails_list}
    while True:
        try:
            req = await next_req()
            logging.debug(f"Request: {req}")
            if req.cmd is Command.CAPA:
                write(ok("No CAPA"))
                write(end())
            elif req.cmd is Command.STAT:
                num, size = mailbox.get_mailbox_size()
                write(ok(f"{num} {size}"))
            elif req.cmd is Command.LIST:
                if req.arg1:
                    write(ok(f"{req.arg1} {mails_map[req.arg1].size}"))
                else:
                    write(ok("Mails follow"))
                    for entry in mails_list:
                        write(msg(f"{entry.nid} {entry.size}"))
                    write(end())
            elif req.cmd is Command.UIDL:
                if req.arg1:
                    write(ok(f"{req.arg1} {mails_map[req.arg1].uid}"))
                else:
                    write(ok("Mails follow"))
                    for entry in mails_list:
                        write(msg(f"{entry.nid} {entry.uid}"))
                    write(end())
                    await session.writer.drain()
            elif req.cmd is Command.RETR:
                if req.arg1 not in mails_map:
                    write(err("Not found"))
                else:
                    write(ok("Contents follow"))
                    write(mailbox.get_mail(mails_map[req.arg1]))
                    write(end())
                    await session.writer.drain()
            else:
                write(err("Not implemented"))
        except ClientQuit:
            write(ok("Bye"))
            return deleted_message_ids


def delete_messages(delete_ids):
    logging.info(f"Client deleted these ids {delete_ids}")


async def new_session(stream_reader: asyncio.StreamReader, stream_writer: asyncio.StreamWriter):
    current_session.set(Session(stream_reader, stream_writer))
    logging.info(f"New session started with {stream_reader} and {stream_writer}")
    try:
        await auth_stage()
        delete_ids = await transaction_stage()
        delete_messages(delete_ids)
    except ClientError as c:
        write(err("Something went wrong"))
        logging.error(f"Unexpected client error", c)
    except Exception as e:
        logging.error(f"Serious client error", e)
        raise
    finally:
        stream_writer.close()


async def create_pop_server(dirpath: Path, port: int, host="", context: ssl.SSLContext = None):
    Session.mails_path = dirpath
    logging.info(
        f"Starting POP3 server Maildir={dirpath}, host={host}, port={port}, context={context}")
    return await asyncio.start_server(new_session, host=host, port=port, ssl=context)


async def a_main(*args, **kwargs):
    server = await create_pop_server(*args, **kwargs)
    await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(a_main(Path("/tmp/mails"), 9995))
