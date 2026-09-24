# shellcheck shell=bash
# HTTPS in front of the web page with Caddy, on a virtualenv install. Sourced by install.sh and by
# maintain.sh (`maintain.sh https`), after lib/common.sh.
#
# With a domain, Caddy gets a certificate for it the usual way. With no domain, the page is served
# at the server's own address: a public IPv4 gets a real certificate from Let's Encrypt (six-day
# certificates, which Caddy renews by itself), so no browser warns; a private one, or a Caddy too
# old to ask for it, gets one Caddy signs itself, which each browser warns about once. Either way
# the password never crosses the network in the clear, and nobody has to open a tunnel.

CADDYFILE=/etc/caddy/Caddyfile
# Where the packaged Caddy keeps what it has been issued (its service runs with this HOME).
CADDY_DATA=/var/lib/caddy/.local/share/caddy
# The first Caddy that can ask for an ACME profile, which is how an IP address certificate is had.
CADDY_FOR_IP="2 10"
# How long to wait for a certificate before settling for Caddy's own.
CERT_WAIT_SECONDS=90

HTTPS_KIND=""     # after setup_https: public, internal or none
HTTPS_BLOCKED=0   # after setup_https: 1 when it looked as if nothing outside could reach this machine

is_ipv4() { # a dotted IPv4 address, each part 0-255
  printf '%s' "$1" | grep -Eq '^([0-9]{1,3}\.){3}[0-9]{1,3}$' || return 1
  local IFS=. part
  for part in $1; do [ "$part" -le 255 ] || return 1; done
}

is_private_ipv4() { # the ranges nothing on the internet can reach directly
  case "$1" in
    10.*|127.*|192.168.*|169.254.*) return 0 ;;
    172.1[6-9].*|172.2[0-9].*|172.3[01].*) return 0 ;;
    100.6[4-9].*|100.[7-9][0-9].*|100.1[01][0-9].*|100.12[0-7].*) return 0 ;;  # carrier NAT
  esac
  return 1
}

this_address() { # the address a browser would use: this machine's first public IPv4, else a private one
  local found private=""
  for found in $(hostname -I 2>/dev/null); do
    is_ipv4 "$found" || continue
    if is_private_ipv4 "$found"; then
      [ -n "$private" ] || private="$found"
    else
      printf '%s' "$found"
      return 0
    fi
  done
  printf '%s' "$private"
}

caddy_is_at_least() { # caddy_is_at_least MAJOR MINOR
  local version major minor
  version="$(caddy version 2>/dev/null | sed -n 's/^v\{0,1\}\([0-9][0-9]*\)\.\([0-9][0-9]*\).*/\1 \2/p' | head -1)"
  [ -n "$version" ] || return 1
  read -r major minor <<<"$version"
  [ "$major" -gt "$1" ] || { [ "$major" -eq "$1" ] && [ "$minor" -ge "$2" ]; }
}

caddy_from_its_own_repository() { # a current Caddy, from the repository Caddy's own guide uses
  local keyring=/usr/share/keyrings/caddy-stable-archive-keyring.gpg
  local sources=/etc/apt/sources.list.d/caddy-stable.list
  as_root env DEBIAN_FRONTEND=noninteractive apt-get install -y -qq curl gnupg >/dev/null 2>&1 || true
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
    | as_root gpg --dearmor --yes -o "$keyring" 2>/dev/null || return 1
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
    | as_root tee "$sources" >/dev/null || return 1
  as_root chmod o+r "$keyring" "$sources"
  as_root env DEBIAN_FRONTEND=noninteractive apt-get update -qq >/dev/null 2>&1 || return 1
  # --force-confold: keep a Caddyfile that is already there rather than stop to ask about it.
  as_root env DEBIAN_FRONTEND=noninteractive apt-get install -y -qq -o Dpkg::Options::=--force-confold \
    caddy >/dev/null 2>&1
}

open_web_ports() { # ufw is the one firewall this knows; it says so when there may be another
  if have ufw && as_root ufw status 2>/dev/null | grep -q "^Status: active"; then
    if as_root ufw allow 80,443/tcp >/dev/null 2>&1; then
      ok "Opened ports 80 and 443 in this machine's firewall."
    else
      warn "Could not open ports 80 and 443 with ufw. Do it with: sudo ufw allow 80,443/tcp"
    fi
  fi
}

write_caddyfile() { # write_caddyfile SITE PORT HOW - HOW is domain, public-ip or internal
  local site="$1" port="$2" how="$3" tls=""
  case "$how" in
    public-ip) tls=$'\ttls {\n\t\tissuer acme {\n\t\t\tprofile shortlived\n\t\t}\n\t}\n' ;;
    internal) tls=$'\ttls internal\n' ;;
  esac
  {
    printf '# FamilyDB, written by its installer. `sudo %s/scripts/maintain.sh https` writes it again.\n' \
      "${TARGET:-${REPO_ROOT:-/opt/familydb}}"
    printf '%s {\n%s\treverse_proxy 127.0.0.1:%s\n}\n' "$site" "$tls" "$port"
  } | as_root tee "$CADDYFILE" >/dev/null
}

