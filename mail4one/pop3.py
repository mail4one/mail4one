import asyncio
import contextlib
import contextvars
import logging
import os
import ssl
import uuid
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from .config import User
from .pwhash import parse_hash, check_pass, PWInfo
from asyncio import StreamReader, StreamWriter
import random

from typing import Optional

from .poputils import (
    InvalidCommand,
    parse_command,
    err,
    Command,
    ClientQuit,
    ClientDisconnected,
    ClientError,
    AuthError,
    ok,
    msg,
    end,
    Request,
    MailEntry,
    get_mail,
    get_mails_list,
    MailList,
)


@dataclass
class State:
    reader: StreamReader
    writer: StreamWriter
    ip: str
    req_id: int
    username: str = ""
    mbox: str = ""


class SharedState:
    def __init__(self, mails_path: Path, users: dict[str, tuple[PWInfo, str]]):
        self.mails_path = mails_path
        self.users = users
        self.loggedin_users: set[str] = set()
        self.counter = random.randint(10000, 99999) * 100000

    def next_id(self) -> int:
        self.counter = self.counter + 1
        return self.counter


c_shared_state: contextvars.ContextVar = contextvars.ContextVar("pop_shared_state")


def scfg() -> SharedState:
    return c_shared_state.get()


c_state: contextvars.ContextVar = contextvars.ContextVar("state")


def state() -> State:
    return c_state.get()


class PopLogger(logging.LoggerAdapter):
    def __init__(self):
        super().__init__(logging.getLogger("pop3"), None)

    def process(self, msg, kwargs):
        state: State = c_state.get(None)
        if not state:
            return super().process(msg, kwargs)
        user = "NA"
        if state.username:
            user = state.username
        return super().process(f"{state.ip} {state.req_id} {user} {msg}", kwargs)


logger = PopLogger()


async def next_req() -> Request:
    for _ in range(InvalidCommand.RETRIES):
        line = await state().reader.readline()
        logger.debug(f"Client: {line!r}")
        if not line:
            if state().reader.at_eof():
                raise ClientDisconnected
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


async def expect_cmd(*commands: Command) -> Request:
    req = await next_req()
    if req.cmd not in commands:
        logger.error(f"Unexpected command: {req.cmd} is not in {commands}")
        raise ClientError
    return req


def write(data) -> None:
    logger.debug(f"Server: {data}")
    state().writer.write(data)


def validate_password(username, password) -> None:
    try:
        pwinfo, mbox = scfg().users[username]
    except:
        raise AuthError("Invalid user pass")

    if not check_pass(password, pwinfo):
        raise AuthError("Invalid user pass")
    state().username = username
    state().mbox = mbox


async def handle_user_pass_auth(user_cmd) -> None:
    username = user_cmd.arg1
    if not username:
        raise AuthError("Invalid USER command. username empty")
    write(ok("Welcome"))
    cmd = await expect_cmd(Command.PASS)
    password = cmd.arg1
    validate_password(username, password)
    logger.info(f"{username=} has logged in successfully")


async def auth_stage() -> None:
    write(ok("Server Ready"))
    for _ in range(AuthError.RETRIES):
        try:
            req = await expect_cmd(Command.USER, Command.CAPA)
            if req.cmd is Command.CAPA:
                write(ok("Following are supported"))
                write(msg("USER"))
                write(end())
            else:
                await handle_user_pass_auth(req)
                if state().username in scfg().loggedin_users:
                    logger.warning(
                        f"User: {state().username} already has an active session"
                    )
                    raise AuthError("Already logged in")
                else:
                    scfg().loggedin_users.add(state().username)
                    write(ok("Login successful"))
                    return
        except AuthError as ae:
            write(err(f"Auth Failed: {ae}"))
        except ClientQuit as c:
            write(ok("Bye"))
            logger.warning("Client has QUIT before auth succeeded")
            raise
    else:
        raise ClientError("Failed to authenticate")


def trans_command_capa(_, __) -> None:
    write(ok("CAPA follows"))
    write(msg("UIDL"))
    write(end())


def trans_command_stat(mails: MailList, _) -> None:
    num, size = mails.compute_stat()
    write(ok(f"{num} {size}"))


def trans_command_list(mails: MailList, req: Request) -> None:
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


def trans_command_uidl(mails: MailList, req: Request) -> None:
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


