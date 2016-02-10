# -*- coding: utf-8 -*-

"""@package pydwg

    * Description
        DWGFormatR18 - R18 (AutoCAD 2004) file format handler
    * Author
        Hyunji Chung  (localchung@gmail.com)
        Jungheum Park (junghmi@gmail.com)
    * License
        MIT License
    * Tested Environment
        Python 3.5.1
    * References
        Open Design Alliance, Open Design Specification for .dwg files (v5.3)
"""
from .dwg_common import *
from .dwg_report import *


class DWGFormatBase(object):
    """DWGFormatBase class
    """

    def __init__(self):
        """The constructor"""
        self.mode = DWGParsingMode.FULL

        # File header & System sections (ss)
        self.dwg_file_header_1st = None
        self.dwg_file_header_2nd = None
        self.dwg_page_map = None            # for both system and data sections
        self.dwg_section_map = None         # for just data sections
        self.dwg_section_entry_list = []    # list of section entry

        # Data sections (ds)
        self.dwg_summaryinfo = None         # document properties (dict)
        self.dwg_appinfo = None             # application info. (dict)
        self.dwg_appinfohistory = None      # application info. history (dict)
        self.dwg_filedeplist = None         # file dependencies (dict)
        self.dwg_preview = None             # preview data (dict)
        self.dwg_security = None            # security info. (dict)
        self.dwg_header = None              # header (system) variables (dict)
        self.dwg_classes = None             # defined classes (dict)
        self.dwg_auxheader = None           # additional document properties (dict)

        self.dwg_object_map = None          # list of handle/object location(offset) pairs
        self.dwg_objects = None             # list of decoded objects

        # Report
        self.report = DWGReport()
        return

    def close(self):
        # File header & System sections (ss)
        self.dwg_file_header_1st = None
        self.dwg_file_header_2nd = None
        self.dwg_page_map = None
        self.dwg_section_map = None
        self.dwg_section_entry_list = None

        # Data sections (ds)
        self.dwg_summaryinfo = None
        self.dwg_appinfo = None
        self.dwg_appinfohistory = None
        self.dwg_filedeplist = None
        self.dwg_preview = None
        self.dwg_security = None
        self.dwg_header = None
        self.dwg_classes = None
        self.dwg_auxheader = None

        self.dwg_object_map = None
        self.dwg_objects = None
        return
