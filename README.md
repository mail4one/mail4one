# Mail4one

Personal mail server for a single user or a small family. Written in pure python with [minimal dependencies](Pipfile).
Designed for dynamic alias based workflow where a different alias is used for each purpose.

# Getting started

 1. Get a domain name
 1. Get a VPS (or a home server). Setup firewall rules for receive on port 25, 995, 465
 1. Setup [MX record](#dns-records-receiving)
 1. [Build](#building-from-source) / Download latest release - `mail4one.pyz`
 1. Generate `config.json` from [config.sample](deploy_configs/config.sample)
 1. Run `./mail4one.pyz -c config.json`
 1. Setup systemd service and TLS certificates. See [deploy_configs](deploy_configs/) for examples

# Sending email

Mail4one only takes care of receiving and serving email. For sending email, use an external service like below

* https://www.smtp2go.com/pricing/
* https://www.mailgun.com/pricing/
* https://sendgrid.com/free/

Most of them have generous free tier which is more than enough for personal use.

Sending email is tricky. Even if everything is correctly setup (DMARC, DKIM, SPF), popular email vendors like google, microsoft may mark emails sent from your IP as spam for no reason. Hence using a dedicated service is the only reliable way to send emails.

# Community

Original source is at https://gitea.balki.me/balki/mail4one

For issues, pull requests, discussions, please use github mirror: https://github.com/mail4one/mail4one

# Documentation

See files under [deploy_configs](deploy_configs/) for configuring and deploying to a standard systemd based linux system (e.g. debian, ubuntu, fedora, archlinux etc). [config.sample](deploy_configs/config.sample) has inline comments for more details. Feel free create github issue/discussions for support.

## DNS Records (Receiving)

If you want to receive email for `john@example.com` and your VPS IP address is `1.2.3.4`. Following record needs to be created

|Type  | Name             | Target               | Notes                                                |
|------|------------------|----------------------|------------------------------------------------------|
| A    | mail.example.com | `1.2.3.4`              |                                                      |
| AAAA | mail.example.com | `abcd:1234::1234::1`   | Optional, add if available                           |
| MX   | example.com      | `mail.example.com`     |                                                      |
| MX   | sub.example.com  | `mail.example.com`     | Optional, to receive emails like foo@sub.example.com |

For sending emails `DMARC`, `DKIM` and `SPF` records need to be set. Please refer to email [sending](#sending-email) provider for details.

# Building from source

Make sure to have make, git, python >= 3.9, and pip installed in your system and run below

    make build

This should generate `mail4one.pyz` in current folder. This is a [executable python archive](https://docs.python.org/3/library/zipapp.html). Should be runnable as `./mail4one.pyz` or as `python3 mail4one.pyz`.

# Roadmap (Planned features for future)

* Other ways to install and update (PIP, AUR, docker etc)
* Write dedicated documentation
* Test with more email clients ([Thunderbird](https://www.thunderbird.net/) and [k9mail](https://k9mail.app/) are tested now)
* IMAP support
* Web UI for editing config ([WIP](https://github.com/mail4one/mail4one/tree/webform))
* Support email submission from client to forward to other senders or direct delivery
* Optional SPAM filtering
* Optional DMARC,SPF,DKIM verification
* Webmail Client
* Web UI to view graphs and smart reports