def trans_command_retr(mails: MailList, req: Request) -> None:
    entry = mails.get(req.arg1)
    if entry:
        write(ok("Contents follow"))
        write(get_mail(entry))
        write(end())
        mails.delete(req.arg1)
    else:
        write(err("Not found"))


def trans_command_dele(mails: MailList, req: Request) -> None:
    entry = mails.get(req.arg1)
    if entry:
        mails.delete(req.arg1)
        write(ok("Deleted"))
    else:
        write(err("Not found"))


def trans_command_noop(_, __) -> None:
    write(ok("Hmm"))


async def process_transactions(mails_list: list[MailEntry]) -> set[str]:
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
        logger.debug(f"Request: {req}")
        try:
            func = handle_map[req.cmd]
        except KeyError:
            write(err("Not implemented"))
            raise ClientError("We shouldn't reach here")
        else:
            func(mails, req)
            await state().writer.drain()


def get_deleted_items(deleted_items_path: Path) -> set[str]:
    if deleted_items_path.exists():
        with deleted_items_path.open() as f:
            return set(f.read().splitlines())
    return set()


def save_deleted_items(deleted_items_path: Path, deleted_items: set[str]) -> None:
    with deleted_items_path.open(mode="w") as f:
        f.writelines(f"{did}\n" for did in deleted_items)


async def transaction_stage() -> None:
    deleted_items_path = scfg().mails_path / state().mbox / state().username
    existing_deleted_items: set[str] = get_deleted_items(deleted_items_path)
    mails_list = [
        entry
        for entry in get_mails_list(scfg().mails_path / state().mbox / "new")
        if entry.uid not in existing_deleted_items
    ]

    new_deleted_items: set[str] = await process_transactions(mails_list)
    logger.info(f"completed transactions. Deleted:{len(new_deleted_items)}")
    if new_deleted_items:
        save_deleted_items(
            deleted_items_path, existing_deleted_items.union(new_deleted_items)
        )

    logger.info(f"Saved deleted items")


async def start_session() -> None:
    logger.info("New session started")
    try:
        await auth_stage()
        assert state().username
        assert state().mbox
        await transaction_stage()
        logger.info(f"User:{state().username} done")
    except ClientDisconnected as c:
        logger.info("Client disconnected")
        pass
    except ClientQuit:
        logger.info("Client QUIT")
        pass
    except ClientError as c:
        write(err("Something went wrong"))
        logger.error(f"Unexpected client error: {c}")
    except:
        logger.exception("Serious client error")
        raise
    finally:
        with contextlib.suppress(KeyError):
            scfg().loggedin_users.remove(state().username)


def parse_users(users: list[User]) -> dict[str, tuple[PWInfo, str]]:
    def inner():
        for user in users:
            user = User(user)
            pwinfo = parse_hash(user.password_hash)
            yield user.username, (pwinfo, user.mbox)

    return dict(inner())


def make_pop_server_callback(mails_path: Path, users: list[User], timeout_seconds: int):
    scfg = SharedState(mails_path=mails_path, users=parse_users(users))

    async def session_cb(reader: StreamReader, writer: StreamWriter):
        c_shared_state.set(scfg)
        ip, _ = writer.get_extra_info("peername")
        c_state.set(State(reader=reader, writer=writer, ip=ip, req_id=scfg.next_id()))
        logger.info(f"Got pop server callback")
        try:
            try:
                return await asyncio.wait_for(start_session(), timeout_seconds)
            finally:
                writer.close()
                await writer.wait_closed()
        except:
            logger.exception("unexpected exception")

    return session_cb


async def create_pop_server(
    host: str,
    port: int,
    mails_path: Path,
    users: list[User],
    ssl_context: Optional[ssl.SSLContext] = None,
    timeout_seconds: int = 60,
) -> asyncio.Server:
    logging.info(
        f"Starting POP3 server {host=}, {port=}, {mails_path=!s}, {len(users)=}, {ssl_context != None=}, {timeout_seconds=}"
    )
    return await asyncio.start_server(
        make_pop_server_callback(mails_path, users, timeout_seconds),
        host=host,
        port=port,
        ssl=ssl_context,
    )


async def a_main(*args, **kwargs) -> None:
    server = await create_pop_server(*args, **kwargs)
    await server.serve_forever()


def debug_main():
    logging.basicConfig(level=logging.DEBUG)

    import sys

    _, mails_path, port, password = sys.argv

    mails_path = Path(mails_path)
    port = int(port)

    asyncio.run(a_main(mails_path, port, password_hash=password_hash))


if __name__ == "__main__":
    debug_main()
