#!/usr/bin/env python3
# -*- coding: utf-8 -*-

class Error(Exception):
    def __init__(self, message, file_and_pos=None, request=None, details=None, *args, **kwargs):
        super().__init__(message, *args, **kwargs)
        self._file_and_pos = file_and_pos
        self._request = request
        self._details = details

    @property
    def file_and_pos(self):
        return self._file_and_pos

    @property
    def request(self):
        return self._request

    @property
    def reason(self):
        return ", ".join((str(x) for x in [
            super().__str__(),
            "details: {}".format(self._details) if self._details else ""
            ] if x))

    def set_details(self, file_and_pos=None, request=None, details=None):
        if file_and_pos is not None:
            self._file_and_pos = file_and_pos
        if request is not None:
            self._request = request
        if details is not None:
            self._details = details

    def with_details(self):
        return ", ".join((str(x) for x in [
            super().__str__(),
            "details: {}".format(self._details) if self._details else "",
            "request: <{}>".format(self._request) if self._request else "",
            "at: [{}]".format(self._file_and_pos) if self._file_and_pos else "",
        ] if x))


class ErrorWithParent(Error):
    def __init__(self, message, parent=None, parent_tb=None, *args, **kwargs):
        super().__init__(message, *args, **kwargs)
        self._parent = parent
        self._parent_tb = parent_tb

    def get_parent(self):
        return self._parent

    def with_details(self):
        result = super().with_details()
        if self._parent:
            result += "\nOriginal exception:\n" + str(self._parent)
            if self._parent_tb:
                result += "\nParent exception traceback:\n" + "".join(self._parent_tb)
        return result


class ProgramError(ErrorWithParent):
    pass


class DataResultDiffer(Error):
    pass
