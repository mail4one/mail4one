#!/bin/sh

#  certbot deploy hook to copy certificates to mail4one when renewed.
#  Initial setup, Install certbot(https://certbot.eff.org/) and run `certbot certonly` as root
#  Doc: https://eff-certbot.readthedocs.io/en/latest/using.html#renewing-certificates
#
#  This file is supposed to be copied to /etc/letsencrypt/renewal-hooks/deploy/
#  Change the mail domain to the one on MX record

set -eu

if [ "$RENEWED_DOMAINS" = "mail.mydomain.com" ]
then
	app=mail4one
	appuser=$app
	certpath="/var/lib/$app/certs"

	mkdir -p "$certpath"
	chmod 750 "$certpath"

	chown $appuser:$appuser "$certpath"
	install -o "$appuser" -g "$appuser" -m 444 "$RENEWED_LINEAGE/fullchain.pem" -t "$certpath"
	install -o "$appuser" -g "$appuser" -m 400 "$RENEWED_LINEAGE/privkey.pem" -t "$certpath"

	systemctl restart $app.service
	echo "$(date) Renewed and deployed certificates for $app" >> /var/log/cert-renew.log
fi
