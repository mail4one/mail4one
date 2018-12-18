import os
from dataclasses import dataclass
from enum import Enum, auto
from typing import NewType, List


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


User = NewType('User', str)


class Command(Enum):
    USER = auto()
    PASS = auto()
    CAPA = auto()
    QUIT = auto()
    LIST = auto()
    UIDL = auto()
    RETR = auto()
    DELE = auto()
    STAT = auto()


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


def parse_command(line: bytes) -> Request:
    line = line.decode()
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


def files_in_path(path):
    for _, _, files in os.walk(path):
        return [(f, os.path.join(path, f)) for f in files]


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


class MailStorage:
    def __init__(self, dirpath: str):
        self.dirpath = dirpath
        self.files = files_in_path(self.dirpath)
        self.entries = [MailEntry(filename, path) for filename, path in self.files]
        self.entries = sorted(self.entries, reverse=True, key=lambda e: e.c_time)
        for i, entry in enumerate(self.entries, start=1):
            entry.nid = i

    def get_mailbox_size(self) -> (int, int):
        return len(self.entries), sum(entry.size for entry in self.entries)

    def get_mails_list(self) -> List[MailEntry]:
        return self.entries

    @staticmethod
    def get_mail(entry: MailEntry) -> bytes:
        with open(entry.path, mode='rb') as fp:
            return fp.read()
