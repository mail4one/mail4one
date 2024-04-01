import unittest

from mail4one import config

TEST_CONFIG = """
{
  "mails_path": "/var/tmp/mails",
  "matches": [
    {
      "name": "mydomain",
      "addr_rexs": [
        ".*@mydomain.com",
        ".*@m.mydomain.com"
      ]
    },
    {
      "name": "personal",
      "addrs": [
        "first.last@mydomain.com",
        "secret.name@mydomain.com"
      ]
    }
  ],
  "boxes": [
    {
      "name": "spam",
      "rules": [
        {
          "match_name": "mydomain",
          "negate": true,
          "stop_check": true
        }
      ]
    },
    {
      "name": "important",
      "rules": [
        {
          "match_name": "personal"
        }
      ]
    },
    {
      "name": "all",
      "rules": [
        {
          "match_name": "default_match_all"
        }
      ]
    }
  ]
}
"""


class TestConfig(unittest.TestCase):

    def test_config(self) -> None:
        cfg = config.Config(TEST_CONFIG)
        self.assertEqual(cfg.mails_path, "/var/tmp/mails")

    def test_parse_rules(self) -> None:
        cfg = config.Config(TEST_CONFIG)
        op = config.parse_checkers(cfg)
        self.assertEqual(len(op), 3)

    def test_get_mboxes(self) -> None:
        cfg = config.Config(TEST_CONFIG)
        rules = config.parse_checkers(cfg)
        self.assertEqual(config.get_mboxes("foo@bar.com", rules), ["spam"])
        self.assertEqual(config.get_mboxes("foo@mydomain.com", rules), ["all"])
        self.assertEqual(
            config.get_mboxes("first.last@mydomain.com", rules), ["important", "all"]
        )


if __name__ == "__main__":
    unittest.main()
