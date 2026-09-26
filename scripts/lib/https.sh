# shellcheck shell=bash
# HTTPS in front of the web page with Caddy, on a virtualenv install. Sourced by install.sh and by
# maintain.sh (`maintain.sh https`), after lib/common.sh.
#
# With a domain, Caddy gets a certificate for it the usual way. With no domain, the page is served
# at the server's own address: a public IPv4 gets a real certificate from Let's Encrypt (six-day
# certificates, which Caddy renews by itself), so no browser warns; a private one, or a Caddy too
# old to ask for it, gets one Caddy signs itself, which each browser warns about once. Either way
# the password never crosses the network in the clear, and nobody has to open a tunnel.
#
# The page is on 443 unless PUBLIC_PORT says otherwise. Any other port keeps it out of the scans
# that sweep the internet's usual ports, 443 above all; it is not a lock, since a scan of every
# port on this one machine still finds it, but it is far less often looked at. There Caddy serves
# HTTPS on that port alone, answers nothing on 80 but a certificate authority checking this machine
# (a redirect would give the port away), and asks for certificates only that way, the other way
# needing 443.

CADDYFILE=/etc/caddy/Caddyfile
# Where the packaged Caddy keeps what it has been issued (its service runs with this HOME).
CADDY_DATA=/var/lib/caddy/.local/share/caddy
# The first Caddy that can ask for an ACME profile, which is how an IP address certificate is had.
CADDY_FOR_IP="2 10"
# How long to wait for a certificate before settling for Caddy's own.
CERT_WAIT_SECONDS=90

HTTPS_KIND=""     # after setup_https: public, internal or none
HTTPS_BLOCKED=0   # after setup_https: 1 when it looked as if nothing outside could reach this machine
PUBLIC_PORT="${PUBLIC_PORT:-443}"  # before setup_https: the port the page is served on
# Where a port is picked at random: below the range Linux hands out for outgoing connections, and
# never one of the thousand ports nmap tries unless told otherwise, the 24 of them in this range.
RANDOM_PORT_FROM=20000
RANDOM_PORT_TO=29999
NMAP_FAVOURITES=" 20000 20005 20031 20221 20222 20828 21571 22939 23502 24444 24800 25734 25735 26214 27000 27352 27353 27355 27356 27715 28201 28211 29672 29831 "

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
  apt_install_noted curl gnupg >/dev/null 2>&1 || true
  noting_new "$keyring" keyring
  noting_new "$sources" apt-source
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
    | as_root gpg --dearmor --yes -o "$keyring" 2>/dev/null || return 1
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
    | as_root tee "$sources" >/dev/null || return 1
  as_root chmod o+r "$keyring" "$sources"
  as_root env DEBIAN_FRONTEND=noninteractive apt-get update -qq >/dev/null 2>&1 || return 1
  # --force-confold: keep a Caddyfile that is already there rather than stop to ask about it.
  apt_install_noted -o Dpkg::Options::=--force-confold caddy >/dev/null 2>&1
}

public_url() { # public_url SITE - the address a browser opens, with the port unless it is 443
  if [ "$PUBLIC_PORT" = 443 ]; then printf 'https://%s/' "$1"; else printf 'https://%s:%s/' "$1" "$PUBLIC_PORT"; fi
}

web_ports_rule() { # the ufw rule the page needs: 80 for the certificate, and the page's own port
  printf '80,%s/tcp' "$PUBLIC_PORT"
}

port_listening() { # port_listening PORT - something on this machine listens on that TCP port
  have ss && ss -ltnH 2>/dev/null | awk '{print $4}' | grep -qE "[:.]${1}\$"
}

random_public_port() { # a port at random: not a favourite of scanners, and not taken here
  local tries=0 candidate
  while [ "$tries" -lt 200 ]; do
    tries=$((tries + 1))
    candidate=$((RANDOM_PORT_FROM + (RANDOM * 32768 + RANDOM) % (RANDOM_PORT_TO - RANDOM_PORT_FROM + 1)))
    case "$NMAP_FAVOURITES" in *" ${candidate} "*) continue ;; esac
    port_listening "$candidate" && continue
    printf '%s' "$candidate"
    return 0
  done
  return 1
}

