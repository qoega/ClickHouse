#!/bin/bash
set -exu
trap "exit" INT TERM

echo "ENV"
env
# fail on errors, verbose and export all env variables
set -e -x -a

echo "Current directory"
pwd
echo "Files in current directory"
ls -la ./
echo "Files in root directory"
ls -la /
echo "Files in /clickhouse-tests directory"
ls -la /clickhouse-tests
echo "Files in /clickhouse-tests/sqllogic directory"
ls -la /clickhouse-tests/sqllogic
echo "Files in /package_folder directory"
ls -la /package_folder

dpkg -i package_folder/clickhouse-common-static_*.deb
dpkg -i package_folder/clickhouse-common-static-dbg_*.deb
dpkg -i package_folder/clickhouse-server_*.deb
dpkg -i package_folder/clickhouse-client_*.deb

# install test configs
# /clickhouse-tests/config/install.sh

sudo clickhouse start

sleep 5
for _ in $(seq 1 60); do if [[ $(wget --timeout=1 -q 'localhost:8123' -O-) == 'Ok.' ]]; then break ; else sleep 1; fi ; done

function run_tests()
{
    set -x

    set +e
    /clickhouse-tests/sqllogic/runner.py --help 2>&1 \
        | ts '%Y-%m-%d %H:%M:%S' \
        | tee -a test_output/test_result.txt
    set -e
}

function self_check()
{
    set -x

    mkdir -p /test_output/self-test-result/sqlite-out
    mkdir -p /test_output/self-test-result/clickhouse-out

    set +e
    /clickhouse-tests/sqllogic/runner.py \
      --log-file /test_output/self-test-result/debug_log \
      manual \
      --engine odbc \
      --test-input-dir /clickhouse-tests/sqllogic/self-test  \
      --test-output-dir /test_output/self-test-result/sqlite-out \
      --out-report /test_output/self-test-result/sqlite-out/report \
      > /test_output/self-test-result/stdout.log 2> /test_output/self-test-result/stderr.log

    /clickhouse-tests/sqllogic/runner.py \
      --log-file /test_output/self-test-result/debug_log \
      manual \
      --engine odbc \
      --test-input-dir /test_output/self-test-result/sqlite-out  \
      --test-output-dir /test_output/self-test-result/clickhouse-out \
      --out-report /test_output/self-test-result/clickhouse-out/report \
      >> /test_output/self-test-result/stdout.log 2>> /test_output/self-test-result/stderr.log
    set -e
}

export -f self_check

timeout "${MAX_RUN_TIME:-900}" bash -c self_check ||:

export -f run_tests

timeout "${MAX_RUN_TIME:-900}" bash -c run_tests ||:


#/process_functional_tests_result.py || echo -e "failure\tCannot parse results" > /test_output/check_status.tsv

clickhouse-client -q "system flush logs" ||:

# Stop server so we can safely read data with clickhouse-local.
# Why do we read data with clickhouse-local?
# Because it's the simplest way to read it when server has crashed.
sudo clickhouse stop ||:

for _ in $(seq 1 60); do if [[ $(wget --timeout=1 -q 'localhost:8123' -O-) == 'Ok.' ]]; then sleep 1 ; else break; fi ; done

grep -Fa "Fatal" /var/log/clickhouse-server/clickhouse-server.log ||:
pigz < /var/log/clickhouse-server/clickhouse-server.log > /test_output/clickhouse-server.log.gz &

# Compressed (FIXME: remove once only github actions will be left)
rm /var/log/clickhouse-server/clickhouse-server.log
mv /var/log/clickhouse-server/stderr.log /test_output/ ||:
