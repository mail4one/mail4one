from .pwhash import gen_pwhash, parse_hash, check_pass, SALT_LEN, KEY_LEN
import unittest


class TestPWHash(unittest.TestCase):

    def test_expected_usage(self):
        password = "Blah Blah ABCD"
        pwhash = gen_pwhash(password)
        pwinfo = parse_hash(pwhash)
        self.assertEqual(len(pwinfo.salt), SALT_LEN)
        self.assertEqual(len(pwinfo.scrypt_hash), KEY_LEN)
        self.assertTrue(check_pass(password, pwinfo),
                        "check pass with correct password")
        self.assertFalse(check_pass("foobar", pwinfo),
                         "check pass with wrong password")

    def test_hardcoded_hash(self):
        test_hash = "".join((l.strip() for l in """
        AFTY5EVN7AX47ZL7UMH3BETYWFBTAV3XHR73CEFAJBPN2NIHPWD
        ZHV2UQSMSPHSQQ2A2BFQBNC77VL7F2UKATQNJZGYLCSU6C43UQD
        AQXWXSWNGAEPGIMG2F3QDKBXL3MRHY6K2BPID64ZR6LABLPVSF
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
