# -*- coding: utf-8 -*-

import os.path
from enum import Enum, IntEnum
from decorator import decorator
# from lxml import etree
import json
import logging
from .dwg_common import *


class DWGVType(Enum):
    """DWGVType class

        Validation (Vulnerability) types (possible vulnerability points)
    """
    SYNTAX_ERROR    = "Syntax error"
    UNKNOWN_SECTION = "Unknown section"
    UNKNOWN_OBJECT  = "Unknown object"
    UNUSED_AREA     = "Unused area"
    INVALID_CRC     = "Invalid CRC value"
    CORRUPTED       = "Corrupted data"


class DWGVInfo:
    """DWGVInfo class
    """

    def __init__(self, type, offset, length, desc=""):
        """The constructor"""
        self.type = type
        self.offset = offset
        self.length = length
        self.desc = desc
        return

    def __str__(self):
        return "\t{:20} {}".format(self.type.name, self.desc)

    # @property
    # def type(self):
    #     return self._type
    #
    # @property
    # def offset(self):
    #     return self._offset
    #
    # @property
    # def length(self):
    #     return self._length
    #
    # @property
    # def desc(self):
    #     return self._desc
    #
    # @type.setter
    # def type(self, value):
    #     self._type = value
    #
    # @type.setter
    # def offset(self, value):
    #     self._offset = value
    #
    # @type.setter
    # def length(self, value):
    #     self._length = value
    #
    # @type.setter
    # def desc(self, value):
    #     self._desc = value


class DWGReport:
    """DWGReport class

    Attributes:
        vinfo (list): List of DWGVInfoItem
    """

    """
    =======================
    Report format
    =======================
    type:       DWGVType
    offset:     offset (from beginning of file or decompressed stream)
    length:     length
    desc:       detailed description
    """
    _HEADERS = (
        u'type,offset,length,desc\n'
    )

    def __init__(self):
        """The constructor"""
        self.vinfo = []
        self.logger = logging.getLogger(__name__)
        return

    def add(self, item):
        """Add a new validation item

        Args:
            item (DWGVInfoItem)
        """
        # verify 'item'

        self.vinfo.append(item)

    def get_vinfo(self):
        return self.vinfo

    def get_count(self):
        return len(self.vinfo)

    def print_summary(self, file_name, level=0):
        tabs = ""
        if level != 0:
            tabs = "\t" * level

        if file_name != "":
            print("{}[ Format validation of '{}' ]".format(tabs, file_name))

        msg = ''
        if self.get_count() == 0:
            msg = "*SUCCESS* - This file has the normal structure."
        else:
            msg = "*FAIL* - There are {} abnormal points.".format(self.get_count())

        print("  {}{}".format(tabs, msg))

    def write_report(self, out_path, format_csv=True, format_json=False):
        """Write validation results to a file

        Args:
            out_path (str): The full path of an output file
            format_csv  (bool)
            format_json (bool)
        """
        # CSV
        # output = u"{0:s}\n".format(u",".join(value.replace(u',', u' ') for value in events))
        # print(output)
        # self.write_line(output)
        # self.event_count += 1

        # JSON
        return

    def write_line(self, line):
        f = open(self.file_path, "a")
        f.write(line)
        f.close()
        return
