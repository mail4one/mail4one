import asyncio
import logging
import os
import ssl
from _contextvars import ContextVar
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import ClassVar, List, Set

from .poputils import InvalidCommand, parse_command, err, Command, ClientQuit, ClientError, AuthError, ok, msg, end, \
    Request, MailEntry, get_mail, get_mails_list, MailList


def add_season(content: bytes, season: bytes):
    return sha256(season + content).digest()


# noinspection PyProtectedMember
@dataclass
class Session:
    _reader: asyncio.StreamReader
    _writer: asyncio.StreamWriter

    # common state
    all_sessions: ClassVar[Set] = set()
    mails_path: ClassVar[Path] = Path("")
    current_session: ClassVar = ContextVar("session")
    password_hash: ClassVar[str] = ""
    SALT: ClassVar[bytes] = b"balki is awesome+"
    pepper: ClassVar[bytes]

    @classmethod
    def init_password(cls, salted_hash: str):
        cls.pepper = os.urandom(32)
        cls.password_hash = add_season(bytes.fromhex(salted_hash), cls.pepper)

    @classmethod
    def get(cls):
        return cls.current_session.get()

    @classmethod
    def reader(cls):
        return cls.get()._reader

    @classmethod
    def writer(cls):
        return cls.get()._writer


async def next_req():
    for _ in range(InvalidCommand.RETRIES):
        line = await Session.reader().readline()
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


async def expect_cmd(*commands: Command):
    req = await next_req()
    if req.cmd not in commands:
        logging.error(f"Unexpected command: {req.cmd} is not in {commands}")
        raise ClientError
    return req


def write(data):
    logging.debug(f"Server: {data}")
    Session.writer().write(data)


def validate_password(password):
    if Session.password_hash != add_season(add_season(password.encode(), Session.SALT), Session.pepper):
        raise AuthError("Invalid user pass")


async def handle_user_pass_auth(user_cmd):
    username = user_cmd.arg1
    if not username:
        raise AuthError("Invalid USER command. username empty")
    write(ok("Welcome"))
    cmd = await expect_cmd(Command.PASS)
    password = cmd.arg1
    validate_password(password)
    logging.info(f"User: {username} has logged in successfully")
    return username


async def auth_stage():
    write(ok("Server Ready"))
    for _ in range(AuthError.RETRIES):
        try:
            req = await expect_cmd(Command.USER, Command.CAPA)
            if req.cmd is Command.CAPA:
                write(ok("Following are supported"))
                write(msg("USER"))
                write(end())
            else:
                username = await handle_user_pass_auth(req)
                if username in Session.all_sessions:
                    logging.warning(f"User: {username} already has an active session")
                    raise AuthError("Already logged in")
                else:
                    write(ok("Login successful"))
                    return username
        except AuthError as ae:
            write(err(f"Auth Failed: {ae}"))
        except ClientQuit as c:
            write(ok("Bye"))
            logging.warning("Client has QUIT before auth succeeded")
            raise ClientError from c
    else:
        raise ClientError("Failed to authenticate")


def trans_command_capa(_, __):
    write(ok("CAPA follows"))
    write(msg("UIDL"))
    write(end())


def trans_command_stat(mails: MailList, _):
    num, size = mails.compute_stat()
    write(ok(f"{num} {size}"))


def trans_command_list(mails: MailList, req: Request):
    if req.arg1:
        entry = mails.get(req.arg1)
        if entry:
            write(ok(f"{req.arg1} {entry.size}"))
        else:
            write(err("Not found"))
    else:
        write(ok("Mails follow"))
        for entry in mails.get_all():
            write(msg(f"{entry.nid} {entry.size}"))
        write(end())


def trans_command_uidl(mails: MailList, req: Request):
    if req.arg1:
        entry = mails.get(req.arg1)
        if entry:
            write(ok(f"{req.arg1} {entry.uid}"))
        else:
            write(err("Not found"))
    else:
        write(ok("Mails follow"))
        for entry in mails.get_all():
            write(msg(f"{entry.nid} {entry.uid}"))
        write(end())


