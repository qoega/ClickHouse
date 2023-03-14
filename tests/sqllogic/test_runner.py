#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import os
import traceback
import io
import json
import csv

import test_parser
from exceptions import Error, ProgramError, ErrorWithParent, DataResultDiffer
from connection import execute_request


logger = logging.getLogger("parser")
logger.setLevel(logging.DEBUG)


def _list_files(path):
    logger.debug("list files in %s, type %s", path, type(path))

    if not isinstance(path, str):
        raise ProgramError("NotImplemented")

    if os.path.isfile(path):
        yield path
    else:
        with os.scandir(path) as it:
            for entry in it:
                yield from _list_files(entry.path)


def _filter_files(suffix, files):
    yield from (path for path in files if path.endswith(suffix))


class SchemeResultDiffer(Error):
    pass


class StatementExecutionError(ErrorWithParent):
    pass


class QueryExecutionError(ErrorWithParent):
    pass


class StatementSuccess(ErrorWithParent):
    def __init__(self, *args, **kwargs):
        super().__init__(message="Statement success", *args, **kwargs)


class QuerySuccess(ErrorWithParent):
    def __init__(self, *args, **kwargs):
        super().__init__(message="Query success", *args, **kwargs)


class SimpleStats:
    def __init__(self, general=None):
        self._general = general
        self._success = 0
        self._fail = 0

    @property
    def success(self):
        return self._success

    @success.setter
    def success(self, value):
        if self._general is not None:
            self._general.success += value - self._success
        self._success = value

    @property
    def fail(self):
        return self._fail

    @fail.setter
    def fail(self, value):
        if self._general is not None:
            self._general.fail += value - self._fail
        self._fail = value

    def __repr__(self):
        return str(self.get_map())

    def get_map(self):
        result = dict()
        result["success"] = self.success
        result["fail"] = self.fail
        return result


class Stats:
    def __init__(self):
        self.total = SimpleStats()
        self.statements = SimpleStats(self.total)
        self.queries = SimpleStats(self.total)

    def __repr__(self):
        return str(self.get_map())

    def get_map(self):
        result = dict()
        result["statements"] = self.statements.get_map()
        result["queries"] = self.queries.get_map()
        result["total"] = self.total.get_map()
        return result


class OneReport:
    def __init__(self, test_name):
        self.test_name = test_name
        self.stats = Stats()
        self.cases = dict()

    def statement_fail(self, status):
        self.stats.statements.fail += 1
        self.cases[status.file_and_pos.pos] = status

    def statement_success(self, status):
        self.stats.statements.success += 1
        self.cases[status.file_and_pos.pos] = status

    def query_fail(self, status):
        self.stats.queries.fail += 1
        self.cases[status.file_and_pos.pos] = status

    def query_success(self, status):
        self.stats.queries.success += 1
        self.cases[status.file_and_pos.pos] = status

    def __repr__(self):
        return str(self.get_map())

    def get_map(self):
        result = dict()
        result["test_name"] = self.test_name
        result["stats"] = self.stats.get_map()
        result["requests"] = dict()
        requests = result["requests"]
        for pos, status in self.cases.items():
            name = f"{self.test_name}_{pos}"
            requests[name] = {"status": status.reason, "request": status.request}
        return result

    def get_requests_map(self):
        result = dict()
        for pos, status in self.cases.items():
            name = f"{self.test_name}_{pos}"
            result[name] = status.reason
        return result

class Report:
    def __init__(self, dbms_name):
        self.dbms_name = dbms_name
        self.stats = Stats()
        self.cases = dict()

    def __get_file_report(self, status):
        file = status.file_and_pos.file
        if file not in self.cases:
            self.cases[file] = OneReport(file)
        return self.cases[file]

    def statement_fail(self, status):
        self.stats.statements.fail += 1
        self.__get_file_report(status).statement_fail(status)

    def statement_success(self, status):
        self.stats.statements.success += 1
        self.__get_file_report(status).statement_success(status)

    def query_fail(self, status):
        self.stats.queries.fail += 1
        self.__get_file_report(status).query_fail(status)

    def query_success(self, status):
        self.stats.queries.success += 1
        self.__get_file_report(status).query_success(status)

    def __repr__(self):
        return str(self.get_map())

    def get_map(self):
        result = dict()
        result["dbms_name"] = self.dbms_name
        result["stats"] = self.stats.get_map()
        result["files"] = []
        requests = result["files"]
        for file, report in self.cases.items():
            requests.append({file: report.get_map()})
        return result

    def get_requests_map(self):
        result = dict()
        for file, report in self.cases.items():
            result.update([{f"{self.dbms_name}_{file}_{pos}", status}  for (pos, status) in report.get_requests_map().items()])
        return result

