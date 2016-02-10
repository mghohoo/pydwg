# -*- coding: utf-8 -*-

"""@package pydwg

    * Description
        DWGFormatR21 - R21 (AutoCAD 2007) file format handler
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

import ctypes
from .dwg_common import *
from .dwg_utils import *
from .dwg_bit_codes import *
from .dwg_report import *
from .dwg_section_decoder import *
from .dwg_format_base import DWGFormatBase


class DWGFormatR21(DWGFormatBase):
    """DWGFormatR21 class
    """

    def __init__(self, buf, size, name="", mode=DWGParsingMode.FULL):
        """The constructor"""
        super(DWGFormatR21, self).__init__()

        self.mode = mode
        self.file_name = name
        self.file_buf = buf
        self.file_size = size
        self.utils = DWGUtils(self.report)
        self.decoder = DWGSectionDecoder(DWGVersion.R21, self.report)

        self.logger = logging.getLogger(__name__)
        return

    def parse(self):
        """Parse a DWG file

        Returns:
            True or False
        """
        offset = 0

        # File headers
        self.dwg_file_header_2nd = self.get_file_header(offset)
        if self.dwg_file_header_2nd.get('body') is None:
            msg = "2nd file header is invalid."
            self.logger.debug("{}(): {}".format(GET_MY_NAME(), msg))
            self.report.add(DWGVInfo(DWGVType.SYNTAX_ERROR, -1, -1, msg))
            return False

        '''
        =============================================================
        System sections: page map, section map
        =============================================================
        '''
        # page map
        self.dwg_page_map = self.get_page_map()

        # section map
        id = self.dwg_file_header_2nd.get('body').get('sections_map_id')
        page_entry = self.find_page_entry(id)
        if page_entry is None:
            msg = "Cannot find the section map."
            self.logger.debug("{}(): {}".format(GET_MY_NAME(), msg))
            self.report.add(DWGVInfo(DWGVType.SYNTAX_ERROR, -1, -1, msg))
            return False

        address = page_entry.get('address')
        self.dwg_section_map = self.get_section_map(address)

        # build section entry list
        # if self.build_section_entry_list() == 0:
        #     return False

        # for debugging
        # self.save_section_data()
        # return

        '''
        =============================================================
        Data sections
        =============================================================
            - AcDb:Security         : encryption settings
            - AcDb:SummaryInfo      : document properties
            - AcDb:AppInfo          : application info.
            - AcDb:AppInfoHistory   : application info.
            - AcDb:AuxHeader        : document properties (additional)
            - AcDb:Preview          : preview images
            - AcDb:Headers          : header variables (base handle values)
            - AcDb:FileDepList      : file dependencies
            - AcDb:Classes          : custom classes
            - AcDb:Handles          : object map
            - AcDb:AcDbObjects      : object data stream
        =============================================================
        '''
        '''-------------------------------------------------------'''
        security_flags = self.dwg_file_header_1st.get('body').get('security_flags')
        if security_flags > 0:
            section = self.get_section_data_by_hashcode(DWGSectionHashCode.SECURITY)
            if section is not None:
                self.dwg_filedeplist = self.decoder.security(section)

        '''-------------------------------------------------------'''
        app_version = self.dwg_file_header_1st.get('body').get('app_version')

        section = self.get_section_data_by_hashcode(DWGSectionHashCode.APPINFO)
        if section is not None:
            self.dwg_appinfo = self.decoder.appinfo(section, app_version)

        section = self.get_section_data_by_hashcode(DWGSectionHashCode.APPINFOHISTORY)
        if section is not None:
            self.dwg_appinfohistory = self.decoder.appinfohistory(section, app_version)

        '''-------------------------------------------------------'''
        section = self.get_section_data_by_hashcode(DWGSectionHashCode.AUXHEADER)
        if section is not None:
            self.dwg_auxheader = self.decoder.auxheader(section)

        '''-------------------------------------------------------'''
        section = self.get_section_data_by_hashcode(DWGSectionHashCode.PREVIEW)
        if section is not None:
            self.dwg_preview = self.decoder.preview(section)

        '''-------------------------------------------------------'''
        section = self.get_section_data_by_hashcode(DWGSectionHashCode.SUMMARYINFO)
        if section is not None:
            self.dwg_summaryinfo = self.decoder.summaryinfo(section, DWGEncoding.UTF16LE.value)

        '''-------------------------------------------------------'''
        section = self.get_section_data_by_hashcode(DWGSectionHashCode.HEADER)
        if section is not None:
            self.dwg_header = self.decoder.header(section)

        '''-------------------------------------------------------'''
        section = self.get_section_data_by_hashcode(DWGSectionHashCode.FILEDEPLIST)
        if section is not None:
            self.dwg_filedeplist = self.decoder.filedeplist(section, DWGEncoding.UTF16LE.value)

        '''-------------------------------------------------------'''
        # Get defined classes from AcDb:Classes
        section = self.get_section_data_by_hashcode(DWGSectionHashCode.CLASSES)
        if section is not None:
            self.dwg_classes = self.decoder.classes(section)
            self.decoder.object.set_classes(self.dwg_classes.get('classes'))

        '''-------------------------------------------------------'''
        # Build the object map for locating objects using AcDb:Handles
        section = self.get_section_data_by_hashcode(DWGSectionHashCode.HANDLES)
        if section is not None:
            self.dwg_object_map = self.build_object_map(section)

        '''-------------------------------------------------------'''
        if self.mode == DWGParsingMode.METADATA or \
           self.mode == DWGParsingMode.VALIDATION:
            return True

        '''-------------------------------------------------------'''
        # Get all objects with object map from AcDb:AcDbObjects
        section = self.get_section_data_by_hashcode(DWGSectionHashCode.ACDBOBJECTS)
        if section is not None:
            self.dwg_objects = self.decoder.objects(section, self.dwg_object_map)

        # Get all objects by carving
        # unfortunately, there is little chance to have unused area in AcDbObjects data stream
        return True

    def save_section_data(self):
        """Save all section data for debugging
        """
        for section_meta in self.dwg_section_map.get('map'):
            section_name = section_meta.get('name')
            if section_name == "":
                continue

            section = self.get_section_data_by_hashcode(section_meta.get('hash_code'))
            if section is not None:
                section_name = section_name.split(':')[1]
                self.utils.save_data_to_file(
                        self.file_name + '.{}.bin'.format(section_name.lower()),
                        section.get('data')
                )
        return

    def build_object_map(self, section):
        """Build the object map table

        Args:
            section (dict): {'meta', 'data'}

        Returns:
            List of {'handle', 'offset'}
        """
        object_map = []

        data = section.get('data')
        if len(data) == 0:
            return object_map

        bc = DWGBitCodes(data, len(data))

        while 1:
            section_size = bc.read_rs(endian='big')
            if section_size == 2:
                # the last empty (except the CRC) section
                break

            if bc.pos_byte == bc.size:
                break

            last_handle = 0
            last_offset = 0
            processed = 0
            pos_start = bc.pos_byte

            while processed < section_size-2:  # 2 bytes for section_size
                last_handle   += bc.read_mc()
                last_offset += bc.read_mc()

                # Validate each object map item
                if last_offset < 0 or self.file_size < last_offset:
                    msg = "[{}] Found an abnormal address value at {}th entry.".format(
                            DWGSectionName.HANDLES.value, len(object_map))
                    self.logger.debug("{}(): {}".format(GET_MY_NAME(), msg))
                    self.report.add(DWGVInfo(DWGVType.CORRUPTED, -1, -1, msg))

                object_map.append({'handle': last_handle,
                                   'offset': last_offset})  # offsets into AcDb:AcDbObjects section
                processed = bc.pos_byte - pos_start

            crc = bc.read_rs(endian='big')

        # Validate CRC value

        self.logger.info("{}(): {} items in object map.".format(GET_MY_NAME(), len(object_map)))
        return object_map

    def build_section_entry_list(self):
        """Build the section entry list (for printing section info.)

            self.dwg_section_entry_list = [section entry dict.]

                    section entry dict. {
                        name    : section name
                        pages   : list of page
                    }

        Returns:
            Length of self.dwg_section_entry_list
        """
        for section in self.dwg_section_map.get('map'):
            section_name = section.get('name')
            if section_name == "":
                continue

            # self.utils.print_dict(section, "Section Map")

            # '''======================================================'''
            # rs_method = section.get('encoded')
            # total_decompressed_size = section.get('size')
            # data = bytearray(total_decompressed_size)
            # '''======================================================'''

            pages = []
            for idx in range(section.get('page_count')):
                page = self.find_page_entry(section.get('pages')[idx].get('id'))
                if page is None:
                    continue
                pages.append(page)
                # self.utils.print_dict(page, "Page Info", level=1)

                # '''======================================================'''
                # # Get the address of data
                # address = page.get('address')
                #
                # # Get related variables
                # size_compressed   = section.get('pages')[idx].get('size_compressed')
                # size_uncompressed = section.get('pages')[idx].get('size_uncompressed')
                # offset = section.get('pages')[idx].get('offset')
                #
                # # Read (+ decode & decompress) the data page
                # temp = self.read_data_page(
                #         address,
                #         size_compressed, size_uncompressed,
                #         page.get('size'),
                #         rs_method
                # )
                #
                # size = len(temp)
                # data[offset:offset+size_uncompressed] = temp

            # Print hex data
            # self.utils.print_dict(section, "Section Map")
            # self.utils.print_hex_bytes(data)
            '''======================================================'''

            entry = OrderedDict()
            entry['name'] = section_name
            entry['pages'] = pages
            self.dwg_section_entry_list.append(entry)

        return len(self.dwg_section_entry_list)

    def get_section_data_by_hashcode(self, hash_code):
        """Get a section data

        Args:
            hash_code (DWGSectionHashCode): The section hashcode to get data

        Returns:
            Section data (dict) or None
            {
                meta   : section name & pages
                data   : decompressed data stream
            }
        """
        section_meta = None
        for item in self.dwg_section_map.get('map'):
            if item.get('hash_code') == hash_code:
                section_meta = item
                break

        if section_meta is None:
            msg = "[{}] Do not exist the section code '{}'.".format("section map", hash_code)
            self.logger.info("{}(): {}".format(GET_MY_NAME(), msg))
            return None

        return self.get_section_data(section_meta)

    def get_section_data(self, section):
        """Get a section data

        Args:
            section (dict): A section meta stored in the section map

        Returns:
            Result data (dict)
            {
                meta : metadata on this section
                data : decompressed (+ decoded) data stream
            }
        """
        self.logger.info("{}(): Get data of the section {}.".format(
                GET_MY_NAME(),
                section.get('name'))
        )

        # 0 (if not encrypted), 2 (meaning unknown)
        if section.get('encrypted') == 1:
            msg = "[{}] Data is encrypted.".format(section.get('name'))
            self.logger.info("{}(): {}".format(GET_MY_NAME(), msg))
            return None

        '''======================================================'''
        rs_method = section.get('encoded')
        total_decompressed_size = section.get('size')
        data = bytearray(total_decompressed_size)
        '''======================================================'''

        pages = []
        for idx in range(section.get('page_count')):
            page = self.find_page_entry(section.get('pages')[idx].get('id'))
            if page is None:
                continue
            pages.append(page)

            '''======================================================'''
            # Get the address of data
            address = page.get('address')

            # Get related variables
            size_compressed   = section.get('pages')[idx].get('size_compressed')
            size_uncompressed = section.get('pages')[idx].get('size_uncompressed')
            offset = section.get('pages')[idx].get('offset')

            # Read (+ decode & decompress) the data page
            temp = self.read_data_page(
                    address,
                    size_compressed, size_uncompressed,
                    page.get('size'),
                    rs_method
            )

            data[offset:offset+size_uncompressed] = temp

        # Print hex data
        # self.utils.print_dict(section, "Section Map")
        # self.utils.print_hex_bytes(data)
        '''======================================================'''

        meta = OrderedDict()
        meta['name'] = section.get('name')
        meta['pages'] = pages

        if len(data) != total_decompressed_size:
            self.logger.debug("{}(): decompressed_size mis-matches.".format(GET_MY_NAME()))
            msg = "[{}] decompressed_size mis-matches.".format(section.get('name'))
            self.report.add(DWGVInfo(DWGVType.CORRUPTED, -1, -1, msg))

        msg = "Totally {} bytes.".format(len(data))
        self.logger.info("{}(): {}".format(GET_MY_NAME(), msg))

        return {'meta': meta,
                'data': bytes(data)}

    def get_section_map(self, address):
        """Parse the section map

        Args:
            address (int): The start address from beginning of the file

        Return:
            Result dict
            {
                header  (None in R21)
                map     (list of dict)
            }
        """
        offset = address

        self.logger.info("{}(): Get a section map.".format(GET_MY_NAME()))

        # Get related variables
        size_compressed   = self.dwg_file_header_2nd.get('body').get('sections_map_size_compressed')
        size_uncompressed = self.dwg_file_header_2nd.get('body').get('sections_map_size_uncompressed')
        correction_factor = self.dwg_file_header_2nd.get('body').get('sections_map_correction_factor')

        # Read (+ decode & decompress) the system page
        data = self.read_system_page(
                offset,
                size_compressed, size_uncompressed, correction_factor
        )

        # Parse the system map structure
        section_map = []
        total_size = len(data)
        offset = 0
        idx = 0

        while idx < total_size:
            # Get a section entry
            entry = self.utils.static_cast(data[idx:idx+sizeof(DWG_R21_SECTION_ENTRY)],
                                           DWG_R21_SECTION_ENTRY)
            entry = self.utils.get_dict_from_ctypes_struct(entry)

            # Validate DWG_R21_SECTION_ENTRY
            if self.validate_DWG_R21_SECTION_ENTRY(entry, offset, total_size) is False:
                msg = "Abnormal 'validate_DWG_R21_SECTION_ENTRY' structure."
                self.logger.debug("{}(): {}".format(GET_MY_NAME(), msg))
                break

            idx += sizeof(DWG_R21_SECTION_ENTRY)

            # Get the section name (UTF-16LE)
            entry['name'] = ""
            if entry.get('name_length') > 0:
                length = entry.get('name_length')  # UTF-16LE
                value = self.utils.rstrip_null(data[idx:idx+length], True)
                entry['name'] = value.decode('UTF-16LE', 'ignore')
                idx += length
                # if not (data[idx] == 0x00 and data[idx+1] == 0x00):
                #     print("[Abnormal] section name should be terminated 0x0000.")
                # idx += 2

            # self.utils.print_dict(entry, "Section Map")

            # Get pages related to this section
            entry['pages'] = []
            for pc in range(entry.get('page_count')):
                page = self.utils.static_cast(data[idx:idx+sizeof(DWG_R21_SECTION_ENTRY_PAGE_INFO)],
                                              DWG_R21_SECTION_ENTRY_PAGE_INFO)
                page = self.utils.get_dict_from_ctypes_struct(page)

                # Validate DWG_R21_SECTION_ENTRY_PAGE_INFO
                if self.validate_DWG_R21_SECTION_ENTRY_PAGE_INFO(page, idx, sizeof(DWG_R21_SECTION_ENTRY_PAGE_INFO)) is False:
                    msg = "Abnormal 'DWG_R21_SECTION_ENTRY_PAGE_INFO' structure."
                    self.logger.debug("{}(): {}".format(GET_MY_NAME(), msg))
                    break

                idx += sizeof(DWG_R21_SECTION_ENTRY_PAGE_INFO)
                entry['pages'].append(page)

                # self.utils.print_dict(page, "Page Info.", 1)

            section_map.append(entry)

        self.logger.info("{}(): {} items in section map.".format(GET_MY_NAME(), len(section_map)))

        return {'header': None,
                'map':    section_map}

    def find_page_entry(self, id):
        page_map = self.dwg_page_map['map']
        for entry in page_map:
            if entry['id'] == id:
                return entry
        return None

    def read_data_page(self, address, size_compressed, size_uncompressed, page_size, rs_method):
        """Read the data page(s)

        Args:
            address (int): The start address from the beginning of the file
            size_compressed (int)
            size_uncompressed (int)
            page_size (int)
            rs_method (int): RS encoding method - 4 (interleaved), 1 (non-interleaved)

        Returns:
            data (bytes)
        """
        def get_values(data_size_compressed):
            """Get the block count based on data_size

                - Open Design Specification for .dwg files v5.3 - page 47

            Args:
                data_size_compressed (int): The compressed data size (not Padded)

            Returns:
                rs_block_count (int)
            """
            crc_block_size = 8
            page_align_size = 0x20
            reed_solomon_data_block_size = 251
            reed_solomon_codeword_size = 255

            # # (1) repeat_count(1) = rs_pre_encoded_size / data_size_compressed (Padded)
            # data_size_compressed_padded = (data_size_compressed + (crc_block_size - 1)) & -crc_block_size
            # rs_pre_encoded_size = data_size_compressed_padded

            # (2) rs_pre_encoded_size = rs_block_count * reed_solomon_data_block_size
            rs_block_count = (data_size_compressed + (reed_solomon_data_block_size - 1)) / reed_solomon_data_block_size
            rs_block_count = int(rs_block_count)

            return rs_block_count

        # Get the block count for reading data (compressed -> padded(0x8) -> RS-encoded -> padded(0x20))
        block_count = get_values(size_compressed)

        # Read data
        page_size = max(page_size, 251 * block_count)
        data = self.file_buf[address:address+page_size]

        # Decode RS-encoded data
        data = self.utils.decode_reed_solomon(data, 251, block_count, rs_method)

        # Print decoded data
        # self.utils.print_hex_bytes(data, 32)

        if size_compressed < size_uncompressed:
            data = self.utils.decompress_r21(
                    data[0:size_compressed],
                    size_uncompressed
            )
        else:  # not compressed
            data = data[0:size_uncompressed]

        return data

    def read_system_page(self, address, size_compressed, size_uncompressed, correction_factor):
        """Read the system page (only 1 page)

        Args:
            address (int): The start address from the beginning of the file
            size_compressed (int)
            size_uncompressed (int)
            correction_factor (int)

        Returns:
            data (bytes)
        """
        def get_values(data_size_compressed, repeat_count):
            """Get the system page size & block count based on data_size

                - Open Design Specification for .dwg files v5.3 - page 47

            Args:
                data_size_compressed (int): The compressed data size (not Padded)
                repeat_count (int): The repeat count for RS encoding

            Returns:
                page_size (int), rs_block_count (int)
            """
            crc_block_size = 8
            page_align_size = 0x20
            reed_solomon_data_block_size = 239
            reed_solomon_codeword_size = 255

            # (1) repeat_count = rs_pre_encoded_size / data_size_compressed (Padded)
            data_size_compressed_padded = (data_size_compressed + (crc_block_size - 1)) & -crc_block_size
            rs_pre_encoded_size = data_size_compressed_padded * repeat_count

            # (2) rs_pre_encoded_size = rs_block_count * reed_solomon_data_block_size
            rs_block_count = (rs_pre_encoded_size + (reed_solomon_data_block_size - 1)) / reed_solomon_data_block_size
            rs_block_count = int(rs_block_count)

            # (3) rs_block_count = page_size / reed_solomon_codeword_size
            page_size = (rs_block_count * reed_solomon_codeword_size + (page_align_size - 1)) & -page_align_size

            return page_size, rs_block_count

        # Get the page size value for reading data (compressed -> padded(0x8) -> RS-encoded -> padded(0x20))
        page_size, block_count = get_values(size_compressed, correction_factor)

        # Read data
        data = self.file_buf[address:address+page_size]

        # Decode RS-encoded data
        data = self.utils.decode_reed_solomon(data, 239, block_count)

        if size_compressed < size_uncompressed:
            data = self.utils.decompress_r21(
                    data[0:size_compressed],
                    size_uncompressed
            )
        else:  # not compressed
            data = data[0:size_uncompressed]

        return data

    def get_page_map(self):
        """Parse the page map

        Returns:
            Result dict
            {
                header  (None in R21)
                map     (list of dict)
            }
        """
        # Calculate the start offset
        offset  = self.dwg_file_header_2nd.get('body').get('pages_map_offset')
        offset += 0x480  # skip the file header

        # Get related variables
        size_compressed   = self.dwg_file_header_2nd.get('body').get('pages_map_size_compressed')
        size_uncompressed = self.dwg_file_header_2nd.get('body').get('pages_map_size_uncompressed')
        correction_factor = self.dwg_file_header_2nd.get('body').get('pages_map_correction_factor')

        # Read (+ decode & decompress) the system page
        data = self.read_system_page(
                offset,
                size_compressed, size_uncompressed, correction_factor
        )

        # Parse the page map structure
        # page_map = [None] * (self.dwg_file_header_2nd.get('body').get('pages_max_id') + 1)
        page_map = []
        total_size = len(data)
        address = 0x480
        idx = 0
        msg_bak = ""

        while idx < total_size:
            entry = OrderedDict()
            entry['size']    = struct.unpack('<q', data[idx+ 0 : idx+ 8])[0]
            entry['id']      = struct.unpack('<q', data[idx+ 8 : idx+16])[0]
            entry['address'] = address
            address += entry['size']
            idx += 16

            if entry['id'] < 0:
                a = 1  # what happened?

            id = entry['id'] if entry['id'] > 0 else -entry['id']
            if id <= 0 or self.dwg_file_header_2nd.get('body').get('pages_max_id') < id:
                msg = "[{}] Found an abnormal ID {} at {}th entry.".format("page map", id, len(page_map))
                self.logger.debug("{}(): {}".format(GET_MY_NAME(), msg))
                self.report.add(DWGVInfo(DWGVType.CORRUPTED, -1, -1, msg))
                break

            size = entry['size']
            if size <= 0 or self.file_size <= entry['address'] + size:
                msg = "[{}] Found an abnormal Size {} at {}th entry.".format("page map", size, len(page_map))
                self.logger.debug("{}(): {}".format(GET_MY_NAME(), msg))
                self.report.add(DWGVInfo(DWGVType.CORRUPTED, -1, -1, msg))
                break

            if entry['address'] <= 0 or self.file_size <= entry['address']:
                msg = "[{}] Found an abnormal Address {} at {}th entry.".format("page map", entry['address'], len(page_map))
                self.logger.debug("{}(): {}".format(GET_MY_NAME(), msg))
                self.report.add(DWGVInfo(DWGVType.CORRUPTED, -1, -1, msg))
                break

            # page_map[id] = entry  # for accessing an entry directly through ID value
            page_map.append(entry)

        if self.dwg_file_header_2nd.get('body').get('pages_max_id') < len(page_map):
            msg = "[{}] page entry count mis-matches.".format("page map")
            self.logger.debug("{}(): {}".format(GET_MY_NAME(), msg))
            self.report.add(DWGVInfo(DWGVType.CORRUPTED, -1, -1, msg))

        self.logger.info("{}(): {} items in page map.".format(GET_MY_NAME(), len(page_map)))

        return {'header': None,
                'map':    page_map}

    def get_file_header(self, offset):
        """Parse the file header

        Returns:
            Result dict --> 2nd file header
            {
                offset
                size
                head (DWG_R21_FILE_HEADER_2ND_HEAD)
                body (DWG_R21_FILE_HEADER_2ND_BODY)
            }
        """
        self.logger.info("{}(): Get the 1st and 2nd file headers.".format(GET_MY_NAME()))

        d = dict()
        d['offset'] = offset
        d['size'] = sizeof(DWG_R21_FILE_HEADER_1ST)
        d['body'] = self.utils.static_cast(self.file_buf[offset:offset+sizeof(DWG_R21_FILE_HEADER_1ST)],
                                           DWG_R21_FILE_HEADER_1ST)
        d['body'] = self.utils.get_dict_from_ctypes_struct(d['body'])

        # Validate DWG_R21_FILE_HEADER_1ST
        if self.validate_DWG_R21_FILE_HEADER_1ST(d.get('body'), d['offset'], d['size']) is False:
            msg = "Abnormal 'DWG_R21_FILE_HEADER_1ST' structure."
            self.logger.debug("{}(): {}".format(GET_MY_NAME(), msg))
            return None

        # Set the 1st file header
        self.dwg_file_header_1st = d

        # Get data of 2nd file header
        offset = 0x80
        data = self.file_buf[offset:offset+0x3D8]
        data = self.utils.decode_reed_solomon(data, k=239, block_count=3)

        d = dict()
        d['offset'] = 0x80
        d['size'] = 0x400

        offset = 0
        d['head'] = self.utils.static_cast(data[offset:offset+sizeof(DWG_R21_FILE_HEADER_2ND_HEAD)],
                                           DWG_R21_FILE_HEADER_2ND_HEAD)
        d['head'] = self.utils.get_dict_from_ctypes_struct(d['head'])

        # Validate DWG_R21_FILE_HEADER_2ND_HEAD
        if self.validate_DWG_R21_FILE_HEADER_2ND_HEAD(d.get('head'), d['offset'], d['size']) is False:
            msg = "Abnormal 'validate_DWG_R21_FILE_HEADER_2ND_HEAD' structure."
            self.logger.debug("{}(): {}".format(GET_MY_NAME(), msg))
            return None

        offset = 0x20
        length = d.get('head').get('compressed_size')

        if length < 0:
            length = -length
            data = data[offset:offset+length]
            self.logger.debug("{}(): 2nd file header is not compressed.".format(GET_MY_NAME()))
        elif length > 0:
            data = self.utils.decompress_r21(data[offset:offset+length], 0x110)
        else:
            self.logger.debug("{}(): 2nd file header is not compressed.".format(GET_MY_NAME()))
            return d

        if length < sizeof(DWG_R21_FILE_HEADER_2ND_HEAD):
            self.logger.debug("{}(): compressed_size is invalid for the 2nd file header.".format(GET_MY_NAME()))

        d['body'] = self.utils.static_cast(data[0:sizeof(DWG_R21_FILE_HEADER_2ND_BODY)],
                                           DWG_R21_FILE_HEADER_2ND_BODY)
        d['body'] = self.utils.get_dict_from_ctypes_struct(d['body'])

        # Validate DWG_R21_FILE_HEADER_2ND_BODY
        if self.validate_DWG_R21_FILE_HEADER_2ND_BODY(d.get('body'), offset, length) is False:
            msg = "Abnormal 'validate_DWG_R21_FILE_HEADER_2ND_BODY' structure."
            self.logger.debug("{}(): {}".format(GET_MY_NAME(), msg))
            return None

        # Last 0x28 bytes consists of check data (5 64-bits CRC?)
        offset = 0x80 + 0x3D8
        length = sizeof(DWG_R21_FILE_HEADER_2ND_TAIL)
        data = self.file_buf[offset:offset+length]
        d['tail'] = self.utils.static_cast(data[0:0+sizeof(DWG_R21_FILE_HEADER_2ND_TAIL)],
                                           DWG_R21_FILE_HEADER_2ND_TAIL)
        d['tail'] = self.utils.get_dict_from_ctypes_struct(d['tail'])

        # Validate DWG_R21_FILE_HEADER_2ND_TAIL
        if self.validate_DWG_R21_FILE_HEADER_2ND_TAIL(d.get('tail'), offset, length) is False:
            msg = "Abnormal 'DWG_R21_FILE_HEADER_2ND_TAIL' structure."
            self.logger.debug("{}(): {}".format(GET_MY_NAME(), msg))
            return None

        # # CRC check
        # data = data[:-4] + (b'\x00' * 4)
        # v = self.check_crc(data, header.get('encrypted').get('crc32'))
        # if v is False:
        #     print("[ALERT] Abnormal point - get_file_header - CRC check failed")
        return d

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

    def check_crc(self, data, saved_crc):
        """Check the CRC value

        Args:
            data (bytes)
            saved_crc (int)

        Returns:
            True or False
        """
        calculated_crc = self.utils.crc32(data, 0)
        if calculated_crc == saved_crc:
            return True
        return False

    def validate_DWG_R21_FILE_HEADER_1ST(self, data, offset=-1, size=-1):
        """Validate the internal structure

        Args:
            data (dict): DWG_R21_FILE_HEADER_1ST
            offset (int)
            size (int)

        Returns:
            True or False
        """

        if self.file_size <= data.get('preview_address'):
            msg = "[{}] preview_address is invalid.".format("1st file header")
            self.report.add(DWGVInfo(DWGVType.SYNTAX_ERROR, offset, size, msg))
            return False

        if self.file_size <= data.get('summary_info_address'):
            msg = "[{}] summary_info_address is invalid.".format("1st file header")
            self.report.add(DWGVInfo(DWGVType.SYNTAX_ERROR, offset, size, msg))
            return False

        if self.file_size <= data.get('vba_project_address'):
            msg = "[{}] vba_project_address is invalid.".format("1st file header")
            self.report.add(DWGVInfo(DWGVType.SYNTAX_ERROR, offset, size, msg))
            return False

        if self.file_size <= data.get('app_info_address'):
            msg = "[{}] vba_project_address is invalid.".format("1st file header")
            self.report.add(DWGVInfo(DWGVType.SYNTAX_ERROR, offset, size, msg))
            return False

        return True

    def validate_DWG_R21_FILE_HEADER_2ND_HEAD(self, data, offset=-1, size=-1):
        """Validate the internal structure

        Args:
            data (dict): DWG_R21_FILE_HEADER_2ND_HEAD
            offset (int)
            size (int)

        Returns:
            True or False
        """

        data_size = data.get('compressed_size')
        if data_size < 0:
            data_size = -data_size

        if self.file_size-0x20 <= data_size:
            msg = "[{}] compressed_size is invalid.".format("2nd file header - head")
            self.report.add(DWGVInfo(DWGVType.SYNTAX_ERROR, offset, size, msg))
            return False

        return True

    def validate_DWG_R21_FILE_HEADER_2ND_BODY(self, data, offset=-1, size=-1):
        """Validate the internal structure

        Args:
            data (dict): DWG_R21_FILE_HEADER_2ND_BODY
            offset (int)
            size (int)

        Returns:
            True or False
        """

        if data.get('header_size') != 0x70:
            msg = "[{}] header_size is invalid.".format("2nd file header - body")
            self.report.add(DWGVInfo(DWGVType.SYNTAX_ERROR, offset, size, msg))
            return False

        if self.file_size <= data.get('pages_map2_offset') + 0x480:
            msg = "[{}] pages_map2_offset is invalid.".format("2nd file header - body")
            self.report.add(DWGVInfo(DWGVType.SYNTAX_ERROR, offset, size, msg))
            return False

        if self.file_size <= data.get('pages_map_offset') + 0x480:
            msg = "[{}] pages_map_offset is invalid.".format("2nd file header - body")
            self.report.add(DWGVInfo(DWGVType.SYNTAX_ERROR, offset, size, msg))
            return False

        return True

    def validate_DWG_R21_FILE_HEADER_2ND_TAIL(self, data, offset=-1, size=-1):
        """Validate the internal structure

        Args:
            data (dict): DWG_R21_FILE_HEADER_2ND_TAIL
            offset (int)
            size (int)

        Returns:
            True or False
        """
        return True

    def validate_DWG_R21_SECTION_ENTRY(self, data, offset=-1, size=-1):
        """Validate the internal structure

        Args:
            data (dict): DWG_R21_SECTION_ENTRY
            offset (int)
            size (int)

        Returns:
            True or False
        """
        # if self.file_size <= data.get('size'):
        #     msg = "[{}] decompressed size is invalid.".format("an entry of section map")
        #     self.report.add(DWGVInfo(DWGVType.SYNTAX_ERROR, offset, size, msg))
        #     return False

        if data.get('encrypted') in [0, 1, 2] is False:
            msg = "[{}] encrypted flag is invalid.".format("an entry of section map")
            self.report.add(DWGVInfo(DWGVType.SYNTAX_ERROR, offset, size, msg))
            return False

        if data.get('encoded') in [0, 1, 4] is False:
            msg = "[{}] encoded flag is invalid.".format("an entry of section map")
            self.report.add(DWGVInfo(DWGVType.SYNTAX_ERROR, offset, size, msg))
            return False

        return True

    def validate_DWG_R21_SECTION_ENTRY_PAGE_INFO(self, data, offset=-1, size=-1):
        """Validate the internal structure

        Args:
            data (dict): DWG_R21_SECTION_ENTRY_PAGE_INFO
            offset (int)
            size (int)

        Returns:
            True or False
        """
        page_entry = self.find_page_entry(data.get('id'))
        if page_entry is None:
            msg = "[{}] page ID is invalid.".format("an entry of section map")
            self.report.add(DWGVInfo(DWGVType.SYNTAX_ERROR, offset, size, msg))
            return False

        if self.file_size <= data.get('size_compressed'):
            msg = "[{}] compressed size is invalid.".format("an entry of section map")
            self.report.add(DWGVInfo(DWGVType.SYNTAX_ERROR, offset, size, msg))
            return False

        return True

