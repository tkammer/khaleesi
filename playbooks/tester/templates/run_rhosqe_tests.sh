#!/bin/bash

# usage:
#  run_rhosqe_tests.sh <dir-with-tests> [fullname-where-to-create-junit-xml]
#
# all *.sh files in dir-with-tests will be executed, each of them as single testcase
#
# if not specified other path, this script creates ./nosetests.xml jUnit xml file
# describing the passed/failed testcases (eg. to be processed by jenkins)
#
# EXIT_SKIP and EXIT_DIRTY env variables are provided, their value should be used
# as exit code when testcase:
# - decides it should not run [SKIP]
# - it reaches state it cannot handle/clean after itself (failure in teardown ...) [DIRTY]
#

if [[ -z "$1" || ! -d "$1" ]]; then
    echo "You have to specify path to directory with testcases to run, as first argument." >&2
    exit 1
fi

TESTS_DIR="$1"
export EXIT_SKIP=75  # code used by tests to announce their skipping
                      # value comes from EX_TEMPFAIL from /usr/include/sysexits.h
export EXIT_DIRTY=70  # code used by tests to announce they failed in cleanup/... part and the env may be dirty
                       # same as if they will time-out
                       # EX_SOFTWARE being used here
DEFAULT_TIMEOUT=5m  # can be overriden per testcase with '# testconfig: timeout=12m'
EXIT_TIMEDOUT=124  # ecode of timeout command
EXIT_TIMEDKILL=$(( 128 + 9 ))  # ecode of timeout command

JUNIT_FINAL="${2:-$(pwd)/nosetests.xml}"
JUNIT="$(mktemp)"
touch "$JUNIT"
trap "rm -f $JUNIT" EXIT
echo "Going to generate $JUNIT_FINAL (with temp file at $JUNIT)"

START="$(date "+%s")"
TOTAL=0
SKIPPED=0
FAILURES=0
ERRORS=0


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
header() {
  echo "====== $TEST: $1 ======"
}
finish() {
    cat > $JUNIT_FINAL <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<testsuite tests="${TOTAL}" errors="${ERRORS}" failures="${FAILURES}" skip="${SKIPPED}">
EOF
    [[ -f "$JUNIT" ]] && cat $JUNIT >> $JUNIT_FINAL
    cat >> $JUNIT_FINAL <<EOF
</testsuite>
EOF

    TEST="RUNNER"
    header "Finished"
    header "Total/Errors/Failures/Skips: $TOTAL/$ERRORS/$FAILURES/$SKIPPED"
    header "in $(( $(date "+%s") - $START )) seconds"

    ls -l "$(dirname "$JUNIT_FINAL")"
    echo $JUNIT_FINAL
    cat $JUNIT_FINAL
    # we always want to exit with 0 in case test-runner worked properly
    # so the non zero means broken runner
    exit 0
}
junit_test() {
    cat >> $JUNIT <<EOF
    <testcase classname="$TEST_CLASS" name="$TEST_NAME" time="$TEST_TIME">$1</testcase>
EOF
}
test_passed() {
    junit_test ""

    header "PASSED in ${TEST_TIME}s"
}
test_skipped() {
    junit_test "<skipped />"

    SKIPPED=$(( $SKIPPED + 1 ))
    header "SKIPPED"
}
test_failed() {
    junit_test "<failure type=\"exitCode\" message=\"$STATUS\"></failure>"

    FAILURES=$(( $FAILURES + 1 ))
    header "FAILED with code $STATUS in ${TEST_TIME}s"
}
test_erred() {
    junit_test "<error type=\"exitCode\" message=\"$STATUS\"></error>"

    ERRORS=$(( $ERRORS + 1 ))
    header "ERROR with code $STATUS in ${TEST_TIME}s"

    finish
}
test_timed_out() {
    junit_test "<error type=\"timeOut\" message=\"$STATUS\"></error>"

    ERRORS=$(( $ERRORS + 1 ))
    header "TIMEOUT with code $STATUS in ${TEST_TIME}s"

    finish
}





cd "$TESTS_DIR"
while read TEST; do
  [[ "$TEST" =~ *SetupTeardown.sh || "$TEST" =~ sanity-net* ]] && continue

  TEST_NAME="$(basename "$TEST")"
  TEST_CLASS="rhosqe.ceilometer.${TEST%.*}"
  #TEST_CLASS="$(basename "$(dirname "$TEST")")"  # TODO: in case we change the structure to <component-subfolder>/<testX.sh>

  TOTAL=$(( $TOTAL + 1 ))
  TEST_TIMEOUT=$(config $TEST timeout $DEFAULT_TIMEOUT)

  header "Running"
  TEST_TIME_START="$(date "+%s")"
  chmod +x "$TEST"
  (timeout $TEST_TIMEOUT "$TEST") 2>&1
  STATUS=$?
  TEST_TIME="$(( $(date "+%s") - $TEST_TIME_START ))"

  if [[ "$STATUS" = "$EXIT_SKIP" ]]; then
    test_skipped
  elif [[ "$STATUS" != "0" ]]; then
    if [[ "$STATUS" = "${EXIT_TIMEDOUT}" || "$STATUS" = "$EXIT_TIMEDKILL" ]]; then
        test_timed_out
    elif [[ "$STATUS" = "${EXIT_DIRTY}" ]]; then
        test_erred
    fi
    test_failed
  else
    test_passed
  fi
done < <(ls -1 ./*.sh)

finish