choose_public_port() { # choose_public_port WANTED APP_PORT - a port to serve on, or why not
  local wanted="$1" app_port="$2"
  case "$wanted" in
    random) random_public_port || { printf 'no free port turned up at random; name one' >&2; return 1; }; return 0 ;;
    ''|*[!0-9]*) printf '%s is not a port number' "$wanted" >&2; return 1 ;;
  esac
  [ "${#wanted}" -le 5 ] || { printf 'a port for the page is 443, or one from 1024 to 65535' >&2; return 1; }
  wanted=$((10#$wanted))
  if [ "$wanted" != 443 ] && { [ "$wanted" -lt 1024 ] || [ "$wanted" -gt 65535 ]; }; then
    printf 'a port for the page is 443, or one from 1024 to 65535' >&2
    return 1
  fi
  if [ "$wanted" = "$app_port" ]; then
    printf 'port %s is where FamilyDB itself listens, behind Caddy; choose another' "$wanted" >&2
    return 1
  fi
  printf '%s' "$wanted"
}

open_web_ports() { # in ufw, the one firewall this knows; say_how_to_open speaks of a provider's own
  local rule
  rule="$(web_ports_rule)"
  if have ufw && as_root ufw status 2>/dev/null | grep -q "^Status: active"; then
    # Written down only when it was not there already: taking it away again must not close a
    # door somebody else opened.
    as_root ufw status 2>/dev/null | grep -qE "^${rule}" || ledger ufw "$rule"
    if as_root ufw allow "$rule" >/dev/null 2>&1; then
      ok "Opened ports 80 and ${PUBLIC_PORT} in this machine's firewall."
    else
      warn "Could not open ports 80 and ${PUBLIC_PORT} with ufw. Do it with: sudo ufw allow ${rule}"
    fi
  fi
}

close_old_web_ports() { # close_old_web_ports OLD_PORT - after a move, the rule for the old port
  local old="$1" rule
  [ -n "$old" ] && [ "$old" != "$PUBLIC_PORT" ] || return 0
  rule="80,${old}/tcp"
  have ufw && as_root ufw status 2>/dev/null | grep -qE "^${rule}" || return 0
  # Only a rule the install opened. The new rule keeps 80 open, so this closes only the old port.
  if ledger_has ufw "$rule" && as_root ufw delete allow "$rule" >/dev/null 2>&1; then
    ok "Closed port ${old} in this machine's firewall; nothing listens there now."
  else
    note "Port ${old} is still open in this machine's firewall, and nothing listens there now."
    note "If nothing else needs it: sudo ufw delete allow ${rule}"
  fi
}

write_caddyfile() { # write_caddyfile SITE PORT HOW - HOW is domain, public-ip or internal
  local site="$1" port="$2" how="$3" tls="" global="" acme=""
  if [ "$PUBLIC_PORT" != 443 ]; then
    # HTTPS on its own port, and no redirect on 80 to tell a passing scan where that is.
    global=$'{\n\thttps_port '"${PUBLIC_PORT}"$'\n\tauto_https disable_redirects\n}\n'
    # A certificate authority checks this machine on 80 or on 443, never on another port, so
    # only the check on 80 can work; Caddy listens there just while it is being checked.
    acme=$'\t\t\tdisable_tlsalpn_challenge\n'
  fi
  case "$how" in
    public-ip) tls=$'\ttls {\n\t\tissuer acme {\n\t\t\tprofile shortlived\n'"${acme}"$'\t\t}\n\t}\n' ;;
    internal) tls=$'\ttls internal\n' ;;
    *) if [ -n "$acme" ]; then tls=$'\ttls {\n\t\tissuer acme {\n'"${acme}"$'\t\t}\n\t}\n'; fi ;;
  esac
  noting_replaced "$CADDYFILE"
  {
    printf '# FamilyDB, written by its installer. `sudo %s/scripts/maintain.sh https` writes it again.\n' \
      "${TARGET:-${REPO_ROOT:-/opt/familydb}}"
    printf '%s%s {\n%s\treverse_proxy 127.0.0.1:%s\n}\n' "$global" "$site" "$tls" "$port"
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
  curl -sS --max-time 5 -o /dev/null "$(public_url "$site")healthz" 2>/dev/null
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
    local had_caddy_user=0
    id caddy >/dev/null 2>&1 && had_caddy_user=1
    step "Installing Caddy, which holds the certificate" apt_install_noted caddy || true
    # The package makes an account of its own to run as; it goes when Caddy does.
    [ "$had_caddy_user" = 0 ] && id caddy >/dev/null 2>&1 && noting_user caddy
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
  if [ "$PUBLIC_PORT" != 443 ] && port_listening "$PUBLIC_PORT" && ! grep -q "https_port ${PUBLIC_PORT}$" "$CADDYFILE" 2>/dev/null; then
    warn "Something on this machine already listens on port ${PUBLIC_PORT}, so the page cannot."
    note "Choose another: sudo ${TARGET:-${REPO_ROOT:-/opt/familydb}}/scripts/maintain.sh https --port random"
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
      ok "Caddy serves $(public_url "$site") and gets its certificate once the name leads here."
      ;;
    internal)
      HTTPS_KIND="internal"
      ok "Caddy serves $(public_url "$site") with a certificate of its own."
      ;;
    public-ip)
      say "Asking Let's Encrypt for a certificate for ${site}. This can take a minute."
      while [ "$waited" -lt "$CERT_WAIT_SECONDS" ]; do
        if has_public_certificate "$site"; then
          HTTPS_KIND="public"
          ok "$(public_url "$site") has a real certificate: no browser will warn."
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
    warn "Nothing outside seems able to reach this server on ports 80 and ${PUBLIC_PORT}."
    note "Most providers have a firewall of their own, in their control panel (it may be called a"
    note "firewall, a security group or networking). Allow TCP ports 80 and ${PUBLIC_PORT} there, then run:"
    note "  sudo ${TARGET:-${REPO_ROOT:-/opt/familydb}}/scripts/maintain.sh https"
  elif [ "$PUBLIC_PORT" != 443 ]; then
    note "If the provider has a firewall of its own, in its control panel, allow TCP port"
    note "${PUBLIC_PORT} there, and 80 too, which a certificate authority uses to check this machine."
  fi
  if [ "$HTTPS_KIND" = internal ]; then
    note "The browser warns the first time that the connection is not private: the certificate is"
    note "this server's own rather than a public authority's. Choose Advanced, then continue. The"
    note "connection is still encrypted, and a domain name later removes the warning."
  fi
  : "$site"
}
