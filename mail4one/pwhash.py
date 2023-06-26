import os
from hashlib import scrypt
from base64 import b32encode, b32decode

# Links
# https://pkg.go.dev/golang.org/x/crypto/scrypt#Key
# https://crypto.stackexchange.com/a/35434

# Doubling N causes Memory limit exceeded
SCRYPT_N = 16384
SCRYPT_R = 8
SCRYPT_P = 1

# If any of above parameters change, version will be incremented
VERSION = b"\x01"
SALT_LEN = 30
KEY_LEN = 64  # This is python default


def gen_pwhash(password: str) -> str:
    salt = os.urandom(SALT_LEN)
    sh = scrypt(
        password.encode(), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=KEY_LEN
    )
    return b32encode(VERSION + salt + sh).decode()


class PWInfo:
    def __init__(self, salt: bytes, sh: bytes):
        self.salt = salt
        self.scrypt_hash = sh


def parse_hash(pwhash_str: str) -> PWInfo:
    pwhash = b32decode(pwhash_str.encode())

    if not len(pwhash) == 1 + SALT_LEN + KEY_LEN:
        raise Exception(
            f"Invalid hash size, {len(pwhash)} !=  {1 + SALT_LEN + KEY_LEN}"
        )

    if (ver := pwhash[0:1]) != VERSION:
        raise Exception(f"Invalid hash version, {ver!r} !=  {VERSION!r}")

    salt, sh = pwhash[1 : SALT_LEN + 1], pwhash[-KEY_LEN:]
    return PWInfo(salt, sh)


def check_pass(password: str, pwinfo: PWInfo) -> bool:
    # No need for constant time compare for hashes. See https://security.stackexchange.com/a/46215
    return pwinfo.scrypt_hash == scrypt(
        password.encode(),
        salt=pwinfo.salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=KEY_LEN,
    )


if __name__ == "__main__":
    import sys

    if len(sys.argv) == 2:
        print(gen_pwhash(sys.argv[1]))
    elif len(sys.argv) == 3:
        ok = check_pass(sys.argv[1], parse_hash(sys.argv[2]))
        print("OK" if ok else "NOT OK")
    else:
        print(
            "Usage: python3 -m mail4one.pwhash <password> [password_hash]",
            file=sys.stderr,
        )
