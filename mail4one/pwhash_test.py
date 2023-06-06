from .pwhash import gen_pwhash, parse_hash, check_pass, SALT_LEN
import unittest


class TestPWHash(unittest.TestCase):

    def test_expected_usage(self):
        password = "Blah Blah ABCD"
        pwhash = gen_pwhash(password)
        pwinfo = parse_hash(pwhash)
        self.assertEqual(len(pwinfo.salt), SALT_LEN)
        self.assertEqual(len(pwinfo.scrypt_hash), 64)
        self.assertTrue(check_pass(password, pwinfo),
                        "check pass with correct password")
        self.assertFalse(check_pass("foobar", pwinfo),
                         "check pass with wrong password")

    def test_hardcoded_hash(self):
        test_hash = "".join((l.strip() for l in """
        AFWMBONQ2XGHWBTKVECDBBJWYEMS4DFIXIJML4VP76JQT5VWVLALE3KV
        KFEBAGWG3DOY53DK3H2EACWOBHJFYAIHDA3OFDQN2UAXI5TLBFOW4O2G
        WXNBGQ5QFMOJ5Z27HGYNO73DS5WPX2INNE47EGI6Z5UAAQAAAAEAAAIA
        """.splitlines()))
        pwinfo = parse_hash(test_hash)
        self.assertTrue(check_pass("helloworld", pwinfo),
                        "check pass with correct password")
        self.assertFalse(check_pass("foobar", pwinfo),
                         "check pass with wrong password")

    def test_invalid_hash(self):
        with self.assertRaises(Exception):
            parse_hash("sdlfkjdsklfjdsk")


if __name__ == '__main__':
    unittest.main()
