#!/bin/bash

TESTS_DIR="{{ tester.dir }}"
export EXIT_SKIP=999  # code used by tests to announce their skipping
export EXIT_DIRTY=998  # code used by tests to announce they failed in cleanup/... part and the env may be dirty
                       # same as if they will time-out
EXIT_TESTFAILED=42  # code used by us to say 'our execution was ok, but some tests failed'
DEFAULT_TIMEOUT=5m  # can be overriden per testcase with '# testconfig: timeout=12m'
EXIT_TIMEDOUT=124  # ecode of timeout command
EXIT_TIMEDKILL=$(( 128 + 9 ))  # ecode of timeout command




header() {
  echo "====== $1 ======"
}
finish() {
    header "FINISHED"
    header "TOTAL/FAILED/SKIPPED: $TOTAL/$FAILED/$SKIPPED"
    header "IN $(( $(date "+%s") - $START )) SECONDS"

    [[ -z "$1" ]] || exit $1
    [[ $FAILED -gt 0 ]] && exit $EXIT_TESTFAILED
    exit 0
}
config() {
    # usage: config <test-file> <key> [default_value=]
    local tfile=$1
    local key=$2
    local default=${3:-}
    local comment="#"
    # grep out testconfig line, with given key, if not find fake it with default value
    (grep -E "^\s*#\s+testconfig:.* ${key}=.*" $tfile || echo " ${key}=\"$default\"") | \
        sed -r "s/.* ${key}=(\"([^\"]*)\"|([^ ]*))($| .*$)/\2\3/"
    # and parse out the value with two possible cases
    # 1) key=value-without-whiespaces
    # 2) key="quoted value"
}

START="$(date "+%s")"
TOTAL=0
SKIPPED=0
FAILED=0

cd "$TESTS_DIR"
while read TEST; do
  [[ "$TEST" =~ *SetupTeardown.sh || "$TEST" =~ sanity-net* ]] && continue

  TOTAL=$(( $TOTAL + 1 ))
  TEST_TIMEOUT=$(config $TEST timeout $DEFAULT_TIMEOUT)

  header "Running $TEST"
  chmod +x "$TEST"
  (time timeout $TEST_TIMEOUT "$TEST") 2>&1
  STATUS=$?

  if [[ "$STATUS" = "$EXIT_SKIP" ]]; then
    SKIPPED=$(( $SKIPPED + 1 ))
    header "$TEST: SKIPPED"
  elif [[ "$STATUS" != "0" ]]; then
    FAILED=$(( $FAILED + 1 ))
    header "$TEST: FAILED with code $STATUS"

    if [[ "$STATUS" = "${EXIT_TIMEDOUT}" || "$STATUS" = "$EXIT_TIMEDKILL" ]]; then
        header "TEST TIMED-OUT"
        finish $STATUS
    elif [[ "$STATUS" = "${EXIT_DIRTY}" ]]; then
        finish $EXIT_DIRTY
    fi
  else
    header "$TEST: PASSED"
  fi
done < <(ls -1 ${TESTS_DIR}/*.sh)

finish
