import asyncio
import logging
import os
import ssl
import sys
from argparse import ArgumentParser
from pathlib import Path

from .smtp import create_smtp_server_starttls, create_smtp_server_tls
from .pop3 import create_pop_server

from .config import Config


def create_tls_context(certfile, keyfile):
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(certfile=certfile, keyfile=keyfile)
    return context


def setup_logging(args):
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)


async def a_main(config, tls_context):
    pop_server = await create_pop_server(
        host=config.host,
        port=config.pop_port,
        mails_path=config.mails_path,
        users=config.users,
        ssl_context=tls_context,
        timeout_seconds=config.pop_timeout_seconds)

    smtp_server_starttls = await create_smtp_server_starttls(
        config.mail_dir_path,
        port=config.smtp_port,
        host=config.host,
        context=tls_context)

    smtp_server_tls = await create_smtp_server_tls(config.mail_dir_path,
                                                   port=config.smtp_port_tls,
                                                   host=config.host,
                                                   context=tls_context)

    await asyncio.gather(pop_server.serve_forever(),
                         smtp_server_starttls.serve_forever(),
                         smtp_server_tls.serve_forever())


def main():
    parser = ArgumentParser()
    parser.add_argument("config_path")
    args = parser.parse_args()
    config = Config(open(args.config_path).read())

    setup_logging(args)
    loop = asyncio.get_event_loop()
    loop.set_debug(config.debug)

    tls_context = create_tls_context(config.certfile, config.keyfile)

    asyncio.run(a_main(config, tls_context))


if __name__ == '__main__':
    main()
