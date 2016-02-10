# -*- coding: utf-8 -*-

"""@package pydwg

    * Description
        Common defines for pydwg
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
PYDWG_VERSION = '0.3'


from ctypes import *
from enum import Enum, IntEnum
import inspect
GET_MY_NAME = lambda: inspect.stack()[1][3]

def RELEASE_LIST(a):
   del a[:]
   del a

class DWGParsingMode(IntEnum):
    """DWGParsingMode class
    """
    VALIDATION = 0
    METADATA = 1
    FULL = 2


class DWGVersion(IntEnum):
    """DWGVersion class

        DWG format versions - https://en.wikipedia.org/wiki/AutoCAD
    """
    UNSUPPORTED = 0
    R13 = 19   # AC1012 = R13 = version 19 (not supported)
    R14 = 20   # AC1014 = R14 = version 20 (not supported)
    R15 = 22   # AC1015 = R15 = version 22 & 23 (not supported)
    R18 = 24   # AC1018 = R18 = version 24 & 25
    R21 = 26   # AC1021 = R21 = version 26 & 27 (incomplete)
    R24 = 28   # AC1024 = R24 = version 28 & 29 (will be supported later)
    R27 = 30   # AC1027 = R27 = version 30 & 31 (will be supported later)


class DWGSectionName(Enum):
    """DWGSectionName class
    """
    HEADER          = "AcDb:Header",
    AUXHEADER       = "AcDb:AuxHeader",
    CLASSES         = "AcDb:Classes",
    HANDLES         = "AcDb:Handles",       # object map
    TEMPLATE        = "AcDb:Template",
    OBJFREESPACE    = "AcDb:ObjFreeSpace",
    ACDBOBJECTS     = "AcDb:AcDbObjects",   # objects
    REVHISTORY      = "AcDb:RevHistory",
    SUMMARYINFO     = "AcDb:SummaryInfo",
    PREVIEW         = "AcDb:Preview",
    APPINFO         = "AcDb:AppInfo",
    APPINFOHISTORY  = "AcDb:AppInfoHistory",
    FILEDEPLIST     = "AcDb:FileDepList",
    SECURITY        = "AcDb:Security",
    VBAPROJECT      = "AcDb:VBAProject",
    SIGNATURE       = "AcDb:Signature"
    # ACDSPROTOTYPE_1B # ?

    def __init__(self, name):
        self._name = name

    @property
    def value(self):
        return self._name

class DWGSectionHashCode(IntEnum):
    """DWGSectionHashCode class
    """
    HEADER          = 0x32b803d9,
    AUXHEADER       = 0x54f0050a,
    CLASSES         = 0x3f54045f,
    HANDLES         = 0x3f6e0450,  # object map
    TEMPLATE        = 0x4a1404ce,
    OBJFREESPACE    = 0x77e2061f,
    ACDBOBJECTS     = 0x674c05a9,  # objects
    REVHISTORY      = 0x60a205b3,
    SUMMARYINFO     = 0x717a060f,
    PREVIEW         = 0x40aa0473,
    APPINFO         = 0x3fa0043e,
    APPINFOHISTORY  = 0x96de0737,
    FILEDEPLIST     = 0x6c4205ca,
    SECURITY        = 0x4a0204ea,
    VBAPROJECT      = 0x586e0544
    # SIGNATURE   # ?
    # ACDSPROTOTYPE_1B # ?


class DWGObjectTypeClass(Enum):
    """DWGObjectTypeClass class
    """
    UNUSED = ''
    OBJECT = 'O'
    ENTITY = 'E'


class DWGObjectType(Enum):
    """DWGObjectType class
    """
    UNUSED              = (0x00, '')
    TEXT                = (0x01, 'E')
    ATTRIB              = (0x02, 'E')
    ATTDEF              = (0x03, 'E')
    BLOCK               = (0x04, 'E')
    ENDBLK              = (0x05, 'E')
    SEQEND              = (0x06, 'E')
    INSERT              = (0x07, 'E')
    MINSERT             = (0x08, 'E')
    # UNKNOWN           = (0x09, 'E')
    VERTEX_2D           = (0x0A, 'E')
    VERTEX_3D           = (0x0B, 'E')
    VERTEX_MESH         = (0x0C, 'E')
    VERTEX_PFACE        = (0x0D, 'E')
    VERTEX_PFACE_FACE   = (0x0E, 'E')
    POLYLINE_2D         = (0x0F, 'E')
    POLYLINE_3D         = (0x10, 'E')
    ARC                 = (0x11, 'E')
    CIRCLE              = (0x12, 'E')
    LINE                = (0x13, 'E')
    DIM_ORDINATE        = (0x14, 'E')   # DIMENSION
    DIM_LINEAR          = (0x15, 'E')   # DIMENSION
    DIM_ALIGNED         = (0x16, 'E')   # DIMENSION
    DIM_ANG3PT          = (0x17, 'E')   # DIMENSION
    DIM_ANG2LN          = (0x18, 'E')   # DIMENSION
    DIM_RADIUS          = (0x19, 'E')   # DIMENSION
    DIM_DIAMETER        = (0x1A, 'E')   # DIMENSION
    POINT               = (0x1B, 'E')
    _3DFACE             = (0x1C, 'E')
    POLYLINE_PFACE      = (0x1D, 'E')
    POLYLINE_MESH       = (0x1E, 'E')
    SOLID               = (0x1F, 'E')
    TRACE               = (0x20, 'E')
    SHAPE               = (0x21, 'E')
    VIEWPORT            = (0x22, 'E')
    ELLIPSE             = (0x23, 'E')
    SPLINE              = (0x24, 'E')
    REGION              = (0x25, 'E')
    _3DSOLID            = (0x26, 'E')
    BODY                = (0x27, 'E')
    RAY                 = (0x28, 'E')
    XLINE               = (0x29, 'E')
    DICTIONARY          = (0x2A, 'O')
    OLEFRAME            = (0x2B, 'E')
    MTEXT               = (0x2C, 'E')
    LEADER              = (0x2D, 'E')
    TOLERANCE           = (0x2E, 'E')
    MLINE               = (0x2F, 'E')
    BLOCK_CONTROL       = (0x30, 'O')
    BLOCK_HEADER        = (0x31, 'O')
    LAYER_CONTROL       = (0x32, 'O')
    LAYER               = (0x33, 'O')
    SHAPEFILE_CONTROL   = (0x34, 'O')
    SHAPEFILE           = (0x35, 'O')
    # UNKNOWN           = (0x36, 'E')
    # UNKNOWN           = (0x37, 'E')
    LTYPE_CONTROL       = (0x38, 'O')
    LTYPE               = (0x39, 'O')
    # UNKNOWN           = (0x3A, 'E')
    # UNKNOWN           = (0x3B, 'E')
    VIEW_CONTROL        = (0x3C, 'O')
    VIEW                = (0x3D, 'O')
    UCS_CONTROL         = (0x3E, 'O')
    UCS                 = (0x3F, 'O')
    VPORT_CONTROL       = (0x40, 'O')
    VPORT               = (0x41, 'O')
    APPID_CONTROL       = (0x42, 'O')
    APPID               = (0x43, 'O')
    DIMSTYLE_CONTROL    = (0x44, 'O')
    DIMSTYLE            = (0x45, 'O')
    VP_ENT_HDR_CONTROL  = (0x46, 'O')
    VP_ENT_HDR          = (0x47, 'O')
    GROUP               = (0x48, 'O')
    MLINESTYLE          = (0x49, 'O')
    OLE2FRAME           = (0x4A, 'E')
    # UNKNOWN (DUMMY)   = (0x4B, 'E')
    LONG_TRANSACTION    = (0x4C, 'E')  # ?
    LWPOLYLINE          = (0x4D, 'E')
    HATCH               = (0x4E, 'E')
    XRECORD             = (0x4F, 'O')
    ACDBPLACEHOLDER     = (0x50, 'O')
    VBA_PROJECT         = (0x51, 'O')
    LAYOUT              = (0x52, 'O')

    def __init__(self, type_code, type_class):
        self.type_code  = type_code
        self.type_class = type_class

    @property
    def get_code(self):
        return self.type_code

    @property
    def get_class(self):
        return self.type_class


class DWGHandleCode(IntEnum):
    """DWGHandleCode class
    """
    ANY            = 0x00,
    SOFT_OWNERSHIP = 0x02,
    HARD_OWNERSHIP = 0x03,
    SOFT_POINTER   = 0x04,
    HARD_POINTER   = 0x05


class DWGEncoding(Enum):
    """DWGEncoding class
    """
    UTF16LE = "utf-16le"
    UTF8 = "utf-8"
    KOREAN = "euc-kr"
    JAPANESE = "euc-jp"
    CHINESE_GB = "gb18030"
    CHINESE_BIG5 = "big-5"


DWG_SENTINEL_HEADER_BEFORE = \
    [0xCF, 0x7B, 0x1F, 0x23, 0xFD, 0xDE, 0x38, 0xA9, 0x5F, 0x7C, 0x68, 0xB8, 0x4E, 0x6D, 0x33, 0x5F]
DWG_SENTINEL_HEADER_AFTER = \
    [0x30, 0x84, 0xE0, 0xDC, 0x02, 0x21, 0xC7, 0x56, 0xA0, 0x83, 0x97, 0x47, 0xB1, 0x92, 0xCC, 0xA0]

DWG_SENTINEL_CLASSES_BEFORE = \
    [0x8D, 0xA1, 0xC4, 0xB8, 0xC4, 0xA9, 0xF8, 0xC5, 0xC0, 0xDC, 0xF4, 0x5F, 0xE7, 0xCF, 0xB6, 0x8A]
DWG_SENTINEL_CLASSES_AFTER = \
    [0x72, 0x5E, 0x3B, 0x47, 0x3B, 0x56, 0x07, 0x3A, 0x3F, 0x23, 0x0B, 0xA0, 0x18, 0x30, 0x49, 0x75]

DWG_SENTINEL_PREVIEW_BEFORE = \
    [0x1F, 0x25, 0x6D, 0x07, 0xD4, 0x36, 0x28, 0x28, 0x9D, 0x57, 0xCA, 0x3F, 0x9D, 0x44, 0x10, 0x2B]
DWG_SENTINEL_PREVIEW_AFTER = \
    [0xE0, 0xDA, 0x92, 0xF8, 0x2B, 0xC9, 0xD7, 0xD7, 0x62, 0xA8, 0x35, 0xC0, 0x62, 0xBB, 0xEF, 0xD4]


"""
R18 Structures
"""

class DWG_R18_FILE_HEADER_1ST(LittleEndianStructure):
    _fields_ = [
        ("signature",                   c_char*6),      # AC1018
        ("zero5",                       c_ubyte*5),     # 5 bytes of 0x00
        ("maintenance_version",         c_ubyte),       # maintenance release version
        ("unknown1",                    c_ubyte),       # 0x00, 0x01 or 0x03
        ("preview_address",             c_uint),        # address of 'image page' + page header size (0x20)
        ("app_version",                 c_ubyte),       # application version
        ("app_maintenance_version",     c_ubyte),       # application maintenance release version
        ("codepage",                    c_ushort),      # codepage
        ("zero3",                       c_ubyte*3),     # 3 bytes of 0x00
        ("security_flags",              c_uint),        # security flags, default is 0
                                                        # 0x01 = encrypted data (sections except Preview & SummaryInfo)
                                                        # 0x02 = encrypted properties (for Preview & SummaryInfo)
                                                        # 0x10 = sign data
                                                        # 0x20 = add timestamp
        ("unknown2",                    c_uint),
        ("summary_info_address",        c_uint),        # address of 'summary info page' + page header size (0x20)
        ("vba_project_address",         c_uint),
        ("unknown3",                    c_uint),        # 0x00000080
        ("unknown4",                    c_ubyte*84),    # NULL
        ("encrypted_header",            c_ubyte*108)    # encrypted header data
    ]
    _pack_ = 1


class DWG_R18_FILE_HEADER_2ND(LittleEndianStructure):   # -> encrypted header data of 1st file header
    _fields_ = [
        ("id_string",                     c_char*12),   # 'AcFssFcAJMB'
        ("x00",                           c_uint),      # 0x00 (4 bytes)
        ("x6C",                           c_uint),      # 0x6C (4 bytes)
        ("x04",                           c_uint),      # 0x04 (4 bytes)
        ("root_tree_node_gap",            c_uint),
        ("lowermost_left_tree_node_gap",  c_uint),
        ("lowermost_right_tree_node_gap", c_uint),
        ("unknown1",                      c_uint),
        ("last_section_page_id",          c_uint),
        ("last_section_page_address",     c_uint64),
        ("second_header_address",         c_uint64),    # pointing to the repeated header data at the end of the file
        ("gap_amount",                    c_uint),
        ("section_page_amount",           c_uint),
        ("x20",                           c_uint),      # 0x20 (4 bytes)
        ("x80",                           c_uint),      # 0x80 (4 bytes)
        ("x40",                           c_uint),      # 0x40 (4 bytes)
        ("page_map_id",                   c_uint),
        ("page_map_address",              c_uint64),    # add 0x100 to this value
        ("section_map_id",                c_uint),
        ("section_page_array_size",       c_uint),      # page ID max
        ("gap_array_size",                c_uint),
        ("crc32",                         c_uint)       # the seed is zero.
    ]
    _pack_ = 4


class DWG_R18_SYSTEM_SECTION_HEADER(LittleEndianStructure):
    _fields_ = [
        ("signature",                     c_uint),      # page map (0x41630E3B), section map (0x4163003B)
        ("decompressed_size",             c_uint),
        ("compressed_size",               c_uint),
        ("compressed_type",               c_uint),      # 0x02
        ("checksum",                      c_uint)
    ]
    _pack_ = 4


class DWG_R18_SECTION_MAP_HEADER(LittleEndianStructure):
    _fields_ = [
        ("section_entry_count",           c_uint),      # total number of data sections
        ("x02",                           c_uint),
        ("x00007400",                     c_uint),
        ("x00",                           c_uint),
        ("unknown",                       c_uint)
    ]
    _pack_ = 4


class DWG_R18_SECTION_ENTRY(LittleEndianStructure):
    _fields_ = [
        ("size",                          c_uint64),
        ("page_count",                    c_uint),
        ("max_decompressed_size",         c_uint),
        ("unknown",                       c_uint),
        ("compressed",                    c_uint),      # 1 = no, 2 = yes
        ("type",                          c_uint),      # see DWGSectionName
        ("encrypted",                     c_uint),      # 0 = no, 1 = yes, 2 = unknown
        ("name",                          c_char*64)    # string
    ]
    _pack_ = 4


class DWG_R18_SECTION_ENTRY_PAGE_INFO(LittleEndianStructure):
    _fields_ = [
        ("id",                            c_uint),      # a page ID in system page map
        ("size",                          c_uint),
        ("address",                       c_uint64)
    ]
    _pack_ = 4


class DWG_R18_DATA_SECTION_HEADER(LittleEndianStructure):
    _fields_ = [
        ("signature",                     c_uint),      # data section (0x4163043B)
        ("type",                          c_uint),
        ("compressed_size",               c_uint),
        ("decompressed_size",             c_uint),
        ("start_offset",                  c_uint),      # in the decompressed buffer
        ("page_header_checksum",          c_uint),
        ("data_checksum",                 c_uint),
        ("unknown",                       c_uint)
    ]
    _pack_ = 4


"""
R21 Structures
"""

class DWG_R21_FILE_HEADER_1ST(LittleEndianStructure):
    _fields_ = [
        ("signature",                   c_char*6),      # AC1021
        ("zero5",                       c_ubyte*5),     # 5 bytes of 0x00
        ("maintenance_version",         c_ubyte),       # maintenance release version
        ("unknown1",                    c_ubyte),       # 0x00, 0x01 or 0x03
        ("preview_address",             c_uint),        # address of 'image page' + page header size (0x20)
        ("app_version",                 c_ubyte),       # application version
        ("app_maintenance_version",     c_ubyte),       # application maintenance release version
        ("codepage",                    c_ushort),      # codepage
        ("unknown2",                    c_ubyte*3),
        ("security_flags",              c_uint),        # security flags, default is 0
                                                        # 0x01 = encrypted data (sections except Preview & SummaryInfo)
                                                        # 0x02 = encrypted properties (for Preview & SummaryInfo)
                                                        # 0x10 = sign data
                                                        # 0x20 = add timestamp
        ("unknown3",                    c_uint),
        ("summary_info_address",        c_uint),        # address of 'summary info page' + page header size (0x20)
        ("vba_project_address",         c_uint),        # 0 if not present
        ("unknown4",                    c_uint),        # 0x00000080
        ("app_info_address",            c_uint),        # NULL
        ("remaining_area",              c_ubyte*80)     # unknown
    ]
    _pack_ = 1

class DWG_R21_FILE_HEADER_2ND_HEAD(LittleEndianStructure):
    _fields_ = [
        ("crc",                         c_uint64),
        ("key",                         c_uint64),      # unknown
        ("compressed_data_crc",         c_uint64),
        ("compressed_size",             c_int),         # if the value is negative,
                                                        # data is not compressed.
        ("length2",                     c_int),         # unknown
    ]
    _pack_ = 4

class DWG_R21_FILE_HEADER_2ND_BODY(LittleEndianStructure):
    _fields_ = [
        ("header_size",                   c_uint64),    # normally 0x70
        ("file_size",                     c_uint64),
        ("pages_map_crc_compressed",      c_uint64),
        ("pages_map_correction_factor",   c_uint64),    #
        ("pages_map_crc_seed",            c_uint64),
        ("pages_map2_offset",             c_uint64),    # relative to data page map 1, add 0x480 to get stream position
        ("pages_map2_id",                 c_uint64),
        ("pages_map_offset",              c_uint64),    # relative to data page map 1, add 0x480 to get stream position
        ("pages_map_id",                  c_uint64),
        ("header2_offset",                c_uint64),    # relative to page map 1, add 0x480 to get stream position
        ("pages_map_size_compressed",     c_uint64),
        ("pages_map_size_uncompressed",   c_uint64),
        ("pages_amount",                  c_uint64),
        ("pages_max_id",                  c_uint64),
        ("unknown1",                      c_uint64),    # normally 0x20
        ("unknown2",                      c_uint64),    # normally 0x40
        ("pages_map_crc_uncompressed",    c_uint64),
        ("unknown3",                      c_uint64),    # normally 0xF800
        ("unknown4",                      c_uint64),    # normally 4
        ("unknown5",                      c_uint64),    # normally 1
        ("sections_amount",               c_uint64),    # number of sections + 1
        ("sections_map_crc_uncompressed", c_uint64),
        ("sections_map_size_compressed",  c_uint64),
        ("sections_map2_id",              c_uint64),
        ("sections_map_id",               c_uint64),
        ("sections_map_size_uncompressed",c_uint64),
        ("sections_map_crc_compressed",   c_uint64),
        ("sections_map_correction_factor",c_uint64),
        ("sections_map_crc_seed",         c_uint64),
        ("stream_version",                c_uint64),    # normally 0x60100
        ("crc_seed",                      c_uint64),
        ("crc_seed_encoded",              c_uint64),
        ("random_seed",                   c_uint64),
        ("header_crc",                    c_uint64)     # the seed is zero.
    ]
    _pack_ = 8

class DWG_R21_FILE_HEADER_2ND_TAIL(LittleEndianStructure):
    _fields_ = [
        ("normal_crc",                   c_uint64),
        ("mirrored_crc",                 c_uint64),
        ("random_value1",                c_uint64),
        ("random_value2",                c_uint64),
        ("encoded_rc_seed",              c_uint64)
    ]
    _pack_ = 8

class DWG_R21_SECTION_ENTRY(LittleEndianStructure):
    _fields_ = [
        ("size",                         c_uint64),     # total decompressed size
        ("max_size",                     c_uint64),
        ("encrypted",                    c_uint64),     # 0 or 1 or 2
        ("hash_code",                    c_uint64),     # one of pre-defined codes
        ("name_length",                  c_uint64),
        ("unknown",                      c_uint64),
        ("encoded",                      c_uint64),     # 0 or 1 or 4
        ("page_count",                   c_uint64)
    ]
    _pack_ = 8

class DWG_R21_SECTION_ENTRY_PAGE_INFO(LittleEndianStructure):
    _fields_ = [
        ("offset",                       c_uint64),     # relative address in the section data
        ("size",                         c_uint64),
        ("id",                           c_uint64),
        ("size_uncompressed",            c_uint64),
        ("size_compressed",              c_uint64),
        ("checksum",                     c_uint64),
        ("crc",                          c_uint64)
    ]
    _pack_ = 8

