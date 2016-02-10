# -*- coding: utf-8 -*-

"""@package pydwg

    * Description
        DWGParser - .DWG (by AutoCAD) file parser
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

import os.path
from decorator import decorator
import ntpath
import logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)-22s %(name)-25s %(levelname)-8s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

from .dwg_common import *
from .dwg_format_base import DWGFormatBase
from .dwg_format_r18 import DWGFormatR18
from .dwg_format_r21 import DWGFormatR21


@decorator
def check_status(func, *args, **kwargs):
    """Decorator for checking the current status
    """
    if args[0].file_size == 0 or args[0].file_buf is None:
        args[0].logger.debug("{}(): File loading failed.".format(GET_MY_NAME()))
        return False
    return func(*args, **kwargs)


class DWGParser:
    """DWGParser class
    """

    def __init__(self, path, mode=DWGParsingMode.FULL):
        """The constructor"""
        self.file_path = path
        self.file_name = ntpath.basename(path)

        self.file_buf = None
        self.file_size = 0
        self.dwg_version = DWGVersion.UNSUPPORTED
        self.fm = DWGFormatBase()
        self.parsing_mode = mode

        self.logger = logging.getLogger(__name__)

        # open and read a dwg file
        self.file_size = os.path.getsize(path)
        f = open(path, 'rb')
        self.file_buf = f.read()
        f.close()
        return

    @check_status
    def parse(self):
        """Parse a DWG file

        Returns:
            True or False
        """
        self.logger.info("{}(): Start parsing a file {}".format(GET_MY_NAME(), self.file_name))

        # get DWG version signature
        self.check_signature()

        if not (DWGVersion.R18 <= self.dwg_version <= DWGVersion.R21):
            self.logger.info("{}(): The current version supports R18 and R21 only.".format(GET_MY_NAME()))
            return False

        # create a format module
        self.fm = self.create_format_module(self.dwg_version.name)

        # parse a specific format version
        if self.fm.parse() is False and \
           self.parsing_mode != DWGParsingMode.VALIDATION:
            return False
        return True

    def close(self):
        """Close this parser

        """
        self.fm.close()
        return

    def get_result(self):
        return self.fm

    def get_version(self):
        return self.dwg_version

    def check_signature(self):
        """Check DWG signature to get the version info.
        """
        signature = self.file_buf[0:6].decode("utf-8")

        if signature == 'AC1012':
            self.dwg_version = DWGVersion.R13
        elif signature == 'AC1014':
            self.dwg_version = DWGVersion.R14
        elif signature == 'AC1015':
            self.dwg_version = DWGVersion.R15
        elif signature == 'AC1018':
            self.dwg_version = DWGVersion.R18
        elif signature == 'AC1021':
            self.dwg_version = DWGVersion.R21
        elif signature == 'AC1024':
            self.dwg_version = DWGVersion.R24
        elif signature == 'AC1027':
            self.dwg_version = DWGVersion.R27
        else:
            self.dwg_version = DWGVersion.UNSUPPORTED

        self.logger.info("{}(): DWG version is {}".format(GET_MY_NAME(), self.dwg_version.name))
        return

    def create_format_module(self, version):
        """Create a DWGFormat module relating to the input version

        Args:
            version (DWGVersion): The version of DWG format

        Returns:
            'DWGFormat' module
        """
        module_name = 'DWGFormat' + version
        module = globals()[module_name](self.file_buf, self.file_size, self.file_name, self.parsing_mode)
        self.logger.info("{}(): {}".format(GET_MY_NAME(), module_name))
        return module