class TestRunner:
    def __init__(self, dbms_name, connection):
        self.dbms_name = dbms_name
        self.connection = connection
        self.report = Report(dbms_name)
        self.results = dict()
        self.verify = False

    def with_verify_mode(self):
        self.verify = True
        return self

    def with_completion_mode(self):
        self.verify = False
        return self

    def __statuses(self, test_file, out_stream):
        for block in test_file.test_blocks():
            file_pos = block.get_file_and_pos()

            if block.get_block_type() == test_parser.BlockType.comments:
                logging.warning("File %s skip comment block", file_pos)
                block.dump_to(out_stream)
                continue

            if block.get_block_type() == test_parser.BlockType.control:
                logging.warning("File %s skip control block", file_pos)
                block.dump_to(out_stream)
                continue

            logging.info("File %s  request <%s>", file_pos, block.get_request())

            cond_lines = block.get_conditions()
            if not test_parser.check_conditions(cond_lines, self.dbms_name):
                logging.info("conditionally skip block for %s", self.dbms_name)
                block.dump_to(out_stream)
                continue

            request = block.get_request()
            exec_res = execute_request(request, self.connection)

            try:
                if block.get_block_type() == test_parser.BlockType.statement:
                    logging.debug("this is statement")
                    if block.expected_error():
                        logging.debug("error is expected")
                        if not exec_res.has_exception():
                            raise StatementExecutionError("statement request did not fail as expected")
                    else:
                        logging.debug("ok is expected")
                        if exec_res.has_exception():
                            raise StatementExecutionError(
                                "statement failed with exception",
                                parent=exec_res.get_exception(),
                                parent_tb=exec_res.get_exception_tb())
                    logging.debug("statement is ok")
                    block.dump_to(out_stream)
                    raise StatementSuccess()
            except StatementSuccess as ok:
                logging.debug("statement is ok")
                ok.set_details(file_and_pos=file_pos, request=request)
                block.dump_to(out_stream)
                yield ok
            except StatementExecutionError as err:
                err.set_details(file_and_pos=file_pos, request=request)
                logging.critical("Unable to execute statement, %s", e.with_details())
                block.dump_to(out_stream)
                yield err

            try:
                if block.get_block_type() == test_parser.BlockType.query:
                    logging.debug("this is query")
                    expected_error = block.expected_error()
                    if expected_error:
                        logging.debug("error is expected %s", expected_error)
                        if exec_res.has_exception():
                            e = exec_res.get_exception()
                            logging.debug("had error %s", e)
                            message = str(e).lower()
                            if expected_error not in message:
                                raise QueryExecutionError(
                                    "query is expected to fail with different error",
                                    details="expected error: {}".format(expected_error),
                                    parent=exec_res.get_exception(),
                                    parent_tb=exec_res.get_exception_tb())
                            else:
                                logging.debug("errors matched")
                                raise QuerySuccess()
                        else:
                            logging.debug("missed error")
                            raise QueryExecutionError(
                                "query is expected to fail with error",
                                details="expected error: {}".format(expected_error))
                    else:
                        logging.debug("success is expected")
                        if exec_res.has_exception():
                            logging.debug("had error")
                            if self.verify:
                                logging.debug("verify mode")
                                canonic = test_parser.QueryResult.parse_it(block.get_result(), 10)
                                exception = QueryExecutionError(
                                    "query execution failed with an exception",
                                    details=str(exec_res.get_exception()),
                                    parent=exec_res.get_exception(),
                                    parent_tb=exec_res.get_exception_tb())
                                actual = test_parser.QueryResult.as_exception(exception)
                                test_parser.QueryResult.assert_eq(canonic, actual)
                                block.with_result(actual)
                                raise QuerySuccess()
                            else:
                                logging.debug("completion mode")
                                raise QueryExecutionError(
                                    "query execution failed with an exception",
                                    details=str(exec_res.get_exception()),
                                    parent=exec_res.get_exception(),
                                    parent_tb=exec_res.get_exception_tb())

                    canonic_types = block.get_types()
                    logging.debug("canonic types %s", canonic_types)

                    if len(exec_res.get_result()) > 0:
                        actual_columns_count = len(exec_res.get_result()[0])
                        canonic_columns_count = len(canonic_types)
                        if canonic_columns_count != actual_columns_count:
                            raise SchemeResultDiffer(
                                "canonic and actual columns count differ",
                                details="expected columns {}, actual columns {}".format(
                                    canonic_columns_count, actual_columns_count)
                            )

                    actual = test_parser.QueryResult.make_it(
                        exec_res.get_result(), canonic_types, block.get_sort_mode(), 10)

                    if self.verify:
                        logging.debug("verify mode")
                        canonic = test_parser.QueryResult.parse_it(block.get_result(), 10)
                        test_parser.QueryResult.assert_eq(canonic, actual)

                    block.with_result(actual)
                    raise QuerySuccess()

            except QuerySuccess as ok:
                ok.set_details(file_and_pos=file_pos, request=request)
                logging.debug("query ok")

                block.dump_to(out_stream)
                yield ok
            except Error as err:
                err.set_details(file_and_pos=file_pos, request=request)
                logging.warning("Query has failed with exception: %s, tb %s",
                                err.with_details(),
                                "".join(traceback.format_exc()))
                block.with_result(test_parser.QueryResult.as_exception(err))
                block.dump_to(out_stream)
                yield err

    def run_one_test(self, stream, test_name):
        out_stream = io.StringIO()
        self.results[test_name] = out_stream

        test_file = test_parser.TestFile(stream, test_name)

        for status in self.__statuses(test_file, out_stream):
            if isinstance(status, StatementSuccess):
                self.report.statement_success(status)
            elif isinstance(status, StatementExecutionError):
                self.report.statement_fail(status)
            elif isinstance(status, QueryExecutionError):
                self.report.query_fail(status)
                pass
            elif isinstance(status, QuerySuccess):
                self.report.query_success(status)
                pass
            elif isinstance(status, SchemeResultDiffer):
                self.report.query_fail(status)
                pass
            elif isinstance(status, DataResultDiffer):
                self.report.query_fail(status)
                pass
            elif isinstance(status, Error):
                raise status
            else:
                raise Error("something unexpected")

    def run_all_tests_from_dir(self, dir_path):
        for file_path in _filter_files(".test", _list_files(dir_path)):
            _, test_name = os.path.split(file_path)
            logging.debug("open file %s", test_name)
            with open(file_path, "r") as stream:
                self.run_one_test(stream, test_name)

    def write_results_to_dir(self, dir_path):
        if not os.path.isdir(dir_path):
            raise NotADirectoryError(dir_path)
        for test_name, stream in self.results.items():
            test_file = os.path.join(dir_path, test_name)
            logging.debug(f"create file {test_file} test name {test_name} results {','.join(self.results.keys())}")
            with open(test_file, "w") as output:
                output.write(stream.getvalue())

    def write_report(self, report_path):
        with open(report_path, "w") as stream:
            stream.write(
                json.dumps(self.report.get_map(), indent=4)
            )

    def write_tsv_report(self, report_path):
        with open(report_path, "w") as stream:
            writer = csv.writer(stream, delimiter='\t', lineterminator='\n')
            for key, val in self.report.get_requests_map().items():
                writer.writerow([key, val])

    def run_all_tests_from_streams(self, tests):
        for test_name, stream in tests.items():
            logging.debug("open test %s", test_name)
            if hasattr(stream, 'seek'):
                stream.seek(0)
            self.run_one_test(stream, test_name)