def trans_command_retr(mails: MailList, req: Request):
    entry = mails.get(req.arg1)
    if entry:
        write(ok("Contents follow"))
        write(get_mail(entry))
        write(end())
    else:
        write(err("Not found"))


def trans_command_dele(mails: MailList, req: Request):
    entry = mails.get(req.arg1)
    if entry:
        mails.delete(req.arg1)
        write(ok("Deleted"))
    else:
        write(err("Not found"))


def trans_command_noop(_, __):
    write(ok("Hmm"))


async def process_transactions(mails_list: List[MailEntry]):
    mails = MailList(mails_list)

    def reset(_, __):
        nonlocal mails
        mails = MailList(mails_list)

    handle_map = {
        Command.CAPA: trans_command_capa,
        Command.STAT: trans_command_stat,
        Command.LIST: trans_command_list,
        Command.UIDL: trans_command_uidl,
        Command.RETR: trans_command_retr,
        Command.DELE: trans_command_dele,
        Command.RSET: reset,
        Command.NOOP: trans_command_noop,
    }

    while True:
        try:
            req = await next_req()
        except ClientQuit:
            write(ok("Bye"))
            return mails.deleted_uids
        logging.debug(f"Request: {req}")
        try:
            func = handle_map[req.cmd]
        except KeyError:
            write(err("Not implemented"))
            raise ClientError("We shouldn't reach here")
        else:
            func(mails, req)
            await Session.writer().drain()


async def transaction_stage(deleted_items_path: Path):
    if deleted_items_path.exists():
        with deleted_items_path.open() as f:
            deleted_items = set(f.read().splitlines())
    else:
        deleted_items = set()

    mails_list = [entry for entry in get_mails_list(Session.mails_path / 'new') if entry.uid not in deleted_items]

    new_deleted_items: Set = await process_transactions(mails_list)
    return deleted_items.union(new_deleted_items)


def delete_messages(delete_ids, deleted_items_path: Path):
    with deleted_items_path.open(mode="w") as f:
        f.writelines(f"{did}\n" for did in delete_ids)


async def new_session(stream_reader: asyncio.StreamReader, stream_writer: asyncio.StreamWriter):
    session = Session(stream_reader, stream_writer)
    Session.current_session.set(session)
    logging.info(f"New session started with {stream_reader} and {stream_writer}")
    username = None
    try:
        username = await auth_stage()
        assert username is not None
        Session.all_sessions.add(username)
        deleted_items_path = Session.mails_path / username
        logging.info(f"User:{username} logged in successfully")

        delete_ids = await transaction_stage(deleted_items_path)
        logging.info(f"User:{username} completed transactions. Deleted:{delete_ids}")

        delete_messages(delete_ids, deleted_items_path)
        logging.info(f"User:{username} Saved deleted items")

    except ClientError as c:
        write(err("Something went wrong"))
        logging.error(f"Unexpected client error: {c}")
    except Exception as e:
        logging.error(f"Serious client error: {e}")
        raise
    finally:
        if username:
            Session.all_sessions.remove(username)
        stream_writer.close()


async def timed_cb(stream_reader: asyncio.StreamReader, stream_writer: asyncio.StreamWriter):
    try:
        return await asyncio.wait_for(new_session(stream_reader, stream_writer), 60)
    finally:
        stream_writer.close()


async def create_pop_server(dirpath: Path, port: int, password_hash: str, host="", context: ssl.SSLContext = None):
    Session.mails_path = dirpath
    Session.init_password(password_hash)
    logging.info(
        f"Starting POP3 server Maildir={dirpath}, host={host}, port={port}, context={context}")
    return await asyncio.start_server(timed_cb, host=host, port=port, ssl=context)


async def a_main(*args, **kwargs):
    server = await create_pop_server(*args, **kwargs)
    await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(a_main(Path("/tmp/mails"), 9995, password_hash=add_season(b"dummy", Session.SALT).hexdigest()))
