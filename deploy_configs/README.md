# Deployment command line example

Example terminal session for deploying. ssh to your VPS and follow along. Minor differences may be required. e.g. if you are already root, skip `sudo`. If curl is missing, use wget.

## Check python version

Python version should be a supported (as of now 3.9 and above)
```sh
python3 -V
```

## Choose release
```sh
RELEASE=v1.0
```

## Download App
```sh
curl -OL "https://gitea.balki.me/balki/mail4one/releases/download/$RELEASE/mail4one.pyz"
chmod 555 mail4one.pyz
```

## Download sample configurations
```sh
curl -OL "https://gitea.balki.me/balki/mail4one/raw/tag/$RELEASE/deploy_configs/mail4one.service"
curl -OL "https://gitea.balki.me/balki/mail4one/raw/tag/$RELEASE/deploy_configs/mail4one.conf"
curl -OL "https://gitea.balki.me/balki/mail4one/raw/tag/$RELEASE/deploy_configs/mail4one_cert_copy.sh"
```

## Generate Password hash

This can be done in any machine. Do this once for each user. Every time a new hash is generated as a random salt is used. Even if you are using the same password for multiple clients, it is recommended to generate different hashes for each.

```sh
./mail4one.pyz -g
./mail4one.pyz -g <password> # also works but the password is saved in the shell commandline history
```

## Generate config.json

Edit [config.sample](config.sample) in your local machine and convert to config.json (See [here](./config.sample#L5) for some tools).

Then copy the config.json to your vps
```sh
scp config.json user@vps:~/
# or run below in vps terminal
cat > config.json
<paste json config from clibboard
<Ctrl + D>

# move to /etc

# This should show number of lines in your config
wc -l config.json
sudo mv config.json /etc/mail4one/config.json
```

## Create mail4one user

```sh
sudo mkdir -p /etc/sysusers.d/
sudo cp mail4one.conf /etc/sysusers.d/
sudo systemctl restart systemd-sysusers
# This should show the new user created
id mail4one
```
## Copy app
```sh
sudo cp mail4one.pyz /usr/local/bin/mail4one
# This should show executable permissions and should be owned by root
ls -l /usr/local/bin/mail4one
```

## Setup mail4one.service
```sh
sudo cp mail4one.service /etc/systemd/system/mail4one.service
sudo systemctl daemon-reload
sudo systemctl enable --now mail4one.service 
systemctl status mail4one
```
Above command should fail as the TLS certificates don't exist yet.

## Setup TLS certificates 
Install [certbot](https://certbot.eff.org/) and run below command. Follow instructions to create TLS certificates. Usually you want certificate for domain name like `mail.example.com`
```sh
sudo certbot certonly
sudo cp /etc/letsencrypt/live/mail.example.com/{fullchain,privkey}.pem  /var/lib/mail4one/certs/
sudo chown mail4one:mail4one /var/lib/mail4one/certs/{fullchain,privkey}.pem

# Edit mail4one_cert_copy.sh to update your domain name
sudo cp mail4one_cert_copy.sh /etc/letsencrypt/renewal-hooks/deploy/
sudo chmod +x /etc/letsencrypt/renewal-hooks/deploy/mail4one_cert_copy.sh
```
## Restart service and check logs
```sh
sudo systemctl restart mail4one.service
systemctl status mail4one.service
cat /var/log/mail4one/mail4one.log
```

## Testing dns and firewall
In vps
```sh
mkdir test_dir
touch test_dir/{a,b,c}
cd test_dir
python3 -m http.server 25
```
In local machine or a browser
You should see file listing a, b, c. Repeat for port 465, 995 to make sure firewall rules and dns is working
```sh
curl http://mail.example.com:25
```
If not working, refer to VPS settings and OS firewall settings.
