# -*- coding: utf-8 -*-

"""@package pydwg

    * Description
        DWGUtils - Common utils (including decoding, decompress, checksum...)
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
import ntpath
import math
import datetime
import logging
import ctypes
from collections import OrderedDict
import csv
from .dwg_common import *
from .dwg_bit_codes import *
from .dwg_report import *


class DWGUtils:
    """DWGUtils class

    Attributes:
        version (DWGVersion)
    """
    def __init__(self, report=None):
        """The constructor"""
        self.logger = logging.getLogger(__name__)
        if report is None:
            self.report = report
        else:
            self.report = DWGReport()
        return

    def print_metadata(self, result, output_path=""):
        """Create a name with the current time

        Args:
            result (DWGFormatRXX): paring results
            output_path (str)
        """
        if output_path != "":
            f = open(output_path, 'w')

        '''--------------------------------
        Data sections
        '''

        # AcDb:SummaryInfo
        title= "AcDb:SummaryInfo"
        self.print_dict(result.dwg_summaryinfo, title, level=0)

        title= "AcDb:AuxHeader"
        self.print_dict(result.dwg_auxheader, title, level=0)

        if result.dwg_header is not None:
            title= "AcDb:Header"
            items = OrderedDict()
            items['Created time'] = result.dwg_header.get('TDCREATE')
            items['Modified time'] = result.dwg_header.get('TDUPDATE')
            items['Cumulative editing time'] = result.dwg_header.get('TDINDWG')
            items['User-elapsed timer'] = result.dwg_header.get('TDUSRTIMER')
            self.print_dict(items, title, level=0)

        title= "AcDb:AppInfo"
        self.print_dict(result.dwg_appinfo, title, level=0)

        title= "AcDb:AppInfoHistory"
        self.print_dict(result.dwg_appinfohistory, title, level=0)

        title= "AcDb:FileDepList"
        self.print_dict(result.dwg_filedeplist, title, level=0)

        '''--------------------------------
        File headers and system sections
        '''
        # 1st file header
        title= "1st File Header"
        self.print_dict(result.dwg_file_header_1st.get('body'), title, level=0)

        # 2nd file header
        title= "2nd File Header"
        self.print_dict(result.dwg_file_header_2nd.get('body'), title, level=0)

        print("[ System Sections ]")

        # page map info. (including unused list)
        page_map = result.dwg_page_map
        print("{:5} items in page map".format(len(page_map.get('map'))))
        print("{:5} items in page map (unused)".format(len(page_map.get('map_unused'))))

        # Section map info.
        section_map = result.dwg_section_map
        print("{:5} items in section map".format(len(section_map.get('map'))))

        # print("[ Section map ]")
        # for item in section_map.get('map'):
        #     title= item.get('name')
        #     self.print_dict(item, title, level=1)

        print("\n[ Object map ]")
        # Object map & Objects info. (AcDb:Handle & AcDb:AcDbObjects)
        object_map = result.dwg_object_map
        print("{:5} items in object map".format(len(object_map)))

        if output_path != "":
            f.close()
        return

    def write_to_csv_for_tool_set(self, data, output_path):
        # create the output file (csv)
        # if os.path.exists(output_path):
        #     os.remove(output_path)

        try:
            writer = csv.writer(open(output_path, 'w', newline=''), delimiter=',')
        except:
            name = ntpath.basename(output_path)
            self.logger.debug("{}(): Cannot create an output file '{}'.".format(GET_MY_NAME(), name))
            return

        if len(data) == 0:
            os.remove(output_path)
            self.logger.debug("{}(): Data is empty.".format(GET_MY_NAME()))
            return

        # Build column name list
        columns = ",".join(k for k, v in data[0].items())
        columns = columns.split(',')

        # Write columns for the output file (csv)
        writer.writerow(columns)

        # Write each row
        for item in data:
            row = []
            for k, v in item.items():
                if isinstance(v, list):
                    v = "|".join(str(x) for x in v)
                    # v = ""
                row.append(v)
            writer.writerow(row)
        return

    def print_dict(self, d, title="", level=0):
        if not isinstance(d, dict) and not isinstance(d, OrderedDict):
            return

        max_length = 0
        for k, v in d.items():
            if len(k) > max_length:
                max_length = len(k)

        tabs = ""
        if level != 0:
            tabs = "\t" * level

        if title != "":
            print("{}[ {} ]".format(tabs, title))

        for k, v in d.items():
            print("  {}{:{}} {}".format(tabs, k, max_length+3, v))
        print("\n")

    def print_hex_bytes(self, data, size_limit=1024, sep=' ', width=16):
        def quote_chars(chars):
            ascii = b"  "
            for c in chars:
                c = c.to_bytes(1, 'little')
                ascii += [b'.', c][c.isalnum()]
            return ascii.decode('UTF-8', 'ignore')

        offset = 0
        while data:
            line = data[:width]
            data = data[width:]
            print("{}{}{}{}".format(
                    "{:06X}  ".format(offset),
                    sep.join(["%02X" % c for c in line]),
                    sep, quote_chars(line))
            )
            offset += width
            if offset >= size_limit:
                break
        return

    def get_section_name(self, type):
        name = ""
        for item in DWGSectionName:
            if item.value == type:
                name = item.name
                break
        return name

    def get_object_name_non_fixed(self, type, classes):
        idx = type - 500
        if len(classes) <= idx:
            return ""
        return classes[idx]['dxf_name']

    def get_object_name(self, type, classes):
        if type >= 500:
            return self.get_object_name_non_fixed(type, classes)

        name = ""
        for item in DWGObjectType:
            if item.get_code == type:
                name = item.name
                break
        return name

    def get_object_class(self, type, classes):
        if type >= 500:
            return 'O'

        type_class = ""
        for item in DWGObjectType:
            if item.get_code == type:
                type_class = item.get_class
                break
        return type_class

    def save_data_to_file(self, path, data):
        try:
            f = open(path, 'wb')
            f.write(data)
            f.close()
        except:
            pass
        return

    def create_name_with_time(self, base):
        """Create a name with the current time

        Returns:
            A name created with the current time (str)
        """
        now = datetime.datetime.now()
        name = "[{:4}-{:02}-{:02}_{:02}.{:02}.{:02}]_{}".format(now.year, now.month, now.day,
                                                                now.hour, now.minute, now.second,
                                                                base)
        return name

    def jd_to_date(self, jd):
        """Convert Julian Day to date (year, month, day) for AutoCAD

        Args:
            jd (int): Integer value of julian days

        Returns:
            year (int), month (int), day (int)
        """
        # jd = float(jd) + 0.5
        # F, I = math.modf(float(jd))
        # I = int(I)
        I = jd
        F = 0

        A = math.trunc((I - 1867216.25)/36524.25)

        if I > 2299160:
            B = I + 1 + A - math.trunc(A / 4.)
        else:
            B = I

        C = B + 1524
        D = math.trunc((C - 122.1) / 365.25)
        E = math.trunc(365.25 * D)
        G = math.trunc((C - E) / 30.6001)

        day = C - E + F - math.trunc(30.6001 * G)

        if G < 13.5:
            month = G - 1
        else:
            month = G - 13

        if month > 2.5:
            year = D - 4716
        else:
            year = D - 4715

        return int(year), int(month), int(day)


    def jd_to_datetime(self, jd, ms, mode_jd=True):
        """Convert 'julian days and milliseconds' to a string value for AutoCAD

        Args:
            jd (int): Integer value of julian days
            ms (int): Integer value of milliseconds
            mode_jd (bool): if False, jd is just number of days

        Returns:
            (1) YY-MM-DD hh:mm:ss.ms (str)
            or
            (2) YY years MM months DD days hh hours mm minutes ss seconds (str)
        """
        YY = 0
        MM = 0
        DD = 0
        hh = 0
        mm = 0
        ss = 0
        ms = ms
        dt = ""

        # Julian date
        if mode_jd is True and jd > 0:
            YY, MM, DD = self.jd_to_date(jd)
        elif mode_jd is False:
            DD = jd

        # Fraction of day
        if ms > 0:
            ss, ms = divmod(ms, 1000)
            mm, ss = divmod(ss, 60)
            hh, mm = divmod(mm, 60)

        if mode_jd is True:
            # dt = datetime.datetime(YY, MM, DD, int(hh), int(mm), int(ss), int(ms))
            # value = dt.strftime("%Y-%m-%d %H:%M:%S.%f")
            dt = "{:04}-{:02}-{:02} {:02}:{:02}:{:02}.{:03} UTC".format(
                YY, MM, DD, int(hh), int(mm), int(ss), int(ms)
            )
        else:
            if DD != 0:
                dt += "{} days ".format(DD)
            if hh != 0:
                dt += "{} hours ".format(hh)
            if mm != 0:
                dt += "{} minutes ".format(mm)
            if ss != 0:
                dt += "{} seconds ".format(ss)

        return dt

    def rstrip_null(self, ba, unicode=False):
        if unicode is True:
            if len(ba) > 2:
                ba = ba[:-2]
        else:
            if len(ba) >= 1:
                ba = ba.split(b'\x00', 1)[0]
        return ba

    def static_cast(self, buffer, structure):
        return cast(c_char_p(buffer), POINTER(structure)).contents

    def get_dict_from_ctypes_struct(self, struct):
        """Convert ctypes struct to dict

        Args:
            struct (ctypes)

        Returns:
            Converted dict
        """
        result = OrderedDict()
        # result = dict()
        for field, _ in struct._fields_:
            value = getattr(struct, field)
            # if the type is not a primitive and it evaluates to False ...
            if (type(value) not in [int, float, bool]) and not bool(value):
                # it's a null pointer
                value = None
            elif type(value) is bytes:
                value = value.decode("utf-8")
            elif hasattr(value, "_length_") and hasattr(value, "_type_"):
                # Probably an array
                value = list(value)
            elif hasattr(value, "_fields_"):
                # Probably another struct
                value = self.get_dict_from_ctypes_struct(value)
            result[field] = value
        return result

    def check_checksum(self, data, seed, saved_value):
        """Check the checksum value

        Args:
            data (bytes)
            seed (int)
            saved_value (int)

        Returns:
            True or False
        """
        calculated_value = self.checksum(data, seed)
        if calculated_value == saved_value:
            return True
        return False

    def checksum(self, data, seed):
        """Calculate the checksum for system and data pages

        Args:
            data (bytes): Data buffer
            seed (int): Seed value

        Returns:
            Checksum value (int)
        """
        sum1 = ctypes.c_uint32(seed & 0xFFFF).value
        sum2 = ctypes.c_uint32(seed >> 0x10).value
        pos  = 0
        size = len(data)

        while size != 0:
            chunk_size = min(0x15B0, size)
            size -= chunk_size
            for idx in range(chunk_size):
                sum1 += data[pos]
                pos += 1
                sum2 += sum1
            sum1 %= 0xFFF1
            sum2 %= 0xFFF1

        sum = ctypes.c_uint32((sum2 << 0x10) | (sum1 & 0xFFFF)).value
        return sum

    def check_crc32(self, data, seed, saved_crc):
        """Check the 32-bits CRC value

        Args:
            data (bytes)
            saved_crc (int)

        Returns:
            True or False
        """
        calculated_crc = self.crc32(data, seed)
        if calculated_crc == saved_crc:
            return True
        return False

    def crc32(self, data, seed):
        """Calculate 32-bits CRC value

        Args:
            data (bytes): Data buffer
            seed (int): Seed value

        Returns:
            32-bits CRC value (int)
        """
        CRC32_TABLE = \
           [0x00000000, 0x77073096, 0xee0e612c, 0x990951ba,
            0x076dc419, 0x706af48f, 0xe963a535, 0x9e6495a3,
            0x0edb8832, 0x79dcb8a4, 0xe0d5e91e, 0x97d2d988,
            0x09b64c2b, 0x7eb17cbd, 0xe7b82d07, 0x90bf1d91,
            0x1db71064, 0x6ab020f2, 0xf3b97148, 0x84be41de,
            0x1adad47d, 0x6ddde4eb, 0xf4d4b551, 0x83d385c7,
            0x136c9856, 0x646ba8c0, 0xfd62f97a, 0x8a65c9ec,
            0x14015c4f, 0x63066cd9, 0xfa0f3d63, 0x8d080df5,
            0x3b6e20c8, 0x4c69105e, 0xd56041e4, 0xa2677172,
            0x3c03e4d1, 0x4b04d447, 0xd20d85fd, 0xa50ab56b,
            0x35b5a8fa, 0x42b2986c, 0xdbbbc9d6, 0xacbcf940,
            0x32d86ce3, 0x45df5c75, 0xdcd60dcf, 0xabd13d59,
            0x26d930ac, 0x51de003a, 0xc8d75180, 0xbfd06116,
            0x21b4f4b5, 0x56b3c423, 0xcfba9599, 0xb8bda50f,
            0x2802b89e, 0x5f058808, 0xc60cd9b2, 0xb10be924,
            0x2f6f7c87, 0x58684c11, 0xc1611dab, 0xb6662d3d,
            0x76dc4190, 0x01db7106, 0x98d220bc, 0xefd5102a,
            0x71b18589, 0x06b6b51f, 0x9fbfe4a5, 0xe8b8d433,
            0x7807c9a2, 0x0f00f934, 0x9609a88e, 0xe10e9818,
            0x7f6a0dbb, 0x086d3d2d, 0x91646c97, 0xe6635c01,
            0x6b6b51f4, 0x1c6c6162, 0x856530d8, 0xf262004e,
            0x6c0695ed, 0x1b01a57b, 0x8208f4c1, 0xf50fc457,
            0x65b0d9c6, 0x12b7e950, 0x8bbeb8ea, 0xfcb9887c,
            0x62dd1ddf, 0x15da2d49, 0x8cd37cf3, 0xfbd44c65,
            0x4db26158, 0x3ab551ce, 0xa3bc0074, 0xd4bb30e2,
            0x4adfa541, 0x3dd895d7, 0xa4d1c46d, 0xd3d6f4fb,
            0x4369e96a, 0x346ed9fc, 0xad678846, 0xda60b8d0,
            0x44042d73, 0x33031de5, 0xaa0a4c5f, 0xdd0d7cc9,
            0x5005713c, 0x270241aa, 0xbe0b1010, 0xc90c2086,
            0x5768b525, 0x206f85b3, 0xb966d409, 0xce61e49f,
            0x5edef90e, 0x29d9c998, 0xb0d09822, 0xc7d7a8b4,
            0x59b33d17, 0x2eb40d81, 0xb7bd5c3b, 0xc0ba6cad,
            0xedb88320, 0x9abfb3b6, 0x03b6e20c, 0x74b1d29a,
            0xead54739, 0x9dd277af, 0x04db2615, 0x73dc1683,
            0xe3630b12, 0x94643b84, 0x0d6d6a3e, 0x7a6a5aa8,
            0xe40ecf0b, 0x9309ff9d, 0x0a00ae27, 0x7d079eb1,
            0xf00f9344, 0x8708a3d2, 0x1e01f268, 0x6906c2fe,
            0xf762575d, 0x806567cb, 0x196c3671, 0x6e6b06e7,
            0xfed41b76, 0x89d32be0, 0x10da7a5a, 0x67dd4acc,
            0xf9b9df6f, 0x8ebeeff9, 0x17b7be43, 0x60b08ed5,
            0xd6d6a3e8, 0xa1d1937e, 0x38d8c2c4, 0x4fdff252,
            0xd1bb67f1, 0xa6bc5767, 0x3fb506dd, 0x48b2364b,
            0xd80d2bda, 0xaf0a1b4c, 0x36034af6, 0x41047a60,
            0xdf60efc3, 0xa867df55, 0x316e8eef, 0x4669be79,
            0xcb61b38c, 0xbc66831a, 0x256fd2a0, 0x5268e236,
            0xcc0c7795, 0xbb0b4703, 0x220216b9, 0x5505262f,
            0xc5ba3bbe, 0xb2bd0b28, 0x2bb45a92, 0x5cb36a04,
            0xc2d7ffa7, 0xb5d0cf31, 0x2cd99e8b, 0x5bdeae1d,
            0x9b64c2b0, 0xec63f226, 0x756aa39c, 0x026d930a,
            0x9c0906a9, 0xeb0e363f, 0x72076785, 0x05005713,
            0x95bf4a82, 0xe2b87a14, 0x7bb12bae, 0x0cb61b38,
            0x92d28e9b, 0xe5d5be0d, 0x7cdcefb7, 0x0bdbdf21,
            0x86d3d2d4, 0xf1d4e242, 0x68ddb3f8, 0x1fda836e,
            0x81be16cd, 0xf6b9265b, 0x6fb077e1, 0x18b74777,
            0x88085ae6, 0xff0f6a70, 0x66063bca, 0x11010b5c,
            0x8f659eff, 0xf862ae69, 0x616bffd3, 0x166ccf45,
            0xa00ae278, 0xd70dd2ee, 0x4e048354, 0x3903b3c2,
            0xa7672661, 0xd06016f7, 0x4969474d, 0x3e6e77db,
            0xaed16a4a, 0xd9d65adc, 0x40df0b66, 0x37d83bf0,
            0xa9bcae53, 0xdebb9ec5, 0x47b2cf7f, 0x30b5ffe9,
            0xbdbdf21c, 0xcabac28a, 0x53b39330, 0x24b4a3a6,
            0xbad03605, 0xcdd70693, 0x54de5729, 0x23d967bf,
            0xb3667a2e, 0xc4614ab8, 0x5d681b02, 0x2a6f2b94,
            0xb40bbe37, 0xc30c8ea1, 0x5a05df1b, 0x2d02ef8d]

        inverted_crc = ctypes.c_uint32(~seed).value
        for byte in data:
            inverted_crc = (inverted_crc >> 8) ^ CRC32_TABLE[(inverted_crc ^ byte) & 0xFF]
        return ctypes.c_uint32(~inverted_crc).value

    def check_crc8(self, data, seed, saved_crc):
        """Check the 8-bits CRC value

        Args:
            data (bytes)
            saved_crc (int)

        Returns:
            True or False
        """
        calculated_crc = self.crc8(data, seed)
        if calculated_crc == saved_crc:
            return True
        return False

    def crc8(self, data, seed):
        """Calculate 8-bits CRC value

        Args:
            data (bytes): Data buffer
            seed (int): Seed value

        Returns:
            8-bits CRC value (int)
        """
        CRC8_TABLE = \
           [0x0000, 0xC0C1, 0xC181, 0x0140, 0xC301, 0x03C0, 0x0280, 0xC241,
            0xC601, 0x06C0, 0x0780, 0xC741, 0x0500, 0xC5C1, 0xC481, 0x0440,
            0xCC01, 0x0CC0, 0x0D80, 0xCD41, 0x0F00, 0xCFC1, 0xCE81, 0x0E40,
            0x0A00, 0xCAC1, 0xCB81, 0x0B40, 0xC901, 0x09C0, 0x0880, 0xC841,
            0xD801, 0x18C0, 0x1980, 0xD941, 0x1B00, 0xDBC1, 0xDA81, 0x1A40,
            0x1E00, 0xDEC1, 0xDF81, 0x1F40, 0xDD01, 0x1DC0, 0x1C80, 0xDC41,
            0x1400, 0xD4C1, 0xD581, 0x1540, 0xD701, 0x17C0, 0x1680, 0xD641,
            0xD201, 0x12C0, 0x1380, 0xD341, 0x1100, 0xD1C1, 0xD081, 0x1040,
            0xF001, 0x30C0, 0x3180, 0xF141, 0x3300, 0xF3C1, 0xF281, 0x3240,
            0x3600, 0xF6C1, 0xF781, 0x3740, 0xF501, 0x35C0, 0x3480, 0xF441,
            0x3C00, 0xFCC1, 0xFD81, 0x3D40, 0xFF01, 0x3FC0, 0x3E80, 0xFE41,
            0xFA01, 0x3AC0, 0x3B80, 0xFB41, 0x3900, 0xF9C1, 0xF881, 0x3840,
            0x2800, 0xE8C1, 0xE981, 0x2940, 0xEB01, 0x2BC0, 0x2A80, 0xEA41,
            0xEE01, 0x2EC0, 0x2F80, 0xEF41, 0x2D00, 0xEDC1, 0xEC81, 0x2C40,
            0xE401, 0x24C0, 0x2580, 0xE541, 0x2700, 0xE7C1, 0xE681, 0x2640,
            0x2200, 0xE2C1, 0xE381, 0x2340, 0xE101, 0x21C0, 0x2080, 0xE041,
            0xA001, 0x60C0, 0x6180, 0xA141, 0x6300, 0xA3C1, 0xA281, 0x6240,
            0x6600, 0xA6C1, 0xA781, 0x6740, 0xA501, 0x65C0, 0x6480, 0xA441,
            0x6C00, 0xACC1, 0xAD81, 0x6D40, 0xAF01, 0x6FC0, 0x6E80, 0xAE41,
            0xAA01, 0x6AC0, 0x6B80, 0xAB41, 0x6900, 0xA9C1, 0xA881, 0x6840,
            0x7800, 0xB8C1, 0xB981, 0x7940, 0xBB01, 0x7BC0, 0x7A80, 0xBA41,
            0xBE01, 0x7EC0, 0x7F80, 0xBF41, 0x7D00, 0xBDC1, 0xBC81, 0x7C40,
            0xB401, 0x74C0, 0x7580, 0xB541, 0x7700, 0xB7C1, 0xB681, 0x7640,
            0x7200, 0xB2C1, 0xB381, 0x7340, 0xB101, 0x71C0, 0x7080, 0xB041,
            0x5000, 0x90C1, 0x9181, 0x5140, 0x9301, 0x53C0, 0x5280, 0x9241,
            0x9601, 0x56C0, 0x5780, 0x9741, 0x5500, 0x95C1, 0x9481, 0x5440,
            0x9C01, 0x5CC0, 0x5D80, 0x9D41, 0x5F00, 0x9FC1, 0x9E81, 0x5E40,
            0x5A00, 0x9AC1, 0x9B81, 0x5B40, 0x9901, 0x59C0, 0x5880, 0x9841,
            0x8801, 0x48C0, 0x4980, 0x8941, 0x4B00, 0x8BC1, 0x8A81, 0x4A40,
            0x4E00, 0x8EC1, 0x8F81, 0x4F40, 0x8D01, 0x4DC0, 0x4C80, 0x8C41,
            0x4400, 0x84C1, 0x8581, 0x4540, 0x8701, 0x47C0, 0x4680, 0x8641,
            0x8201, 0x42C0, 0x4380, 0x8341, 0x4100, 0x81C1, 0x8081, 0x4040]

        dx = seed
        for byte in data:
            al = ctypes.c_uint32(byte ^ (dx & 0xFF)).value
            dx = (dx >> 8) & 0xFF
            dx = dx ^ CRC8_TABLE[al & 0xFF]
        return dx

    def copy_16B(self, src_buf, src_idx, copy_idx, dst_buf, dst_idx):
        """Copy a compressed chunk

        Args:
            src_buf (bytes): Compressed data buffer
            src_idx (int): The current index of src_buf
            copy_idx (int)
            dst_buf (bytes): Decompressed data buffer
            dst_idx (int): The current index of dst_buf
        """
        dst_buf[dst_idx:dst_idx+8] = src_buf[src_idx+copy_idx+8:src_idx+copy_idx+16]
        dst_buf[dst_idx+8:dst_idx+16] = src_buf[src_idx+copy_idx:src_idx+copy_idx+8]

    def copy_compressed_chunk(self, src_buf, src_idx, length, dst_buf, dst_idx):
        """Copy a compressed chunk

        Args:
            src_buf (bytes): Compressed data buffer
            src_idx (int): The current index of src_buf
            length (int): This function will read this length
            dst_buf (bytes): Decompressed data buffer
            dst_idx (int): The current index of dst_buf
        """
        def copy_1b(src_buf, src_idx, copy_idx, dst_buf, dst_idx):
            dst_buf[dst_idx+0 : dst_idx+1] = src_buf[src_idx+copy_idx+0 : src_idx+copy_idx+1]
            return dst_idx+1

        def copy_2b(src_buf, src_idx, copy_idx, dst_buf, dst_idx):
            # dst_buf[dst_idx+0 : dst_idx+1] = src_buf[src_idx+copy_idx+1 : src_idx+copy_idx+2]
            # dst_buf[dst_idx+1 : dst_idx+2] = src_buf[src_idx+copy_idx+0 : src_idx+copy_idx+1]
            dst_idx = copy_1b(src_buf, src_idx+copy_idx,  1, dst_buf, dst_idx)
            dst_idx = copy_1b(src_buf, src_idx+copy_idx,  0, dst_buf, dst_idx)
            return dst_idx

        def copy_3b(src_buf, src_idx, copy_idx, dst_buf, dst_idx):
            dst_idx = copy_1b(src_buf, src_idx+copy_idx,  2, dst_buf, dst_idx)
            dst_idx = copy_1b(src_buf, src_idx+copy_idx,  1, dst_buf, dst_idx)
            dst_idx = copy_1b(src_buf, src_idx+copy_idx,  0, dst_buf, dst_idx)
            return dst_idx

        def copy_4b(src_buf, src_idx, copy_idx, dst_buf, dst_idx):
            dst_buf[dst_idx+0 : dst_idx+4] = src_buf[src_idx+copy_idx+0 : src_idx+copy_idx+4]
            return dst_idx+4

        def copy_8b(src_buf, src_idx, copy_idx, dst_buf, dst_idx):
            dst_buf[dst_idx+0 : dst_idx+8] = src_buf[src_idx+copy_idx+0 : src_idx+copy_idx+8]
            return dst_idx+8

        def copy_16b(src_buf, src_idx, copy_idx, dst_buf, dst_idx):
            # dst_buf[dst_idx+0 : dst_idx+8 ] = src_buf[src_idx+copy_idx+8 : src_idx+copy_idx+16]
            # dst_buf[dst_idx+8 : dst_idx+16] = src_buf[src_idx+copy_idx+0 : src_idx+copy_idx+8 ]
            dst_idx = copy_8b(src_buf, src_idx+copy_idx, 8, dst_buf, dst_idx)
            dst_idx = copy_8b(src_buf, src_idx+copy_idx, 0, dst_buf, dst_idx)
            return dst_idx

        while 32 <= length:
            dst_idx = copy_16b(src_buf, src_idx, 16, dst_buf, dst_idx)
            dst_idx = copy_16b(src_buf, src_idx,  0, dst_buf, dst_idx)
            src_idx += 32
            length  -= 32

        if length == 1:
            copy_1b(src_buf, src_idx,  0, dst_buf, dst_idx)
        elif length == 2:
            dst_idx = copy_1b(src_buf, src_idx,  1, dst_buf, dst_idx)
            dst_idx = copy_1b(src_buf, src_idx,  0, dst_buf, dst_idx)
            # copy_2b(src_buf, src_idx,  0, dst_buf, dst_idx)
        elif length == 3:
            dst_idx = copy_1b(src_buf, src_idx,  2, dst_buf, dst_idx)
            dst_idx = copy_1b(src_buf, src_idx,  1, dst_buf, dst_idx)
            dst_idx = copy_1b(src_buf, src_idx,  0, dst_buf, dst_idx)
        elif length == 4:
            dst_idx = copy_1b(src_buf, src_idx,  0, dst_buf, dst_idx)
            dst_idx = copy_1b(src_buf, src_idx,  1, dst_buf, dst_idx)
            dst_idx = copy_1b(src_buf, src_idx,  2, dst_buf, dst_idx)
            dst_idx = copy_1b(src_buf, src_idx,  3, dst_buf, dst_idx)
        elif length == 5:
            dst_idx = copy_1b(src_buf, src_idx,  4, dst_buf, dst_idx)
            dst_idx = copy_4b(src_buf, src_idx,  0, dst_buf, dst_idx)
        elif length == 6:
            dst_idx = copy_1b(src_buf, src_idx,  5, dst_buf, dst_idx)
            dst_idx = copy_4b(src_buf, src_idx,  1, dst_buf, dst_idx)
            dst_idx = copy_1b(src_buf, src_idx,  0, dst_buf, dst_idx)
        elif length == 7:
            dst_idx = copy_2b(src_buf, src_idx,  5, dst_buf, dst_idx)
            dst_idx = copy_4b(src_buf, src_idx,  1, dst_buf, dst_idx)
            dst_idx = copy_1b(src_buf, src_idx,  0, dst_buf, dst_idx)
        elif length == 8:
            dst_idx = copy_4b(src_buf, src_idx,  0, dst_buf, dst_idx)
            dst_idx = copy_4b(src_buf, src_idx,  4, dst_buf, dst_idx)
        elif length == 9:
            dst_idx = copy_1b(src_buf, src_idx,  8, dst_buf, dst_idx)
            dst_idx = copy_8b(src_buf, src_idx,  0, dst_buf, dst_idx)
        elif length == 10:
            dst_idx = copy_1b(src_buf, src_idx,  9, dst_buf, dst_idx)
            dst_idx = copy_8b(src_buf, src_idx,  1, dst_buf, dst_idx)
            dst_idx = copy_1b(src_buf, src_idx,  0, dst_buf, dst_idx)
        elif length == 11:
            dst_idx = copy_2b(src_buf, src_idx,  9, dst_buf, dst_idx)
            dst_idx = copy_8b(src_buf, src_idx,  1, dst_buf, dst_idx)
            dst_idx = copy_1b(src_buf, src_idx,  0, dst_buf, dst_idx)
        elif length == 12:
            dst_idx = copy_4b(src_buf, src_idx,  8, dst_buf, dst_idx)
            dst_idx = copy_8b(src_buf, src_idx,  0, dst_buf, dst_idx)
        elif length == 13:
            dst_idx = copy_1b(src_buf, src_idx, 12, dst_buf, dst_idx)
            dst_idx = copy_4b(src_buf, src_idx,  8, dst_buf, dst_idx)
            dst_idx = copy_8b(src_buf, src_idx,  0, dst_buf, dst_idx)
        elif length == 14:
            dst_idx = copy_1b(src_buf, src_idx, 13, dst_buf, dst_idx)
            dst_idx = copy_4b(src_buf, src_idx,  9, dst_buf, dst_idx)
            dst_idx = copy_8b(src_buf, src_idx,  1, dst_buf, dst_idx)
            dst_idx = copy_1b(src_buf, src_idx,  0, dst_buf, dst_idx)
        elif length == 15:
            dst_idx = copy_2b(src_buf, src_idx, 13, dst_buf, dst_idx)
            dst_idx = copy_4b(src_buf, src_idx,  9, dst_buf, dst_idx)
            dst_idx = copy_8b(src_buf, src_idx,  1, dst_buf, dst_idx)
            dst_idx = copy_1b(src_buf, src_idx,  0, dst_buf, dst_idx)
        elif length == 16:
            dst_idx = copy_8b(src_buf, src_idx,  8, dst_buf, dst_idx)
            dst_idx = copy_8b(src_buf, src_idx,  0, dst_buf, dst_idx)
        elif length == 17:
            dst_idx = copy_8b(src_buf, src_idx,  9, dst_buf, dst_idx)
            dst_idx = copy_1b(src_buf, src_idx,  8, dst_buf, dst_idx)
            dst_idx = copy_8b(src_buf, src_idx,  0, dst_buf, dst_idx)
        elif length == 18:
            dst_idx = copy_1b(src_buf, src_idx, 17, dst_buf, dst_idx)
            dst_idx = copy_16b(src_buf, src_idx, 1, dst_buf, dst_idx)
            dst_idx = copy_1b(src_buf, src_idx,  0, dst_buf, dst_idx)
        elif length == 19:
            dst_idx = copy_3b(src_buf, src_idx, 16, dst_buf, dst_idx)
            dst_idx = copy_16b(src_buf, src_idx, 0, dst_buf, dst_idx)
        elif length == 20:
            dst_idx = copy_4b(src_buf, src_idx, 16, dst_buf, dst_idx)
            dst_idx = copy_16b(src_buf, src_idx, 0, dst_buf, dst_idx)
        elif length == 21:
            dst_idx = copy_1b(src_buf, src_idx, 20, dst_buf, dst_idx)
            dst_idx = copy_4b(src_buf, src_idx, 16, dst_buf, dst_idx)
            dst_idx = copy_16b(src_buf, src_idx, 0, dst_buf, dst_idx)
        elif length == 22:
            dst_idx = copy_2b(src_buf, src_idx, 20, dst_buf, dst_idx)
            dst_idx = copy_4b(src_buf, src_idx, 16, dst_buf, dst_idx)
            dst_idx = copy_16b(src_buf, src_idx, 0, dst_buf, dst_idx)
        elif length == 23:
            dst_idx = copy_3b(src_buf, src_idx, 20, dst_buf, dst_idx)
            dst_idx = copy_4b(src_buf, src_idx, 16, dst_buf, dst_idx)
            dst_idx = copy_16b(src_buf, src_idx, 0, dst_buf, dst_idx)
        elif length == 24:
            dst_idx = copy_8b(src_buf, src_idx, 16, dst_buf, dst_idx)
            dst_idx = copy_16b(src_buf, src_idx, 0, dst_buf, dst_idx)
        elif length == 25:
            dst_idx = copy_8b(src_buf, src_idx, 17, dst_buf, dst_idx)
            dst_idx = copy_1b(src_buf, src_idx, 16, dst_buf, dst_idx)
            dst_idx = copy_16b(src_buf, src_idx, 0, dst_buf, dst_idx)
        elif length == 26:
            dst_idx = copy_1b(src_buf, src_idx, 25, dst_buf, dst_idx)
            dst_idx = copy_8b(src_buf, src_idx, 17, dst_buf, dst_idx)
            dst_idx = copy_1b(src_buf, src_idx, 16, dst_buf, dst_idx)
            dst_idx = copy_16b(src_buf, src_idx, 0, dst_buf, dst_idx)
        elif length == 27:
            dst_idx = copy_2b(src_buf, src_idx, 25, dst_buf, dst_idx)
            dst_idx = copy_8b(src_buf, src_idx, 17, dst_buf, dst_idx)
            dst_idx = copy_1b(src_buf, src_idx, 16, dst_buf, dst_idx)
            dst_idx = copy_16b(src_buf, src_idx, 0, dst_buf, dst_idx)
        elif length == 28:
            dst_idx = copy_4b(src_buf, src_idx, 24, dst_buf, dst_idx)
            dst_idx = copy_8b(src_buf, src_idx, 16, dst_buf, dst_idx)
            dst_idx = copy_16b(src_buf, src_idx, 0, dst_buf, dst_idx)
        elif length == 29:
            dst_idx = copy_1b(src_buf, src_idx, 28, dst_buf, dst_idx)
            dst_idx = copy_4b(src_buf, src_idx, 24, dst_buf, dst_idx)
            dst_idx = copy_8b(src_buf, src_idx, 16, dst_buf, dst_idx)
            dst_idx = copy_16b(src_buf, src_idx, 0, dst_buf, dst_idx)
        elif length == 30:
            dst_idx = copy_2b(src_buf, src_idx, 28, dst_buf, dst_idx)
            dst_idx = copy_4b(src_buf, src_idx, 24, dst_buf, dst_idx)
            dst_idx = copy_8b(src_buf, src_idx, 16, dst_buf, dst_idx)
            dst_idx = copy_16b(src_buf, src_idx, 0, dst_buf, dst_idx)
        elif length == 31:
            dst_idx = copy_1b(src_buf, src_idx, 30, dst_buf, dst_idx)
            dst_idx = copy_4b(src_buf, src_idx, 26, dst_buf, dst_idx)
            dst_idx = copy_8b(src_buf, src_idx, 18, dst_buf, dst_idx)
            dst_idx = copy_16b(src_buf, src_idx, 2, dst_buf, dst_idx)
            dst_idx = copy_2b(src_buf, src_idx,  0, dst_buf, dst_idx)

    def copy_decompressed_chunks(self, src_buf, src_idx, dst_buf, dst_idx):
        """Copy decompressed chunks

        Args:
            src_buf (bytes): Compressed data buffer
            src_idx (int): The current index of src_buf
            dst_buf (bytes): Decompressed data buffer
            dst_idx (int): The current index of dst_buf

        Returns:
            length (int), src_idx (int), dst_idx (int)
        """
        def read_instructions(src_buf, src_idx, opcode):
            if (opcode >> 4) == 0:
                length = (opcode & 0xF) + 0x13
                offset = src_buf[src_idx]
                src_idx += 1
                opcode = src_buf[src_idx]
                src_idx += 1
                length = ((opcode >> 3) & 0x10) + length
                offset = ctypes.c_uint32((opcode & 0x78) << 5).value + 1 + offset
            elif (opcode >> 4) == 1:
                length = (opcode & 0xF) + 0x3
                offset = src_buf[src_idx]
                src_idx += 1
                opcode = src_buf[src_idx]
                src_idx += 1
                offset = ctypes.c_uint32((opcode & 0xF8) << 5).value + 1 + offset
            elif (opcode >> 4) == 2:
                offset = src_buf[src_idx]
                src_idx += 1
                offset = ctypes.c_uint32((src_buf[src_idx] << 8) & 0xFF00).value | offset
                src_idx += 1
                length = opcode & 7
                if (opcode & 8) == 0:
                    opcode = src_buf[src_idx]
                    src_idx += 1
                    length = (opcode & 0xF8) + length
                else:
                    offset += 1
                    length = ctypes.c_uint32(src_buf[src_idx] << 3).value + length
                    src_idx += 1
                    opcode = src_buf[src_idx]
                    src_idx += 1
                    length = (ctypes.c_uint32((opcode & 0xF8) << 8).value + length) + 0x100
            else:
                length = opcode >> 4
                offset = opcode & 15
                opcode = src_buf[src_idx]
                src_idx += 1
                offset = (ctypes.c_uint32((opcode & 0xF8) << 1).value + offset) + 1

            return opcode, offset, length, src_idx

        def copy_bytes(dst_buf, dst_idx, offset, length):
            offset = dst_idx - offset
            if offset < 0:
                print("[Abnormal] copy_bytes")
                return dst_idx+length
            for idx in range(length):
                dst_buf[dst_idx + idx] = dst_buf[offset + idx]
            return dst_idx+length

        src_size = len(src_buf)  # compressed_end_index_plus_one
        opcode = src_buf[src_idx]
        src_idx += 1

        opcode, offset, length, src_idx = \
            read_instructions(src_buf, src_idx, opcode)

        while True:
            dst_idx = copy_bytes(dst_buf, dst_idx, offset, length)

            length = opcode & 7
            if length != 0 or src_idx >= src_size:
                break

            opcode = src_buf[src_idx]
            src_idx += 1

            if (opcode >> 4) == 0:
                break

            if (opcode >> 4) == 15:
                opcode &= 15

            opcode, offset, length, src_idx = \
                read_instructions(src_buf, src_idx, opcode)

        return opcode, length, src_idx, dst_idx


    def decompress_r2007(self, src_buf, dst_size):
        """Decompress R21 data

        Args:
            src_buf (bytes): Compressed data buffer
            src_size (int): Compressed data size
            dst_size (int): Decompressed size

        Returns:
            Decompressed data (bytes)
        """
        def read_literal_length(src_buf, src_idx, opcode):
            """Read a literal length

            Args:
                src_buf (bytes): Compressed data buffer
                src_idx (int): The current index of src_buf
                opcode (int): The current opcode

            Returns:
                length (int), src_idx (idx)
            """
            length = opcode + 8
            if length == 0x17:
                n = src_buf[src_idx]
                src_idx += 1
                length += n
                if n == 0xFF:
                    while True:
                        n = src_buf[src_idx]
                        src_idx += 1
                        n |= ctypes.c_uint32(src_buf[src_idx] << 8).value
                        src_idx += 1
                        length += n
                        if n != 0xFFFF:
                            break
            return length, src_idx

        dst_buf = bytearray(dst_size)
        dst_size = len(dst_buf)
        src_size = len(src_buf)

        length = 0
        src_idx = 0
        dst_idx = 0
        opcode = src_buf[src_idx]
        src_idx += 1

        # Get the literal length
        if (opcode & 0xF0) == 0x20:
            src_idx += 2
            length = src_buf[src_idx] & 0x07
            src_idx += 1

        while src_idx < src_size:
            if length == 0:
                length, src_idx = read_literal_length(src_buf, src_idx, opcode)

            if dst_size < dst_idx + length:
                break

            self.copy_compressed_chunk(src_buf, src_idx,
                                       length,
                                       dst_buf, dst_idx)

            dst_idx += length
            src_idx += length

            if src_idx >= src_size:
                break

            opcode, length, src_idx, dst_idx = \
                self.copy_decompressed_chunks(src_buf, src_idx,
                                              dst_buf, dst_idx)

        return bytes(dst_buf)

    def decode_reed_solomon(self, src_buf, k, block_count, method=4):
        """Decode reed solomon encoded data

        Args:
            src_buf (bytes): Source data buffer
            k (int): 239 for system pages, 251 for data pages
            block_count (int): Encoded block count (= correction factor = repeat count?)
            method (int): 4 (interleaved), 1 (non-interleaved)

        Returns:
            Decoded data (bytes)
        """
        # dst_buf = b""
        dst_buf = bytearray(k * block_count)
        dst_idx = 0
        src_idx = 0

        if method == 4:
            for bc in range(block_count):
                for idx in range(k):
                    dst_buf[dst_idx] = src_buf[(block_count*idx) + src_idx]
                    dst_idx += 1
                    # byte = src_buf[src_idx + (block_count*idx_k)]
                    # dst_buf += byte.to_bytes(1, 'little')
                src_idx += 1
        elif method == 1:
            dst_buf[0:k*block_count] = src_buf[0:k*block_count]
        else:
            msg = "Found unknown RS encoding method."
            self.logger.debug("{}(): {}".format(GET_MY_NAME(), msg))
            self.report.add(DWGVInfo(DWGVType.CORRUPTED, -1, -1, msg))

        return bytes(dst_buf)

    def decompress_r18(self, src_buf, src_size, dst_size):
        """Decompress R18 data

        Args:
            src_buf (bytes): Compressed data buffer
            src_size (int): Compressed data size
            dst_size (int): Decompressed size

        Returns:
            Decompressed data (bytes)
        """
        def read_literal_length(bc):
            opcode1 = 0x00
            length = 0x00
            byte = bc.read_rc()
            if 0x01 <= byte <= 0x0F:
                length = byte + 3  # 4 ~ 18
            elif byte & 0xF0:
                opcode1 = byte
            elif byte == 0x00:
                length = 0x0F
                byte = bc.read_rc()
                while byte == 0x00:
                    length += 0xFF
                    byte = bc.read_rc()
                length = length + byte + 3
            return length, opcode1

        def read_long_compression_offset(bc):
            value = 0
            byte = bc.read_rc()
            if byte == 0:
                value = 0xFF
                byte = bc.read_rc()
                while byte == 0x00:
                    value += 0xFF
                    byte = bc.read_rc()
            return value + byte

        def read_two_byte_offset(bc):
            byte_1st = bc.read_rc()
            byte_2nd = bc.read_rc()
            value = (byte_1st >> 2) | (byte_2nd << 6)
            literal_count = byte_1st & 0x03
            return value, literal_count

        def copy_compressed_bytes(dst_buf, dst_idx, length, src_buf, src_idx):
            dst_buf[dst_idx : dst_idx + length] = src_buf[src_idx : src_idx + length]
            return dst_idx + length

        def copy_decompressed_bytes(dst_buf, dst_idx, offset, length):
            offset = dst_idx - offset
            if offset < 0:
                msg = "[{}] Found corrupted data during decompression.".format("decompress_r18")
                self.logger.debug("{}(): {}".format(GET_MY_NAME(), msg))
                self.report.add(DWGVInfo(DWGVType.CORRUPTED, -1, -1, msg))
                return dst_idx+length
            for idx in range(length):
                dst_buf[dst_idx + idx] = dst_buf[offset + idx]
            return dst_idx+length

        dst_buf = bytearray(dst_size)
        dst_idx = 0

        bc = DWGBitCodes(src_buf, len(src_buf))

        # Get the literal length
        literal_length, opcode1 = read_literal_length(bc)

        # Get the first literal run
        dst_idx = copy_compressed_bytes(dst_buf, dst_idx, literal_length, src_buf, bc.pos_byte)
        bc.plus_pos(literal_length)

        # Read a set of compression opcodes
        while bc.pos_byte < src_size:
            if opcode1 == 0x00:
                opcode1 = bc.read_rc()

            if opcode1 == 0x10:
                compressed_bytes = read_long_compression_offset(bc) + 9
                compressed_offset, literal_length = read_two_byte_offset(bc)
                compressed_offset += 0x3FFF
                if literal_length == 0:
                    literal_length, opcode1 = read_literal_length(bc)
                else:
                    opcode1 = 0x00
            elif opcode1 == 0x11:
                break
            elif 0x12 <= opcode1 <= 0x1F:
                compressed_bytes = (opcode1 & 0x0F) + 2
                compressed_offset, literal_length = read_two_byte_offset(bc)
                compressed_offset += 0x3FFF
                if literal_length == 0:
                    literal_length, opcode1 = read_literal_length(bc)
                else:
                    opcode1 = 0x00
            elif opcode1 == 0x20:
                compressed_bytes = read_long_compression_offset(bc) + 0x21
                compressed_offset, literal_length = read_two_byte_offset(bc)
                if literal_length == 0:
                    literal_length, opcode1 = read_literal_length(bc)
                else:
                    opcode1 = 0x00
            elif 0x21 <= opcode1 <= 0x3F:
                compressed_bytes = (opcode1 - 0x1E)
                compressed_offset, literal_length = read_two_byte_offset(bc)
                if literal_length == 0:
                    literal_length, opcode1 = read_literal_length(bc)
                else:
                    opcode1 = 0x00
            elif 0x40 <= opcode1 <= 0xFF:
                compressed_bytes = ((opcode1 & 0xF0) >> 4) - 1
                opcode2 = bc.read_rc()
                compressed_offset = (opcode2 << 2) | ((opcode1 & 0x0C) >> 2)
                if opcode1 & 0x03:
                    literal_length = (opcode1 & 0x03)
                    opcode1 = 0x00
                else:
                    literal_length, opcode1 = read_literal_length(bc)
            else:
                msg = "[{}] Found corrupted data during decompression.".format("decompress_r18")
                self.logger.debug("{}(): {}".format(GET_MY_NAME(), msg))
                self.report.add(DWGVInfo(DWGVType.CORRUPTED, -1, -1, msg))
                break

            # Get compressed data
            if len(dst_buf) - 1 >= compressed_offset:
                dst_idx = copy_decompressed_bytes(
                    dst_buf, dst_idx,
                    compressed_offset+1, compressed_bytes
                )

            # Get literal data
            dst_idx = copy_compressed_bytes(dst_buf, dst_idx, literal_length, src_buf, bc.pos_byte)
            bc.plus_pos(literal_length)

        return bytes(dst_buf)
