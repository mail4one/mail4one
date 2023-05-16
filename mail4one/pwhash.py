import os
from hashlib import scrypt
from struct import pack, unpack
from base64 import b32encode, b32decode

# Links
# https://pkg.go.dev/golang.org/x/crypto/scrypt#Key
# https://crypto.stackexchange.com/a/35434

SCRYPT_N = 16384
SCRYPT_R = 8
SCRYPT_P = 1
VERSION = b'\x01'
SALT_LEN = 32
PACK_FMT = f"<c{SALT_LEN}s64slhh"


def gen_pwhash(password: str) -> str:
    salt = os.urandom(SALT_LEN)
    sh = scrypt(password.encode(),
                salt=salt,
                n=SCRYPT_N,
                r=SCRYPT_R,
                p=SCRYPT_P)
    pack_bytes = pack(PACK_FMT, VERSION, salt, sh, SCRYPT_N, SCRYPT_R,
                      SCRYPT_P)
    return b32encode(pack_bytes).decode()


class PWInfo:

    def __init__(self, salt, sh):
        self.salt = salt
        self.scrypt_hash = sh


def parse_hash(pwhash: str) -> PWInfo:
    decoded = b32decode(pwhash.encode())
    ver, salt, sh, n, r, p = unpack(PACK_FMT, decoded)
    if not (ver, n, r, p, len(salt)) == (VERSION, SCRYPT_N, SCRYPT_R, SCRYPT_P,
                                         SALT_LEN):
        raise Exception(
            f"Invalid hash: {ver=}, {n=}, {r=}, {p=}, f{len(salt)=} != {VERSION=}, {SCRYPT_N=}, {SCRYPT_R=}, {SCRYPT_P=}, {SALT_LEN=}"
        )
    return PWInfo(salt, sh)


def check_pass(password: str, pwinfo: PWInfo) -> bool:
    # No need for constant time compare for hashes. See https://security.stackexchange.com/a/46215
    return pwinfo.scrypt_hash == scrypt(password.encode(),
                                        salt=pwinfo.salt,
                                        n=SCRYPT_N,
                                        r=SCRYPT_R,
                                        p=SCRYPT_P)
