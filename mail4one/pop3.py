import asyncio
import ssl
from _contextvars import ContextVar
from pathlib import Path
import logging

from .poputils import *

reader: ContextVar[asyncio.StreamReader] = ContextVar("reader")
writer: ContextVar[asyncio.StreamWriter] = ContextVar("writer")


def write(data):
    logging.debug(f"Server: {data}")
    writer.get().write(data)


async def next_req():
    for _ in range(InvalidCommand.RETRIES):
        line = await reader.get().readline()
        logging.debug(f"Client: {line}")
        if not line:
            continue
        try:
            request = parse_command(line)
        except InvalidCommand:
            write(err("Bad command"))
        else:
            if request.cmd == Command.QUIT:
                raise ClientQuit
            return request
    else:
        raise ClientError(f"Bad command {InvalidCommand.RETRIES} times")


async def expect_cmd(*commands: Command):
    cmd = await next_req()
    if cmd.cmd not in commands:
        logging.error(f"{cmd.cmd} is not in {commands}")
        raise ClientError
    return cmd


def validate_user_and_pass(username, password):
    if username != password:
        raise AuthError("Invalid user pass")


async def handle_user_pass_auth(user_cmd):
    username = user_cmd.arg1
    if not username:
        raise AuthError("Invalid USER command. username empty")
    write(ok("Welcome"))
    cmd = await expect_cmd(Command.PASS)
    password = cmd.arg1
    validate_user_and_pass(username, password)
    write(ok("Good"))
    return username, password


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
                username, password = await handle_user_pass_auth(req)
                logging.info(f"User: {username} has logged in successfully")
                return username
        except AuthError:
            write(err("Wrong auth"))
        except ClientQuit:
            write(ok("Bye"))
            logging.info("Client has QUIT")
            raise
    else:
        raise ClientError("Failed to authenticate")


MAILS_PATH = ""
WAIT_FOR_PRIVILEGES_TO_DROP = None


async def transaction_stage(user: User):
    logging.debug(f"Entering transaction stage for {user}")
    deleted_message_ids = []
    mailbox = MailStorage(MAILS_PATH)
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
                    await writer.get().drain()
            elif req.cmd is Command.RETR:
                if req.arg1 not in mails_map:
                    write(err("Not found"))
                else:
                    write(ok("Contents follow"))
                    write(mailbox.get_mail(mails_map[req.arg1]))
                    write(end())
                    await writer.get().drain()
            else:
                write(err("Not implemented"))
        except ClientQuit:
            write(ok("Bye"))
            return deleted_message_ids


def delete_messages(delete_ids):
    logging.info(f"Client deleted these ids {delete_ids}")


async def new_session(stream_reader: asyncio.StreamReader, stream_writer: asyncio.StreamWriter):
    if WAIT_FOR_PRIVILEGES_TO_DROP:
        await WAIT_FOR_PRIVILEGES_TO_DROP
    reader.set(stream_reader)
    writer.set(stream_writer)
    logging.info(f"New session started with {stream_reader} and {stream_writer}")
    try:
        username: User = await auth_stage()
        delete_ids = await transaction_stage(username)
        delete_messages(delete_ids)
    except ClientQuit:
        pass
    except ClientError as c:
        write(err("Something went wrong"))
        logging.error(f"Unexpected client error", c)
    except:
        logging.error(f"Serious client error")
        raise
    finally:
        stream_writer.close()


async def a_main(dirpath: Path, port: int, host="", context: ssl.SSLContext = None, waiter=None):
    global MAILS_PATH, WAIT_FOR_PRIVILEGES_TO_DROP
    MAILS_PATH = dirpath / 'new'
    WAIT_FOR_PRIVILEGES_TO_DROP = waiter
    server = await asyncio.start_server(new_session, host=host, port=port, ssl=context)
    await server.serve_forever()


if __name__ == "__main__":
    # noinspection PyTypeChecker
    asyncio.run(a_main(Path("/tmp/mails"), 9995))
