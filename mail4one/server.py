import asyncio
import logging
import os
import ssl
import sys
from argparse import ArgumentParser
from pathlib import Path

from .smtp import create_smtp_server_starttls, create_smtp_server
from .pop3 import create_pop_server

from . import config


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
    parser = ArgumentParser()
    parser.add_argument("config_path", type=Path)
    args = parser.parse_args()
    cfg = config.Config(args.config_path.read_text())

    setup_logging(cfg)
    loop = asyncio.get_event_loop()
    loop.set_debug(cfg.debug)

    asyncio.run(a_main(cfg))


if __name__ == '__main__':
    main()
