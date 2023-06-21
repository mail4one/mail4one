#!/bin/sh

#  certbot deploy hook to copy certificates to mail4one when renewed.
#  This file is supposed to be copied to /etc/letsencrypt/renewal-hooks/deploy/
#  Change the mail domain to the one on MX record

set -x


if [ "$RENEWED_DOMAINS" = "mail.mydomain.com" ]
then
		mkdir -p /var/lib/mail4one/certs
		chmod 500 /var/lib/mail4one/certs
		chown mail4one:mail4one /var/lib/mail4one/certs
		cp "$RENEWED_LINEAGE/fullchain.pem" /var/lib/mail4one/certs/
		cp "$RENEWED_LINEAGE/privkey.pem" /var/lib/mail4one/certs/
		systemctl restart mail4one.service
fi
