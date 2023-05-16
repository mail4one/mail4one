from .pwhash import *

def check_pass_from_hash(password: str, pwhash: str) -> bool:
    try:
        pwinfo = parse_hash(pwhash)
    except:
        return False
    return check_pass(password, pwinfo)

test_hash = "AFWMBONQ2XGHWBTKVECDBBJWYEMS4DFIXIJML4VP76JQT5VWVLALE3KVKFEBAGWG3DOY53DK3H2EACWOBHJFYAIHDA3OFDQN2UAXI5TLBFOW4O2GWXNBGQ5QFMOJ5Z27HGYNO73DS5WPX2INNE47EGI6Z5UAAQAAAAEAAAIA"

def main():
    print(gen_pwhash("helloworld"))
    print("------------")
    print(check_pass_from_hash("hElloworld", test_hash))
    print(check_pass_from_hash("helloworld", "foobar"))
    print("------------")
    print(check_pass_from_hash("helloworld", test_hash))


if __name__ == '__main__':
    main()