caddy_reload() { # load the Caddyfile, and say what is wrong with it rather than fail quietly
  if ! as_root caddy validate --adapter caddyfile --config "$CADDYFILE" >/dev/null 2>&1; then
    return 1
  fi
  as_root systemctl reload-or-restart caddy >/dev/null 2>&1
}

has_public_certificate() { # has_public_certificate SITE - Caddy holds one a browser trusts
  local site="$1"
  if as_root find "${CADDY_DATA}/certificates" -name "${site}.crt" -not -path '*/local/*' 2>/dev/null \
    | grep -q .; then
    return 0
  fi
  curl -sS --max-time 5 -o /dev/null "https://${site}/healthz" 2>/dev/null
}

sounds_unreachable() { # Caddy's log says the certificate authority could not reach this machine
  as_root journalctl -u caddy --since "-5 min" --no-pager 2>/dev/null \
    | grep -qiE "firewall problem|Timeout during connect|connection refused|no route to host"
}

setup_https() { # setup_https SITE PORT - Caddy in front of 127.0.0.1:PORT for SITE, a domain or an IPv4
  local site="$1" port="$2" how waited=0
  HTTPS_KIND="none"
  HTTPS_BLOCKED=0
  if ! have caddy && have apt-get; then
    step "Installing Caddy, which holds the certificate" \
      as_root env DEBIAN_FRONTEND=noninteractive apt-get install -y -qq caddy || true
  fi
  if ! have caddy; then
    warn "Caddy is not installed, so the page has no HTTPS yet."
    note "Install it (sudo apt install caddy), then: sudo ${TARGET:-${REPO_ROOT:-/opt/familydb}}/scripts/maintain.sh https"
    return 1
  fi
  if [ -f "$CADDYFILE" ] && ! grep -q -e '/usr/share/caddy' -e 'reverse_proxy 127.0.0.1' -e 'FamilyDB' "$CADDYFILE"; then
    warn "${CADDYFILE} already serves something else, so it was left alone."
    note "Add this to it yourself:  ${site} { reverse_proxy 127.0.0.1:${port} }"
    return 1
  fi
  open_web_ports

  if ! is_ipv4 "$site"; then
    how=domain
  elif is_private_ipv4 "$site"; then
    how=internal  # no public authority can reach a private address to check it
  else
    how=public-ip
    # shellcheck disable=SC2086  # two numbers, meant to be split
    if ! caddy_is_at_least $CADDY_FOR_IP; then
      step "Updating Caddy from Caddy's own repository, so the page can have a real certificate without a domain" \
        caddy_from_its_own_repository || true
      # shellcheck disable=SC2086
      caddy_is_at_least $CADDY_FOR_IP || how=internal
    fi
  fi

  write_caddyfile "$site" "$port" "$how"
  if ! caddy_reload; then
    if [ "$how" = public-ip ]; then
      how=internal
      write_caddyfile "$site" "$port" "$how"
      caddy_reload || { warn "Caddy would not load its configuration; see: sudo journalctl -u caddy -n 30"; return 1; }
    else
      warn "Caddy would not load its configuration; see: sudo journalctl -u caddy -n 30"
      return 1
    fi
  fi

  case "$how" in
    domain)
      HTTPS_KIND="public"
      ok "Caddy serves https://${site}/ and gets its certificate once the name leads here."
      ;;
    internal)
      HTTPS_KIND="internal"
      ok "Caddy serves https://${site}/ with a certificate of its own."
      ;;
    public-ip)
      say "Asking Let's Encrypt for a certificate for ${site}. This can take a minute."
      while [ "$waited" -lt "$CERT_WAIT_SECONDS" ]; do
        if has_public_certificate "$site"; then
          HTTPS_KIND="public"
          ok "https://${site}/ has a real certificate: no browser will warn."
          return 0
        fi
        sleep 5
        waited=$((waited + 5))
      done
      sounds_unreachable && HTTPS_BLOCKED=1
      warn "No certificate came back for ${site}, so Caddy uses one of its own for now."
      write_caddyfile "$site" "$port" internal
      caddy_reload || true
      HTTPS_KIND="internal"
      ;;
  esac
  return 0
}

say_how_to_open() { # say_how_to_open SITE - the lines a person needs to get to the page
  local site="$1"
  if [ "$HTTPS_BLOCKED" = 1 ]; then
    warn "Nothing outside seems able to reach this server on ports 80 and 443."
    note "Most providers have a firewall of their own, in their control panel (it may be called a"
    note "firewall, a security group or networking). Allow TCP ports 80 and 443 there, then run:"
    note "  sudo ${TARGET:-${REPO_ROOT:-/opt/familydb}}/scripts/maintain.sh https"
  fi
  if [ "$HTTPS_KIND" = internal ]; then
    note "The browser warns the first time that the connection is not private: the certificate is"
    note "this server's own rather than a public authority's. Choose Advanced, then continue. The"
    note "connection is still encrypted, and a domain name later removes the warning."
  fi
  : "$site"
}
