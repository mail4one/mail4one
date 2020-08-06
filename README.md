# mail4one

Mail server for single user #asyncio #python

## Features

* smtp server with STARTTLS
* pop3 server with TLS
* Both running on single thread using asyncio
* Saves mails in simple Maildir format (i.e one file per email message)
* After opening port, drops root privileges. So the process will not running as `nobody`

## How to use

    echo -n "balki is awesome+<YOUR PASSWORD>" | sha256sum 
    pipenv install
    sudo $(pipenv --venv)/bin/python ./run.py --certfile /etc/letsencrypt/live/your.domain.com/fullchain.pem --keyfile /etc/letsencrypt/live/your.domain.com/privkey.pem /var/mails --password_hash <PASSWORD_HASH_FROM_ABOVE>

## Just pop server for debugging

    pipenv run python -m mail4one.pop3 /path/to/mails 9995 your_password

## Nextups

 * Support sending emails - Also support for popular services like mailgun/sendgrid 
 * Smart assistant like functionality. For e.g. 
   * You don't need all emails of package deliver status. Just the latest one would be enough.
   * Some type of emails can auto expire. Old newsletters are not very helpful
   * Aggregate emails for weekend reading.
 * Small webserver
 * SPAM filtering - not that important as you can use unique addresses for each service. e.g. facebook@mydomian.com, bankac@mydomain.com, reddit@mydomain.com etc. You can easily figure out who sold your address to spammers and block it.

## Goals
 * Intended to be used for one person. So won't have features that don't make sense in this context. e.g. LDAP AUTH, Mail quota, etc,
 * Supports only python3.7. No plans to support older versions

## Known to work
 * Server: Google Cloud f1-micro with Ubuntu 18.04 - Always Free instance
 * Clients: thunderbird, evolution, k9mail
 * smtp: Received email from all. Didn't see any drops. Tested from gmail, protonmail, reddit and few others

## Contribution

Pull requests and issues welcome
