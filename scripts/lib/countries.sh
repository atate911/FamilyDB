#!/usr/bin/env bash
# Letting in only the countries the family is in: an nftables table that drops every new
# connection to this machine, on any port, from an address outside them. Source it, do not run it;
# `maintain.sh countries` is what uses it.
#
# What it lets in, whatever the country: this machine talking to itself, replies to connections
# this machine made (Telegram, the AI companies, updates: the bot only ever calls out), the
# provider's DHCP, private and link-local networks (the provider's own, Docker's, a VPN's), and
# the addresses in the allow file, which starts with whoever is connected over SSH when it is
# turned on. Everything else from outside the countries is dropped without a reply.
#
# The address lists are ipdeny.com's, one per country, built from the regional registries. They
# are fetched again each week; a download that fails, or that has shrunk by more than half, is
# not used, and the last good list stays in force.
#
# One opening it makes by itself: port 80, to everyone, while the page's certificate is missing
# or its renewal is overdue. Let's Encrypt checks a domain from more than one place before it
# issues a certificate, and they need not all be in the countries let in. Caddy renews once a
# third of a certificate's life is left, so one still unrenewed half a day into that stretch is
# being turned away; the window opens then, and shuts again as soon as a fresh certificate is
# served. Port 80 answers nothing but that check and a redirect. The hourly check does this, and
# `maintain.sh countries` and `maintain.sh https` open it themselves when they need a certificate.

[ -n "${FAMILYDB_COUNTRIES_SOURCED:-}" ] && return 0
FAMILYDB_COUNTRIES_SOURCED=1

COUNTRIES_DIR="${COUNTRIES_DIR:-/etc/familydb-countries}"
COUNTRIES_TABLE=familydb_countries
COUNTRIES_UNIT=/etc/systemd/system/familydb-countries.service
COUNTRIES_REFRESH=/etc/systemd/system/familydb-countries-refresh.service
COUNTRIES_TIMER=/etc/systemd/system/familydb-countries-refresh.timer
# shellcheck disable=SC2034  # read by maintain.sh
COUNTRIES_UNDO=familydb-countries-undo
# Present while port 80 is open to everyone for the certificate (above).
COUNTRIES_WINDOW="${COUNTRIES_DIR}/certificate-window"
# shellcheck disable=SC2034  # read by maintain.sh
LIST_MAX_AGE=604800  # a week: the hourly check fetches the lists again when they are older
# Never dropped, whatever the country: private, shared (CGNAT, Tailscale) and link-local ranges.
ALWAYS_ALLOWED4="10.0.0.0/8 100.64.0.0/10 169.254.0.0/16 172.16.0.0/12 192.168.0.0/16"
ALWAYS_ALLOWED6="fc00::/7 fe80::/10"

countries_url() { # countries_url CC v4|v6
  local cc
  cc="$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')"
  if [ "$2" = v4 ]; then
    printf 'https://www.ipdeny.com/ipblocks/data/aggregated/%s-aggregated.zone' "$cc"
  else
    printf 'https://www.ipdeny.com/ipv6/ipaddresses/aggregated/%s-aggregated.zone' "$cc"
  fi
}

is_country_code() { printf '%s' "$1" | grep -qE '^[A-Za-z]{2}$'; }

is_address() { # is_address ADDR - an IPv4 or IPv6 address, or a range of either
  printf '%s' "$1" | grep -qE '^([0-9]{1,3}\.){3}[0-9]{1,3}(/[0-9]{1,2})?$' && return 0
  printf '%s' "$1" | grep -qE '^[0-9A-Fa-f:]*:[0-9A-Fa-f:]*(/[0-9]{1,3})?$'
}

is_v6() { case "$1" in *:*) return 0 ;; esac; return 1; }

list_is_sound() { # list_is_sound v4|v6 FILE [PREVIOUS] - every line a range, and not shrunk by half
  local family="$1" file="$2" previous="${3:-}" pattern count before
  if [ "$family" = v4 ]; then
    pattern='^([0-9]{1,3}\.){3}[0-9]{1,3}/[0-9]{1,2}$'
  else
    pattern='^[0-9A-Fa-f:]+/[0-9]{1,3}$'
  fi
  [ -s "$file" ] || return 1
  grep -vE "$pattern" "$file" | grep -q '[^[:space:]]' && return 1
  count="$(grep -cE "$pattern" "$file")"
  [ "$count" -gt 0 ] || return 1
  if [ -n "$previous" ] && [ -s "$previous" ]; then
    before="$(grep -cE "$pattern" "$previous")"
    [ "$count" -ge $((before / 2)) ] || return 1
  fi
  return 0
}

ssh_peers() { # the public addresses connected to this machine over SSH right now, one a line
  {
    [ -n "${SSH_CLIENT:-}" ] && printf '%s\n' "${SSH_CLIENT%% *}"
    who -m 2>/dev/null | sed -n 's/.*(\([0-9A-Fa-f:.]*\)).*/\1/p'
    ss -Htn state established '( sport = :22 )' 2>/dev/null | awk '{print $NF}' \
      | sed -E 's/^\[?([0-9A-Fa-f:.]+)\]?:[0-9]+$/\1/; s/^::ffff://'
  } | while read -r peer; do
    is_address "$peer" || continue
    case "$peer" in 127.*|::1|10.*|192.168.*|fe80:*) continue ;; esac
    printf '%s\n' "$peer"
  done | sort -u
}

_elements() { # _elements ADDR... - an nft element list, one a line
  local first=1 addr
  for addr in "$@"; do
    [ -n "$addr" ] || continue
    if [ "$first" = 1 ]; then printf '      %s' "$addr"; first=0; else printf ',\n      %s' "$addr"; fi
  done
  printf '\n'
}

