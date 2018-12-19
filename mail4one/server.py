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

from .smtp import create_smtp_server
from .pop3 import create_pop_server


def create_tls_context(certfile, keyfile):
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(certfile=certfile, keyfile=keyfile)
    return context


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--certfile')
    parser.add_argument('--keyfile')
    parser.add_argument("mail_dir_path")

    args = parser.parse_args()
    args.mail_dir_path = Path(args.mail_dir_path)

    # Hardcoded args
    args.host = '0.0.0.0'
    args.smtp_port = 25
    args.pop_port = 995
    args.smtputf8 = True
    args.debug = True
    return args


def setup_logging(args):
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)


def drop_privileges():
    try:
        import pwd
    except ImportError:
        logging.error("Cannot import pwd; run as root")
        sys.exit(1)
    nobody = pwd.getpwnam('nobody')
    try:
        os.setgid(nobody.pw_gid)
        os.setuid(nobody.pw_uid)
    except PermissionError:
        logging.error("Cannot setuid nobody; run as root")
        sys.exit(1)
    logging.info("Dropped privileges")
    logging.debug("Signalled! Clients can come in")


async def a_main(args, tls_context):
    # pop_server = await create_pop_server(args.mail_dir_path, port=args.pop_port, host=args.host, context=tls_context)
    smtp_server = await create_smtp_server(args.mail_dir_path, port=args.smtp_port, host=args.host, context=tls_context)
    drop_privileges()
    # await pop_server.start_serving()
    await smtp_server.serve_forever()


def main():
    args = parse_args()
    tls_context = create_tls_context(args.certfile, args.keyfile)
    setup_logging(args)
    loop = asyncio.get_event_loop()
    loop.set_debug(args.debug)
    asyncio.run(a_main(args, tls_context))


if __name__ == '__main__':
    main()
