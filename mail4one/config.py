"""Module for parsing mail4one config.json"""

import re
import logging
from typing import Callable, Union, Optional
from jata import Jata, MutableDefault


class Match(Jata):
    name: str
    addrs: list[str] = MutableDefault(lambda: [])  # type: ignore
    addr_rexs: list[str] = MutableDefault(lambda: [])  # type: ignore


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


class TLSCfg(Jata):
    certfile: str
    keyfile: str


class ServerCfg(Jata):
    server_type: str
    host: str = "default"
    port: int
    # disabled: bool = False
    tls: Union[TLSCfg, str] = "default"


class PopCfg(ServerCfg):
    server_type = "pop"
    port = 995
    timeout_seconds = 60


class SmtpStartTLSCfg(ServerCfg):
    server_type = "smtp_starttls"
    require_starttls = True
    smtputf8 = True
    port = 25


class SmtpCfg(ServerCfg):
    server_type = "smtp"
    smtputf8 = True
    port = 465


class LogCfg(Jata):
    logfile = "CONSOLE"
    level = "INFO"


class Config(Jata):
    default_tls: Optional[TLSCfg] = None
    default_host: str = "0.0.0.0"
    logging: Optional[LogCfg] = None

    mails_path: str
    matches: list[Match]
    boxes: list[Mbox]
    users: list[User]

    servers: list[ServerCfg]


CheckerFn = Callable[[str], bool]
Checker = tuple[str, CheckerFn, bool]


def parse_checkers(cfg: Config) -> list[Checker]:
    def make_match_fn(m: Match):
        if m.addrs and m.addr_rexs:
            raise Exception("Both addrs and addr_rexs is set")
        if m.addrs:
            return lambda malias: malias in m.addrs
        if m.addr_rexs:
            compiled_res = [re.compile(reg) for reg in m.addr_rexs]
            return lambda malias: any(reg.match(malias) for reg in compiled_res)
        raise Exception("Neither addrs nor addr_rexs is set")

    matches = {m.name: make_match_fn(Match(m)) for m in cfg.matches or []}
    matches[DEFAULT_MATCH_ALL] = lambda _: True

    def make_checker(mbox_name: str, rule: Rule) -> Checker:
        fn = matches[rule.match_name]
        if rule.negate:
            match_fn = lambda malias: not fn(malias)
        else:
            match_fn = fn
        return mbox_name, match_fn, rule.stop_check

    return [
        make_checker(mbox.name, Rule(rule))
        for mbox in cfg.boxes or []
        for rule in mbox.rules
    ]


def get_mboxes(addr: str, checks: list[Checker]) -> list[str]:
    def inner():
        for mbox, match_fn, stop_check in checks:
            if match_fn(addr):
                if mbox != DEFAULT_NULL_MBOX:
                    yield mbox
                if stop_check:
                    return

    return list(inner())


def gen_addr_to_mboxes(cfg: Config) -> Callable[[str], list[str]]:
    checks = parse_checkers(cfg)
    logging.info(f"Parsed checkers from config, {len(checks)=}")
    return lambda addr: get_mboxes(addr, checks)
