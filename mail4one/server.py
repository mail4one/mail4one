import asyncio
# Though we don't use requests, without the below import, we crash https://stackoverflow.com/a/13057751
# When running on privilege port after dropping privileges.
# noinspection PyUnresolvedReferences
import encodings.idna
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


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--certfile')
    parser.add_argument('--keyfile')
    parser.add_argument('--password_hash')
    parser.add_argument("mail_dir_path")

    args = parser.parse_args()
    args.mail_dir_path = Path(args.mail_dir_path)

    # Hardcoded args
    args.host = '0.0.0.0'
    args.smtp_port = 25
    args.smtp_port_tls = 465
    args.smtp_port_submission = 587
    args.pop_port = 995
    args.smtputf8 = True
    args.debug = True
    return args


def setup_logging(args):
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)


async def a_main(config, tls_context):
    pop_server = await create_pop_server(config.mails_path,
                                         port=config.pop_port,
                                         host=config.host,
                                         context=tls_context,
                                         users=config.users)

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
    config_path = sys.argv[1]
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
