import os
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path


class ClientError(Exception):
    pass


class ClientQuit(ClientError):
    pass


class InvalidCommand(ClientError):
    RETRIES = 3
    """WIll allow NUM_BAD_COMMANDS times"""
    pass


class AuthError(ClientError):
    RETRIES = 3
    pass


class Command(Enum):
    CAPA = auto()
    USER = auto()
    PASS = auto()
    QUIT = auto()
    STAT = auto()
    LIST = auto()
    UIDL = auto()
    RETR = auto()
    DELE = auto()
    RSET = auto()
    NOOP = auto()


@dataclass
class Request:
    cmd: Command
    arg1: str = ""
    arg2: str = ""
    rest: str = ""


def ok(arg):
    return f"+OK {arg}\r\n".encode()


def msg(arg: str):
    return f"{arg}\r\n".encode()


def end():
    return b".\r\n"


def err(arg):
    return f"-ERR {arg}\r\n".encode()


def parse_command(bline: bytes) -> Request:
    line = bline.decode()
    if not line.endswith("\r\n"):
        raise ClientError("Invalid line ending")

    parts = line.rstrip().split(maxsplit=3)
    if not parts:
        raise InvalidCommand("No command found")

    cmd_str, *parts = parts
    try:
        cmd = Command[cmd_str]
    except KeyError:
        raise InvalidCommand(cmd_str)

    request = Request(cmd)
    if parts:
        request.arg1, *parts = parts
    if parts:
        request.arg2, *parts = parts
    if parts:
        request.rest, = parts
    return request


@dataclass
class MailEntry:
    uid: str
    size: int
    c_time: float
    path: str
    nid: int = 0

    def __init__(self, filename, path):
        self.uid = filename
        stats = os.stat(path)
        self.size = stats.st_size
        self.c_time = stats.st_ctime
        self.path = path


def files_in_path(path):
    for _, _, files in os.walk(path):
        return [(f, os.path.join(path, f)) for f in files]
    return []


def get_mails_list(dirpath: Path) -> list[MailEntry]:
    files = files_in_path(dirpath)
    entries = [MailEntry(filename, path) for filename, path in files]
    return entries


def set_nid(entries: list[MailEntry]):
    entries.sort(reverse=True, key=lambda e: e.c_time)
    entries = sorted(entries, reverse=True, key=lambda e: e.c_time)
    for i, entry in enumerate(entries, start=1):
        entry.nid = i


def get_mail(entry: MailEntry) -> bytes:
    with open(entry.path, mode='rb') as fp:
        return fp.read()


class MailList:

    def __init__(self, entries: list[MailEntry]):
        self.entries = entries
        set_nid(self.entries)
        self.mails_map = {str(e.nid): e for e in entries}
        self.deleted_uids: set[str] = set()

    def delete(self, nid: str):
        self.deleted_uids.add(self.mails_map.pop(nid).uid)

    def get(self, nid: str):
        return self.mails_map.get(nid)

    def get_all(self):
        return [e for e in self.entries if str(e.nid) in self.mails_map]

    def compute_stat(self):
        entries = self.get_all()
        return len(entries), sum(entry.size for entry in entries)
