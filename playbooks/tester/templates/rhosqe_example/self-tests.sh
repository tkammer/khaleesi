#!/bin/bash

cd "$(dirname "$0")"
export PATH="$(pwd)/..:$PATH"

if ! which run_rhosqe_tests.sh > /dev/null; then
    echo "Runner not found in the path ...."
    exit 1
fi

tmplog="$(mktemp)"
tmpxml="$(mktemp)"
diff="$(which colordiff diff|head -n1)"
trap "rm -f $tmplog $tmpxml" EXIT


run_set() {
    echo "... running tests in $1"
    run_rhosqe_tests.sh $1 $tmpxml 2>&1 | tee $tmplog
    echo -e "\n\n\n"
    if ! $diff $1/expected.xml $tmpxml; then
        echo ""
        echo "... the XML output does not match the expected one!"
        echo "... (diff expected actually-got)"
        exit 2
    fi
}
assert_out() {
    if ! grep -q "$1" $tmplog; then
        echo "... runner failed here!"
        echo "... expected but not found: $1"
        exit 2
    fi
}

run_set ./all-ok
assert_out "Total/Errors/Failures/Skips: 3/0/1/1"

run_set ./error
assert_out "TotalyBroken.sh: ERROR with code 70"
assert_out "Total/Errors/Failures/Skips: 1/1/0/0"

run_set ./timeout
assert_out "ConfigAndTimeout.sh: TIMEOUT with code 124 in 1s"
assert_out "Total/Errors/Failures/Skips: 1/1/0/0"

echo ""
echo "... all passed :)"
