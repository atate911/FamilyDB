# HTTPS and the firewall

The web page is served over HTTPS at your domain, or at the server's own address, on port 443 unless you move it. `maintain.sh https` puts it there, and two ports must be open: 80 and the web page's own.

## What the installer does by default

On a virtualenv install the installer puts [Caddy](/wiki/reference/glossary#caddy) in front of the web page, writes `/etc/caddy/Caddyfile` (one site block that passes the web page to FamilyDB), and opens ports 80 and 443 in `ufw` if it is on. FamilyDB then listens on this machine only (`WEB_HOST=127.0.0.1`) and believes Caddy about who is visiting (`WEB_TRUST_PROXY=true`).

It does none of this with `--local-only`, and on Docker it does it only when you give a domain. On Docker without a domain the web page stays on the machine, reached over an SSH tunnel; see [Install and first run](/wiki/operations/install#choices-you-can-make).

| The web page is at | Certificate |
|---|---|
| A domain | Caddy gets a public one once the name points at the server and ports 80 and 443 are open |
| A public IPv4 address | A six-day Let's Encrypt certificate that Caddy renews. It needs Caddy 2.10 or newer, which the installer fetches if the system's is older. It waits 90 seconds for the certificate |
| A private address, no certificate within 90 seconds, or a Caddy older than 2.10 | A certificate Caddy signs itself; each browser warns once |

A Caddyfile that serves something else is left alone, and the installer prints the lines to add.

## Put the page on HTTPS

For a domain, first add an A record at your registrar pointing at the server. `dig +short family.example.com` on the server prints the address once it has taken effect. Then, on the server:

```bash
sudo /opt/familydb/scripts/maintain.sh https family.example.com
```

With no domain, `https` uses the one in `.env`, else the server's own address. It writes the Caddyfile, gets the certificate, opens the ports in `ufw` if it is on, sets `WEB_DOMAIN`, `WEB_TRUST_PROXY`, `WEB_HOST` and `WEB_PUBLIC_PORT` in `.env`, and restarts FamilyDB. You should see `The page: https://family.example.com/` at the end.

Run it again after you open a provider's firewall, to try for a real certificate, or to move from an SSH tunnel to a link anyone can open.

On Docker, `https` cannot do this first step. Set `WEB_DOMAIN`, `WEB_TRUST_PROXY=true` and `COMPOSE_PROFILES=tls` in `.env`, then run:

```bash
sudo docker compose --project-directory /opt/familydb up -d
```

## Move the public port

> **Moving the web page to another port makes the old address stop working.** Bookmark the new address, and allow the new port in your hosting provider's firewall too.

A scan of the internet looks at 443. To serve the web page on another port, on the server:

```bash
sudo /opt/familydb/scripts/maintain.sh https --port random
```

`random` picks a port from 20000 to 29999; a number from 1024 to 65535 works too, and `--port 443` moves it back. It prints the new address, `https://your.domain:PORT/`. On a virtualenv install Caddy then serves HTTPS on that port alone and sends no redirect from port 80, which it listens on only while a certificate authority checks the machine. On Docker, Caddy still redirects 80 to 443, which then answers nothing. This keeps the web page out of casual sweeps and is no substitute for good passwords.

`maintain.sh port N` (or `port random`) moves FamilyDB's own port, 8080 by default, behind Caddy. The address people open does not change. N is a number from 1025 to 65535. The [General settings](/wiki/controls/settings/general) page shows both ports and cannot change them.

## The browser says the connection is not private

Caddy could not get a certificate from a public authority, so it signed one itself. The connection is still encrypted. Choose **Advanced**, then continue; each browser asks once. A domain removes the warning for good. If the authority could not reach the server, open ports 80 and 443 in your provider's firewall and run `maintain.sh https` again.

## The firewall

FamilyDB polls Telegram rather than waiting for it, so the only inbound traffic is the web page.

| Port | Open? | Why |
|---|---|---|
| 22 (SSH) | Yes | Your way in, not FamilyDB's |
| 80/tcp | Yes | Caddy's certificate check, and its redirect to HTTPS |
| 443/tcp, or your public port | Yes | The web page |
| 8080, or your `WEB_PORT` | No | FamilyDB listens on the loopback, so only Caddy reaches it |

On a virtualenv install the installer opens ports 80 and 443 (or 80 and your port) only if `ufw` is already on, and `https --port` closes the old port only if the installer opened it. On Docker the installer opens nothing in `ufw`: Docker publishes Caddy's ports itself, and `ufw` rules normally do not apply to them. Your provider's own firewall is separate, and yours to open.

> **Turning on `ufw` without allowing SSH first locks you out of the server.** The only way back is the provider's console.

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow OpenSSH
sudo ufw allow 80,443/tcp
sudo ufw enable
```

Use `80,<port>/tcp` instead if the web page is on another port. `ufw enable` asks `Proceed with operation (y|n)?`; answer `y` only after the `OpenSSH` line.

## Another proxy

Use nginx only if it already runs on the server; Caddy needs less. Install with `--local-only` so the installer leaves ports 80 and 443 to nginx. The exact steps are at the top of `deploy/nginx-familydb.conf`: copy it into place, put your domain in, run `certbot --nginx -d <domain>`, then `nginx -t` and reload. In `.env`, set `WEB_HOST=127.0.0.1`, `WEB_TRUST_PROXY=true` and a `WEB_PASSWORD` of 12 or more characters.

The proxy must pass `Host` as `$http_host`, because `$host` drops the port that the sign-in's Origin check keeps:

```nginx
proxy_pass http://127.0.0.1:8080;
proxy_set_header Host $http_host;
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
```

Do not run `maintain.sh https` on such a server: it installs Caddy and writes its own Caddyfile. For what else protects a public page, see the [checklist for a public install](/wiki/security/model#checklist-for-a-public-install).
