import json
import re
from typing import Callable
from jata import Jata, MutableDefault


class Match(Jata):
    name: str
    addrs: list[str] = MutableDefault(lambda: [])
    addr_rexs: list[str] = MutableDefault(lambda: [])


DEFAULT_MATCH_ALL = "default_match_all"


class Rule(Jata):
    match_name: str
    negate: bool = False
    # Do not process further rules
    stop_check: bool = False


class Mbox(Jata):
    name: str
    rules: list[Rule]


DEFAULT_NULL_MBOX = "default_null_mbox"


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
    pop_timeout_seconds = 60
    smtputf8 = True
    users: list[User]
    boxes: list[Mbox]
    matches: list[Match]


def parse_rules(cfg: Config) -> list[tuple[str, Callable[[str], bool], bool]]:

    def make_match_fn(m: Match):
        if m.addrs and m.addr_rexs:
            raise Exception("Both addrs and addr_rexs is set")
        if m.addrs:
            return lambda malias: malias in m.addrs
        elif m.addr_rexs:
            compiled_res = [re.compile(reg) for reg in m.addr_rexs]
            return lambda malias: any(
                reg.match(malias) for reg in compiled_res)
        else:
            raise Exception("Neither addrs nor addr_rexs is set")

    matches = {
        m.name: make_match_fn(m)
        for match in cfg.matches if (m := Match(match)) is not None
    }
    matches[DEFAULT_MATCH_ALL] = lambda _: True

    def flat_rules():
        for mbox in cfg.boxes:
            for rule in mbox.rules:
                rule = Rule(rule)
                fn = matches[rule.match_name]
                if rule.negate:
                    match_fn = lambda malias, fn=fn: not fn(malias)
                else:
                    match_fn = fn
                yield (mbox.name, match_fn, rule.stop_check)

    return list(flat_rules())


def get_mboxes(
        addr: str, rules: list[tuple[str, Callable[[str], bool],
                                     bool]]) -> list[str]:

    def inner():
        for mbox, match_fn, stop_check in rules:
            if match_fn(addr):
                yield mbox
                if stop_check:
                    return

    return list(inner())
