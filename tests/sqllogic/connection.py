#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import pyodbc
import sqlite3
import traceback
import enum

from exceptions import ProgramError


logger = logging.getLogger("connection")
logger.setLevel(logging.DEBUG)


class Engines(enum.Enum):
    SQLITE = enum.auto()
    ODBC = enum.auto()

    @staticmethod
    def list():
        return list(map(lambda c: c.name.lower(), Engines))


class ConnectionWrap(object):
    def __init__(self, connection):
        self._connection = connection
        self.DBMS_NAME = None

    def __getattr__(self, item):
        return getattr(self._connection, item)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        if hasattr(self._connection, "close"):
            return self._connection.close()


def __default_odbc_clickhouse_conn_str():
    conn_attrs = {
        "DSN": "ClickHouse DSN (ANSI)",
        "Server": "localhost",
        "User": "default",
        "Database": "default",
    }
    conn_str = ";".join(["{}={}".format(x, y) for x, y in conn_attrs.items()])
    return conn_str


def setup_connection(engine, conn_str=None, make_debug_request=True):
    connection = None

    if isinstance(engine, str):
        engine = Engines[engine.upper()]

    if engine == Engines.ODBC:
        conn_str = conn_str if conn_str is not None else __default_odbc_clickhouse_conn_str()

        logger.info("Drivers: %s", pyodbc.drivers())
        logger.info("DataSources: %s", pyodbc.dataSources())
        logger.info("Connection string: %s", conn_str)

        connection = ConnectionWrap(pyodbc.connect(conn_str))
        connection.add_output_converter(pyodbc.SQL_UNKNOWN_TYPE, lambda x: None)

        setattr(connection, "DBMS_NAME", connection.getinfo(pyodbc.SQL_DBMS_NAME))
        connection.DBMS_NAME = connection.getinfo(pyodbc.SQL_DBMS_NAME)
        connection.DATABASE_NAME = connection.getinfo(pyodbc.SQL_DATABASE_NAME)
        connection.USER_NAME = connection.getinfo(pyodbc.SQL_USER_NAME)
    elif engine == Engines.SQLITE:
        conn_str = conn_str if conn_str is not None else ":memory:"
        connection = ConnectionWrap(sqlite3.connect(conn_str))
        setattr(connection, "DBMS_NAME", "sqlite")
        connection.DBMS_NAME = "sqlite"
        connection.DATABASE_NAME = "default"
        connection.USER_NAME = "default"

    logger.info("Connection info: DBMS name %s, database %s, user %s",
                connection.DBMS_NAME,
                connection.DATABASE_NAME,
                connection.USER_NAME)

    if make_debug_request:
        request = "SELECT 1"
        logger.debug("Make debug request to the connection: %s", request)
        result = execute_request(request, connection)
        logger.debug("Debug request returned: %s", result.get_result())

    logger.debug("Connection is ok")
    return connection


class ExecResult:
    def __init__(self):
        self._exception = None
        self._tb = None
        self._result = None
        self._description = None

    def as_exception(self, exc, tb=None):
        self._exception = exc
        self._tb = tb
        return self

    def get_result(self):
        self._assert_no_exception()
        return self._result

    def get_description(self):
        self._assert_no_exception()
        return self._description

    def as_ok(self, rows=None, description=None):
        if rows is None:
            self._result = True
            return self
        self._result = rows
        self._description = description
        return self

    def get_exception(self):
        return self._exception

    def get_exception_tb(self):
        return self._tb

    def has_exception(self):
        return self._exception is not None

    def _assert_no_exception(self):
        if self.has_exception():
            raise ProgramError(f"request doesn't have a result set, it has the exception",
                               parent=self._exception,
                               parent_tb=self._tb)


def execute_request(request, connection):
    cursor = connection.cursor()
    try:
        cursor.execute(request)
        if cursor.description:
            logging.debug("request has a description %s", cursor.description)
            rows = cursor.fetchall()
            connection.commit()
            return ExecResult().as_ok(rows=rows, description=cursor.description)
        else:
            logging.debug("request doesn't have a description")
            connection.commit()
            return ExecResult().as_ok()
    except (pyodbc.Error, sqlite3.DatabaseError) as e:
        return ExecResult().as_exception(e, traceback.format_exc())
    finally:
        cursor.close()
