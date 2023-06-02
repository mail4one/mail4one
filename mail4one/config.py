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
    debug: bool = False
    mails_path: str
    host = '0.0.0.0'
    smtp_port = 25
    smtp_port_tls = 465
    smtp_port_submission = 587
    pop_port = 995
    smtputf8 = True
    rules: list[Rule]
    boxes: list[Mbox]
    users: list[User]


