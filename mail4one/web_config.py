import asyncio
from asyncbasehttp import request_handler, Request, Response, RequestHandler
from typing import Optional, Tuple
import ssl
import logging
from pprint import pprint
import http
from base64 import b64decode
from .pwhash import gen_pwhash, parse_hash, PWInfo, check_pass
import pkgutil

def get_template() -> bytes:
    if data:= pkgutil.get_data('mail4one', 'template_web_config.html'):
        return data
    raise Exception("Failed to get template data from 'template_web_config.html'")


def get_dummy_pwinfo() -> PWInfo:
    pwhash = gen_pwhash("world")
    return parse_hash(pwhash)


class WebonfigHandler(RequestHandler):
    def __init__(self, username: str, pwinfo: PWInfo):
        self.username = username.encode()
        self.pwinfo = pwinfo
        self.auth_required = True

    def do_auth(self, req: Request) -> Tuple[bool, Optional[Response]]:

        def resp_unauthorized():
            resp = Response.no_body_response(http.HTTPStatus.UNAUTHORIZED)
            resp.add_header("WWW-Authenticate", 'Basic realm="Mail4one"')
            return resp

        auth_header = req.headers["Authorization"]

        if not auth_header:
            return False, resp_unauthorized()

        if not auth_header.startswith("Basic "):
            logging.error("Authorization header malformed")
            return False, Response.no_body_response(http.HTTPStatus.BAD_REQUEST)

        userpassb64 = auth_header[len("Basic ") :]
        try:
            userpass = b64decode(userpassb64)
            username, password = userpass.split(b":")
        except:
            logging.exception("bad request")
            return False, Response.no_body_response(http.HTTPStatus.BAD_REQUEST)

        if username == self.username and check_pass(password.decode(), self.pwinfo):
            return True, None

        return False, resp_unauthorized()
        

    async def process_request(self, req: Request) -> Response:
        if self.auth_required:
            ok, resp = self.do_auth(req)
            if not ok:
                if resp:
                    return resp
                else: # To silence mypy
                    raise Exception("Something went wrong!")
        return Response.create_ok_response(get_template())


async def create_web_config_server(
    host: str, port: int, ssl_context: Optional[ssl.SSLContext]
) -> asyncio.Server:
    logging.info(f"template: {get_template().decode()}")
    logging.info(f"Starting Webconfig server {host=}, {port=}, {ssl_context != None=}")
    return await asyncio.start_server(
        WebonfigHandler("hello", get_dummy_pwinfo()),
        host=host,
        port=port,
        ssl=ssl_context,
    )