countries_rules() { # countries_rules - the whole table, from the lists and the allow file, on stdout
  local cc v4=() v6=() addr
  read -ra v4 <<<"$ALWAYS_ALLOWED4"
  read -ra v6 <<<"$ALWAYS_ALLOWED6"
  for cc in $(cat "${COUNTRIES_DIR}/countries"); do
    [ -s "${COUNTRIES_DIR}/lists/${cc}.v4" ] && mapfile -t -O "${#v4[@]}" v4 < "${COUNTRIES_DIR}/lists/${cc}.v4"
    [ -s "${COUNTRIES_DIR}/lists/${cc}.v6" ] && mapfile -t -O "${#v6[@]}" v6 < "${COUNTRIES_DIR}/lists/${cc}.v6"
  done
  if [ -s "${COUNTRIES_DIR}/allow" ]; then
    while read -r addr _; do
      case "$addr" in ''|'#'*) continue ;; esac
      if is_v6 "$addr"; then v6+=("$addr"); else v4+=("$addr"); fi
    done < "${COUNTRIES_DIR}/allow"
  fi
  local window=""
  if [ -e "$COUNTRIES_WINDOW" ]; then
    window='    tcp dport 80 accept comment "the certificate window: open while a certificate is due"'
  fi
  cat <<EOF
# FamilyDB's country filter, written by maintain.sh countries. Do not edit it: change the
# countries or ${COUNTRIES_DIR}/allow and run maintain.sh countries again.
# The first two lines make loading it replace the table whole, in one go.
table inet ${COUNTRIES_TABLE}
delete table inet ${COUNTRIES_TABLE}
table inet ${COUNTRIES_TABLE} {
  set allowed4 {
    type ipv4_addr; flags interval; auto-merge
    elements = {
$(_elements "${v4[@]}")    }
  }
  set allowed6 {
    type ipv6_addr; flags interval; auto-merge
    elements = {
$(_elements "${v6[@]}")    }
  }
  chain gate {
    iif "lo" accept
    ct state established,related accept
    udp sport 67 udp dport 68 accept
    udp sport 547 udp dport 546 accept
    icmpv6 type { nd-neighbor-solicit, nd-neighbor-advert, nd-router-advert, nd-router-solicit } accept
${window}
    ip saddr @allowed4 accept
    ip6 saddr @allowed6 accept
    counter drop
  }
  chain input {
    type filter hook input priority -10; policy accept;
    jump gate
  }
  # What Docker publishes arrives here rather than at input.
  chain forward {
    type filter hook forward priority -10; policy accept;
    jump gate
  }
}
EOF
}

certificate_state() { # certificate_state SITE PORT - none, good, due or overdue, then the days left
  local site="$1" port="$2" dates start end now left third
  have openssl || { echo "unknown 0"; return 0; }
  # Only a certificate a browser would take counts: a trusted one, for this name.
  dates="$(printf '' | timeout 8 openssl s_client -connect "127.0.0.1:${port}" -servername "$site" \
      -verify_hostname "$site" -verify_return_error ${CERT_CAFILE:+-CAfile "$CERT_CAFILE"} 2>/dev/null \
    | openssl x509 -noout -startdate -enddate 2>/dev/null)" || dates=""
  if [ -z "$dates" ]; then echo "none 0"; return 0; fi
  start="$(date -d "$(printf '%s\n' "$dates" | sed -n 's/^notBefore=//p')" +%s)"
  end="$(date -d "$(printf '%s\n' "$dates" | sed -n 's/^notAfter=//p')" +%s)"
  now="${CERT_NOW:-$(date +%s)}"
  left=$(( (end - now) / 86400 ))
  third=$(( (end - start) / 3 ))
  if [ $((end - now)) -gt "$third" ]; then echo "good $left"
  elif [ $((end - now)) -gt $((third - 43200)) ]; then echo "due $left"
  else echo "overdue $left"
  fi
}

countries_turned_away() { # how many connections the filter has dropped since it was loaded
  as_root nft list chain inet "$COUNTRIES_TABLE" gate 2>/dev/null \
    | sed -n 's/.*counter packets \([0-9]*\).*/\1/p' | head -1
}

countries_on_now() { as_root nft list table inet "$COUNTRIES_TABLE" >/dev/null 2>&1; }

countries_write_units() { # countries_write_units MAINTAIN - the boot unit and the weekly refresh
  local maintain="$1"
  noting_new "$COUNTRIES_UNIT"
  as_root tee "$COUNTRIES_UNIT" >/dev/null <<EOF
# FamilyDB's country filter (maintain.sh countries): puts it back in place at every boot.
[Unit]
Description=FamilyDB: only let in connections from ${COUNTRIES_DIR}/countries
Wants=network-pre.target
Before=network-pre.target
ConditionPathExists=${COUNTRIES_DIR}/rules.nft

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=$(command -v nft) -f ${COUNTRIES_DIR}/rules.nft
ExecStop=-$(command -v nft) delete table inet ${COUNTRIES_TABLE}

[Install]
WantedBy=multi-user.target
EOF
  noting_new "$COUNTRIES_REFRESH"
  as_root tee "$COUNTRIES_REFRESH" >/dev/null <<EOF
# FamilyDB's country filter: fetches the address lists again. A failed fetch keeps the last ones.
[Unit]
Description=FamilyDB: keep the country filter's lists fresh, and let a certificate renew
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/bin/bash ${maintain} countries tend --yes
EOF
  noting_new "$COUNTRIES_TIMER"
  as_root tee "$COUNTRIES_TIMER" >/dev/null <<EOF
[Unit]
Description=FamilyDB: look after the country filter each hour

[Timer]
OnCalendar=hourly
RandomizedDelaySec=10m
Persistent=true

[Install]
WantedBy=timers.target
EOF
}
