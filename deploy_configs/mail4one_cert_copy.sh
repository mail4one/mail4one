#!/bin/sh

#  certbot deploy hook to copy certificates to mail4one when renewed.
#  Initial setup, Install certbot(https://certbot.eff.org/) and run `certbot certonly` as root
#  Doc: https://eff-certbot.readthedocs.io/en/latest/using.html#renewing-certificates
#
#  This file is supposed to be copied to /etc/letsencrypt/renewal-hooks/deploy/
#  Change the mail domain to the one on MX record

if [ "$RENEWED_DOMAINS" = "mail.mydomain.com" ]
then
		mkdir -p /var/lib/mail4one/certs
		chmod 750 /var/lib/mail4one/certs
		chown mail4one:mail4one /var/lib/mail4one/certs
		cp "$RENEWED_LINEAGE/fullchain.pem" /var/lib/mail4one/certs/
		cp "$RENEWED_LINEAGE/privkey.pem" /var/lib/mail4one/certs/
		systemctl restart mail4one.service
		echo "$(date) Renewed and deployed certificates for mail4one" >> /var/log/mail4one-cert-renew.log
fi
