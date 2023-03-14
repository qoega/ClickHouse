#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
import sys
import logging
import json

from connection import setup_connection, execute_request, Engines
from test_runner import TestRunner


LEVEL_NAMES = [x.lower() for x in logging._nameToLevel.keys() if x != logging.NOTSET]


def setup_logger(args):
    logging.getLogger().setLevel(logging.NOTSET)
    formatter = logging.Formatter('%(levelname)s:%(name)s:%(filename)s:%(funcName)s:%(lineno)d - %(message)s')

    if args.log_file:
        file_handler = logging.FileHandler(args.log_file)
        file_handler.setLevel(args.log_level.upper())
        file_handler.setFormatter(formatter)
        logging.getLogger().addHandler(file_handler)
    else:
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.INFO)
        stream_handler.setFormatter(formatter)
        logging.getLogger().addHandler(stream_handler)


def clear_tables(connection, do_not_drop_before=False):
    if connection.DBMS_NAME == "ClickHouse" and not do_not_drop_before:
        cursor = connection.cursor()
        to_drop = [name for _, _, name, type, _ in cursor.tables() if type == "TABLE"]
        for name in to_drop:
            request = f"DROP TABLE IF EXISTS {name}"
            logging.debug("Make request to the connection: %s", request)
            result = execute_request(request, connection)
            result.get_result()


def mode_manual(parser):
    parser.add_argument("--engine", choices=Engines.list(), required=True)
    parser.add_argument("--connection")
    parser.add_argument("--verify", action='store_true', default=False)

    parser.add_argument("--do-not-drop-before", action='store_true', default=False)
    parser.add_argument("--do-not-debug-request", action='store_true', default=False)

    package = parser.add_argument_group("package mode")
    package.add_argument("--test-input-dir", metavar='DIR', required=False)
    package.add_argument("--test-output-dir", metavar='DIR', required=False)
    package.add_argument("--out-report", metavar='FILE', required=False)

    def calle(args):
        if args.test_input_dir is not None and args.test_output_dir is None:
            raise argparse.ArgumentTypeError(
                args.test_output_dir,
                "test_output_dir has to be specified")

        if args.test_input_dir is None and args.test_output_dir is None:
            raise argparse.ArgumentTypeError(
                args.test_input_dir,
                "stdin and stdout are used when not test_input_dir, test_output_dir is excess")

        connection = setup_connection(args.engine, args.connection, args.do_not_debug_request)
        clear_tables(connection)
        runner = TestRunner(connection.DBMS_NAME, connection)
        if args.verify:
            runner.with_verify_mode()

        if args.test_input_dir is None:
            logging.debug("read from stdin")
            runner.run_one_test(sys.stdin, "stdin")
            result = runner.results["stdin"]
            result.seek(0)
            print(result)
        else:
            test_input_dir = os.path.realpath(args.test_input_dir)
            test_output_dir = os.path.realpath(args.test_output_dir)
            logging.debug(f"input dir is: {test_input_dir} outdir: {test_output_dir}")
            runner.run_all_tests_from_dir(test_input_dir)
            runner.write_results_to_dir(test_output_dir)

        if args.out_report is not None:
            runner.write_report(args.out_report)

    parser.set_defaults(func=calle)


def mode_check_statements(parser):
    parser.add_argument("--test-input-dir", metavar='DIR', required=True)
    parser.add_argument("--test-output-dir", metavar='DIR', required=True)

    def calle(args):
        test_input_dir = os.path.realpath(args.test_input_dir)
        test_output_dir = os.path.realpath(args.test_output_dir)

        logging.debug("dir is: %s", test_input_dir)

        sqlite = setup_connection(Engines.SQLITE)

        runner_sqlite = TestRunner(sqlite.DBMS_NAME, sqlite)
        runner_sqlite.run_all_tests_from_dir(test_input_dir)
        runner_sqlite.write_results_to_dir(test_output_dir)
        print(json.dumps(runner_sqlite.report.get_map(), indent=4))

        clickhouse = setup_connection(Engines.ODBC)
        clear_tables(clickhouse)

        runner_clickhouse = TestRunner(clickhouse.DBMS_NAME, clickhouse)
        runner_clickhouse.with_verify_mode()
        runner_clickhouse.run_all_tests_from_streams(runner_sqlite.results)
        print(json.dumps(runner_clickhouse.report.get_map(), indent=4))

    parser.set_defaults(func=calle)


