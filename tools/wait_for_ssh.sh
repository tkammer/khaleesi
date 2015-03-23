#!/bin/bash

if [[ -z "$#" || "$1" = "-h" || "$1" = "--help" ]]; then
  cat <<EOF
usage:
  wait_for_ssh.sh [-v] <ip> [<any-other-ssh-opts>, <like-user-etc>, ...]

optionaly override TIMEOUT/DELAY with env variables
EOF
fi

debug() { :; }
if [[ "$1" = "-v" || "$1" = "-vv" ]]; then
  [[ "$1" = "-vv" ]] && set -x
  shift
  debug() {
    [[ "$#" -gt "0" ]] && echo "$@"
    read -t 0 && cat;
  }
fi

TIMEOUT=${TIMEOUT:-300}       # how many seconds before this script fails if it couldn't already reach the machine before
DELAY=${DELAY:-0.3}           # how long to wait between retrying ssh (low is better, though it means more traffic)
CONNTIMEOUT=${CONNTIMEOUT:-2} # (soft) timeout for ssh connection
CONNKILL=${CONNKILL:-5}       # hard timeout for ssh connection
OLDUPTIME=${OLDUPTIME:-0}
IP="$1"
shift

E_NOT_REBOOTED=998  # machine has higher uptime then the provided OLDUPTIME, at the end of TIMEOUT period

if ${KHALEESI_SSH_VERBOSE:-false}; then
  SSHDEBUG="${SSHDEBUG:-"-vvvv"}"
fi
SSHDEBUG="${SSHDEBUG:-}"

TIME_START=$(date "+%s")


if [[ "$OLDUPTIME" != "0" ]]; then
    echo "Going to wait for reboot, which means uptime < ${OLDUPTIME}."
fi


ssh="$(which ssh)"
ssh="$ssh $IP $SSHDEBUG"
ssh="$ssh -o ConnectTimeout=$CONNTIMEOUT"
ssh="$ssh -o PreferredAuthentications=publickey";
ssh="$ssh -o StrictHostKeyChecking=no";
ssh="$ssh -o UserKnownHostsFile=/dev/null";
ssh="$ssh $@"

last_rc=999
cnt=0

while true; do
  cnt=$(( $cnt + 1 ))
  TIME_NOW=$(date "+%s")
  TIME_DIFF=$(( $TIME_NOW - $TIME_START ))
  if [[ $TIME_DIFF -ge $TIMEOUT ]]; then
    echo "Timed out after $cnt retries / ${TIME_DIFF}s with exit code $last_rc while trying to reach: $IP"
    exit 1
  else
    debug "Trying to reach $IP. For $cnt times / $TIME_DIFF seconds in total so far."
  fi


  # try ssh connection, while:
  # - be wrapped in killing-timeout (to not hang for any reason)
  # - capture possible uptime output in variable
  # - redirect any stderr content to debug function (whatever if it ignores or prints it out (-v arg used))
  UPTIME=$(timeout -s KILL ${CONNKILL}s $ssh 'cat /proc/uptime | sed "s/\..*//"' 2> >(debug))
  last_rc=$?

  if [[ "$OLDUPTIME" != "0" && $UPTIME -ge $OLDUPTIME ]]; then
    last_rc=$E_NOT_REBOOTED
    debug "$IP did not rebooted yet: uptime $UPTIME > olduptime $OLDUPTIME"
  fi

  if [[ "$last_rc" = "0" ]]; then
    echo "Reached $IP after waiting for $cnt retries / ${TIME_DIFF}s: $UPTIME"
    exit 0
  fi
  sleep $DELAY
done

