#!/bin/bash
# Watch the VENI suite. If a server test makes no progress for 8 min, pause the runner (never kill the NPU
# process), sysrq-reset the board and let the queue continue. Exits when the queue finishes or the runner is
# disabled, or after 3 wedges.
S="ssh -o ConnectTimeout=8 -o BatchMode=yes -o ServerAliveInterval=5 -o ServerAliveCountMax=2 -i ${VENI_KEY:-$HOME/.ssh/id_ed25519} -o IdentitiesOnly=yes arduino@${VENI_HOST:?set VENI_HOST}"
PW=${VENI_SUDO_PW:?set VENI_SUDO_PW}
last=""; still=0; resets=0
while true; do
  sleep 30
  o=$($S 'cd ~/llm-bench/suite; tail -1 driver.log; systemctl is-enabled veni-bench; f=$(ls -t logs/*.transcript.jsonl 2>/dev/null | head -1); echo "$f $(stat -c %s "$f" 2>/dev/null) $(stat -c %s driver.log)"' 2>/dev/null) || continue
  tl=$(echo "$o" | sed -n 1p); en=$(echo "$o" | sed -n 2p); sig=$(echo "$o" | sed -n 3p)
  echo "$tl" | grep -q "queue finished" && { echo "DONE: $tl"; break; }
  [ "$en" != "enabled" ] && { echo "RUNNER DISABLED: $tl"; break; }
  if [ "$sig" = "$last" ]; then still=$((still+1)); else still=0; last=$sig; fi
  if [ $still -ge 16 ] && ! echo "$tl" | grep -q "finished"; then
    resets=$((resets+1)); echo "$(date +%T) WEDGED #$resets: $tl"
    if [ $resets -gt 3 ]; then
      echo "too many wedges, disabling runner"
      $S "echo $PW | sudo -S -p '' systemctl disable veni-bench"
      break
    fi
    # Pause only the runner's main process, by its systemd PID (pgrep -f would also match this shell)
    timeout 30 $S "P=\$(systemctl show -p MainPID --value veni-bench); echo $PW | sudo -S -p '' sh -c \"kill -STOP \$P; echo '\$(date +%T) wedge watcher: no progress 8 min, sysrq reset' >> /home/arduino/llm-bench/suite/driver.log; sync\"" 2>/dev/null
    timeout 30 $S "echo $PW | sudo -S -p '' sh -c 'echo s > /proc/sysrq-trigger; sleep 2; echo u > /proc/sysrq-trigger; sleep 1; echo b > /proc/sysrq-trigger'" 2>/dev/null
    sleep 40
    until $S true 2>/dev/null; do sleep 10; done
    up=$($S 'cut -d. -f1 /proc/uptime' 2>/dev/null)
    echo "$(date +%T) board back, uptime ${up}s"
    [ "${up:-9999}" -gt 300 ] && { echo "reset did not happen, stopping watcher"; break; }
    still=0; last=""
  fi
done
$S 'grep -E " end |wedge|finished" ~/llm-bench/suite/driver.log | tail -30'