def mode_self_test(parser):
    parser.add_argument("--self-test-dir", metavar='DIR', required=True)
    parser.add_argument("--out-dir", metavar='DIR', required=True)

    def calle(args):
        self_test_dir = os.path.realpath(args.self_test_dir)
        logging.debug("self test dir is: %s", self_test_dir)

        out_dir = os.path.realpath(args.out_dir)
        if not os.path.exists(out_dir):
            raise NotADirectoryError(out_dir, "self test: dir not found")
        if not os.path.isdir(out_dir):
            raise NotADirectoryError(out_dir, "self test: not a dir")

        out_dir_sqlite_complete = os.path.join(out_dir, "sqlite-complete")
        os.makedirs(out_dir_sqlite_complete, exist_ok=True)
        with setup_connection(Engines.SQLITE) as sqlite:
            runner = TestRunner(sqlite.DBMS_NAME, sqlite)
            runner.run_all_tests_from_dir(self_test_dir)
            runner.write_results_to_dir(out_dir_sqlite_complete)
            runner.write_report(os.path.join(out_dir_sqlite_complete, "report"))
            runner.write_tsv_report(os.path.join(out_dir_sqlite_complete, "report.tsv"))

        out_dir_sqlite_vs_sqlite = os.path.join(out_dir, "sqlite-vs-sqlite")
        os.makedirs(out_dir_sqlite_vs_sqlite, exist_ok=True)
        with setup_connection(Engines.SQLITE) as sqlite:
            runner = TestRunner(sqlite.DBMS_NAME, sqlite)
            runner.with_verify_mode()
            runner.run_all_tests_from_dir(out_dir_sqlite_complete)
            runner.write_results_to_dir(out_dir_sqlite_vs_sqlite)
            runner.write_report(os.path.join(out_dir_sqlite_vs_sqlite, "report"))
            runner.write_tsv_report(os.path.join(out_dir_sqlite_vs_sqlite, "report.tsv"))

        out_dir_clickhouse_complete = os.path.join(out_dir, "clickhouse-complete")
        os.makedirs(out_dir_clickhouse_complete, exist_ok=True)
        with setup_connection(Engines.ODBC) as clickhouse:
            clear_tables(clickhouse)
            runner = TestRunner(clickhouse.DBMS_NAME, clickhouse)
            runner.run_all_tests_from_dir(self_test_dir)
            runner.write_results_to_dir(out_dir_clickhouse_complete)
            runner.write_report(os.path.join(out_dir_clickhouse_complete, "report"))
            runner.write_tsv_report(os.path.join(out_dir_clickhouse_complete, "report.tsv"))

        out_dir_clickhouse_vs_clickhouse = os.path.join(out_dir, "clickhouse-vs-clickhouse")
        os.makedirs(out_dir_clickhouse_vs_clickhouse, exist_ok=True)
        with setup_connection(Engines.ODBC) as clickhouse:
            clear_tables(clickhouse)
            runner = TestRunner(clickhouse.DBMS_NAME, clickhouse)
            runner.with_verify_mode()
            runner.run_all_tests_from_dir(out_dir_clickhouse_complete)
            runner.write_results_to_dir(out_dir_clickhouse_vs_clickhouse)
            runner.write_report(os.path.join(out_dir_clickhouse_vs_clickhouse, "report"))
            runner.write_tsv_report(os.path.join(out_dir_clickhouse_vs_clickhouse, "report.tsv"))

        out_dir_sqlite_vs_clickhouse = os.path.join(out_dir, "sqlite-vs-clickhouse")
        os.makedirs(out_dir_sqlite_vs_clickhouse, exist_ok=True)
        with setup_connection(Engines.ODBC) as clickhouse:
            clear_tables(clickhouse)
            runner = TestRunner(clickhouse.DBMS_NAME, clickhouse)
            runner.with_verify_mode()
            runner.run_all_tests_from_dir(out_dir_sqlite_complete)
            runner.write_results_to_dir(out_dir_sqlite_vs_clickhouse)
            runner.write_report(os.path.join(out_dir_sqlite_vs_clickhouse, "report"))
            runner.write_tsv_report(os.path.join(out_dir_sqlite_vs_clickhouse, "report.tsv"))

    parser.set_defaults(func=calle)

def parse_args():
    parser = argparse.ArgumentParser(
        description="This script runs sqllogic tests over database."
    )

    parser.add_argument("--log-file", help="write logs to the file", metavar="FILE")
    parser.add_argument("--log-level", help="define the log level for log file",
                        metavar="level",
                        choices=LEVEL_NAMES,
                        default="debug")

    subparsers = parser.add_subparsers(dest="mode")
    mode_manual(
        subparsers.add_parser(
            "manual",
            help="Run test against database. "
                 "Read test from stdin and write result to stdout.")
    )
    mode_check_statements(
        subparsers.add_parser(
            "statements-check",
            help="Run all test. Check that all statements are passed")
    )
    mode_self_test(
        subparsers.add_parser(
            "self-test",
            help="Run all test. Check that all statements are passed")
    )
    args = parser.parse_args()
    if args.mode is None:
        parser.print_help()
    return args


def main():
    args = parse_args()
    setup_logger(args)
    if args.mode is not None:
        args.func(args)


if __name__ == "__main__":
    main()

