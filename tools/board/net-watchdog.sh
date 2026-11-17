#!/bin/sh
# Keeps the board reachable when its Wi-Fi drops (5 GHz DFS channel changes, ath11k data-path stalls).
# Runs once a minute from net-watchdog.timer. It never reboots: the benchmarks run fine offline, and
# reboots are what hang this board. Each step logs to the journal, which also tells a dead network
# apart from a frozen board after the fact.
#   /etc/default/net-watchdog: FALLBACK_CON=<NetworkManager connection to force, e.g. the 2.4 GHz one>
[ -r /etc/default/net-watchdog ] && . /etc/default/net-watchdog
STATE=/run/net-watchdog.fails
n=$(cat "$STATE" 2>/dev/null || echo 0)
gw=$(ip -4 route show default | awk '{print $3; exit}')
if [ -n "$gw" ] && ping -c 2 -W 3 "$gw" >/dev/null 2>&1; then
    [ "$n" -gt 0 ] && echo "gateway $gw reachable again after $n failed checks"
    echo 0 > "$STATE"
    exit 0
fi
n=$((n + 1)); echo "$n" > "$STATE"
echo "gateway ${gw:-none} unreachable (check $n)"
case $n in
    # A silent ath11k data-path stall (link up, nothing gets through) only clears with a radio toggle
    2|8|20|40) echo "toggling the Wi-Fi radio"; nmcli radio wifi off; sleep 5; nmcli radio wifi on ;;
    4) [ -n "$FALLBACK_CON" ] && { echo "bringing up $FALLBACK_CON"; nmcli connection up "$FALLBACK_CON"; } ;;
    6) echo "restarting NetworkManager"; systemctl restart NetworkManager ;;
esac
exit 0
