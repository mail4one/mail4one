import asyncio
import logging
import os
import ssl
import sys
from argparse import ArgumentParser
from pathlib import Path
from getpass import getpass

from .smtp import create_smtp_server_starttls, create_smtp_server
from .pop3 import create_pop_server

from . import config
from . import pwhash


def create_tls_context(certfile, keyfile) -> ssl.SSLContext:
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(certfile=certfile, keyfile=keyfile)
    return context


def setup_logging(args):
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)


async def a_main(cfg: config.Config) -> None:

    default_tls_context: ssl.SSLContext | None = None

    if tls := cfg.default_tls:
        default_tls_context = create_tls_context(tls.certfile, tls.keyfile)

    def get_tls_context(tls: config.TLSCfg | str):
        if tls == "default":
            return default_tls_context
        elif tls == "disable":
            return None
        else:
            tls_cfg = config.TLSCfg(pop.tls)
            return create_tls_context(tls_cfg.certfile, tls_cfg.keyfile)

    def get_host(host):
        if host == "default":
            return cfg.default_host
        else:
            return host

    mbox_finder = config.gen_addr_to_mboxes(cfg)
    servers: list[asyncio.Server] = []

    if cfg.pop:
        pop = config.PopCfg(cfg.pop)
        pop_server = await create_pop_server(
            host=get_host(pop.host),
            port=pop.port,
            mails_path=Path(cfg.mails_path),
            users=cfg.users,
            ssl_context=get_tls_context(pop.tls),
            timeout_seconds=pop.timeout_seconds)
        servers.append(pop_server)

    if cfg.smtp_starttls:
        stls = config.SmtpStartTLSCfg(cfg.smtp_starttls)
        stls_context = get_tls_context(stls.tls)
        if not stls_context:
            raise Exception("starttls requires ssl_context")
        smtp_server_starttls = await create_smtp_server_starttls(
            host=get_host(stls.host),
            port=stls.port,
            mails_path=Path(cfg.mails_path),
            mbox_finder=mbox_finder,
            ssl_context=stls_context)
        servers.append(smtp_server_starttls)

    if cfg.smtp:
        smtp = config.SmtpCfg(cfg.smtp)
        smtp_server = await create_smtp_server(host=get_host(smtp.host),
                                               port=smtp.port,
                                               mails_path=Path(cfg.mails_path),
                                               mbox_finder=mbox_finder,
                                               ssl_context=get_tls_context(
                                                   smtp.tls))
        servers.append(smtp_server)

    if servers:
        await asyncio.gather(*[server.serve_forever() for server in servers])
    else:
        logging.warn("Nothing to do!")


def main() -> None:
    parser = ArgumentParser(description="Personal Mail Server", epilog="See https://gitea.balki.me/balki/mail4one for more info")
    parser.add_argument(
        "-e",
        "--echo_password",
        action="store_true",
        help="Show password in command line if -g without password is used")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-c",
                       "--config",
                       metavar="CONFIG_PATH",
                       type=Path,
                       help="Run mail server with passed config")
    group.add_argument("-g",
                       "--genpwhash",
                       nargs="?",
                       dest="password",
                       const="FROM_TERMINAL",
                       metavar="PASSWORD",
                       help="Generate password hash to add in config")
    group.add_argument("-r",
                       "--pwverify",
                       dest="password_pwhash",
                       nargs=2,
                       metavar=("PASSWORD", "PWHASH"),
                       help="Check if password matches password hash")
    args = parser.parse_args()
    if password := args.password:
        if password == "FROM_TERMINAL":
            if args.echo_password:
                password = input("Enter password: ")
            else:
                password = getpass("Enter password: ")
        print(pwhash.gen_pwhash(password))
    elif args.password_pwhash:
        password, phash = args.password_pwhash
        if pwhash.check_pass(password, pwhash.parse_hash(phash)):
            print("✓ password and hash match")
        else:
            print("✗ password and hash do not match")
    else:
        cfg = config.Config(args.config.read_text())
        setup_logging(cfg)
        asyncio.run(a_main(cfg), debug=cfg.debug)


if __name__ == '__main__':
    main()
