import json
from jata import Jata, MutableDefault


class Match(Jata):
    name: str
    alias: list[str] = MutableDefault(lambda: [])
    alias_regex: list[str] = MutableDefault(lambda: [])

class Rule(Jata):
    match_name: str
    negate: bool = False
    stop_check: bool = False

class Mbox(Jata):
    name: str
    rules: list[str]


class User(Jata):
    username: str
    password_hash: str
    mbox: str


class Config(Jata):
    certfile: str
    keyfile: str
    mails_path: str
    rules: list[Rule]
    boxes: list[Mbox]
    users: list[User]


