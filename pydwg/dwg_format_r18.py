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

import ctypes
from .dwg_common import *
from .dwg_utils import *
from .dwg_bit_codes import *
from .dwg_report import *
from .dwg_section_decoder import *
from .dwg_format_base import DWGFormatBase


class DWGFormatR18(DWGFormatBase):
    """DWGFormatR18 class
    """

    def __init__(self, buf, size, name="", mode=DWGParsingMode.FULL):
        """The constructor"""
        super(DWGFormatR18, self).__init__()

        self.mode = mode
        self.file_name = name
        self.file_buf = buf
        self.file_size = size
        self.utils = DWGUtils(self.report)
        self.decoder = DWGSectionDecoder(DWGVersion.R18, self.report)

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
        # page map (for both system and data sections)
        offset = self.dwg_file_header_2nd.get('body').get('page_map_address')
        offset += 0x100  # skip the file header
        self.dwg_page_map = self.get_page_map(offset)

        # section map (= directory entries for data sections)
        id = self.dwg_file_header_2nd.get('body').get('section_map_id')
        page_entry = self.find_page_entry(id)
        if page_entry is None:
            msg = "Cannot find the section map."
            self.logger.debug("{}(): {}".format(GET_MY_NAME(), msg))
            self.report.add(DWGVInfo(DWGVType.SYNTAX_ERROR, -1, -1, msg))
            return False

        address = page_entry.get('address')
        self.dwg_section_map = self.get_section_map(address)
        # return False

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
            section = self.get_section_data_by_name(DWGSectionName.SECURITY)
            if section is not None:
                self.dwg_filedeplist = self.decoder.security(section)

        '''-------------------------------------------------------'''
        section = self.get_section_data_by_name(DWGSectionName.SUMMARYINFO)
        if section is not None:
            self.dwg_summaryinfo = self.decoder.summaryinfo(section, encoding=DWGEncoding.KOREAN.value)

        '''-------------------------------------------------------'''
        app_version = self.dwg_file_header_1st.get('body').get('app_version')

        section = self.get_section_data_by_name(DWGSectionName.APPINFO)
        if section is not None:
            self.dwg_appinfo = self.decoder.appinfo(section, app_version)

        section = self.get_section_data_by_name(DWGSectionName.APPINFOHISTORY)
        if section is not None:
            self.dwg_appinfohistory = self.decoder.appinfohistory(section, app_version)

        '''-------------------------------------------------------'''
        section = self.get_section_data_by_name(DWGSectionName.AUXHEADER)
        if section is not None:
            self.dwg_auxheader = self.decoder.auxheader(section)

        '''-------------------------------------------------------'''
        section = self.get_section_data_by_name(DWGSectionName.PREVIEW)
        if section is not None:
            self.dwg_preview = self.decoder.preview(section)

        '''-------------------------------------------------------'''
        section = self.get_section_data_by_name(DWGSectionName.HEADER)
        if section is not None:
            self.dwg_header = self.decoder.header(section)

        '''-------------------------------------------------------'''
        section = self.get_section_data_by_name(DWGSectionName.FILEDEPLIST)
        if section is not None:
            self.dwg_filedeplist = self.decoder.filedeplist(section)

        '''-------------------------------------------------------'''
        # Get defined classes from AcDb:Classes
        section = self.get_section_data_by_name(DWGSectionName.CLASSES)
        if section is not None:
            self.dwg_classes = self.decoder.classes(section)
            self.decoder.object.set_classes(self.dwg_classes.get('classes'))

        '''-------------------------------------------------------'''
        # Build the object map for locating objects using AcDb:Handles
        section = self.get_section_data_by_name(DWGSectionName.HANDLES)
        if section is not None:
            self.dwg_object_map = self.build_object_map(section)

        '''-------------------------------------------------------'''
        if self.mode == DWGParsingMode.METADATA or \
           self.mode == DWGParsingMode.VALIDATION:
            return True

        '''-------------------------------------------------------'''
        # Get all objects with object map from AcDb:AcDbObjects
        section = self.get_section_data_by_name(DWGSectionName.ACDBOBJECTS)
        if section is not None:
            self.dwg_objects = self.decoder.objects(section, self.dwg_object_map)

        # get all objects by carving
        # unfortunately, there is little chance to have unused area in AcDbObjects data stream

        '''-------------------------------------------------------'''
        # post-process
        # self.check_parsed_results()
        return True

    def save_section_data(self):
        """Save all section data for debugging
        """
        for section_meta in self.dwg_section_map.get('map'):
            section_name = section_meta.get('name')
            if section_name == "":
                continue

            section = self.get_section_data(section_meta)
            if section is not None:
                section_name = section_name.split(':')[1]
                self.utils.save_data_to_file(
                        self.file_name + '.{}.bin'.format(section_name.lower()),
                        section.get('data')
                )

    def check_parsed_results(self):
        f = open(self.file_name + '.result.txt', 'w')

        # print("PAGE MAP ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
        # f.write("\nPAGE MAP ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n")
        # obj_str = json.dumps(self.dwg_page_map, sort_keys=False, indent=4, ensure_ascii=False)
        # # print(obj_str)
        # f.write(obj_str)

        # check if there are empty spaces in compressed areas
        page_map = self.dwg_page_map.get('map')
        for idx in range(len(page_map)-1):
            if page_map[idx].get('address') + page_map[idx].get('size') != page_map[idx+1].get('address'):
                # print("[ALERT] Abnormal point: unused areas in a DWG file")
                f.write("[ALERT] Abnormal point: unused areas in a DWG file\n")

        # print("SECTION MAP ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
        # f.write("\nSECTION MAP ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n")
        # # for item in self.dwg_section_map.get('map'):
        # #     obj_str = json.dumps(item, sort_keys=False, indent=4, ensure_ascii=False)
        # #     print(obj_str)
        # obj_str = json.dumps(self.dwg_section_map, sort_keys=False, indent=4, ensure_ascii=False)
        # # print(obj_str)
        # f.write(obj_str)

        print("SECTION ENTRIES ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
        f.write("\nSECTION ENTRIES ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n")
        for section in self.dwg_section_entry_list:
            # print("[SECTION] {0}".format(section.get('name')))
            f.write("[SECTION] {0}\n".format(section.get('name')))
            for idx in range(len(section.get('headers'))):
                header = section.get('headers')[idx]
                output = "\tpage #{0}: OFFSET({1}), SIZE({2})".format(idx+1, header.get('offset'),
                                                                      header.get('body').get('compressed_size'))
                # print(str)
                output += '\n'
                f.write(output)

        print("OBJECTS ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
        f.write("\nOBJECTS ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n")
        # sort object items based on the offset
        objects = self.dwg_objects
        # objects = sorted(self.dwg_objects, key=lambda k: k['meta_offset'])
        for obj in objects:
            output = \
                '''[TYPE] {0:3} {1:20}\t[OFFS] {2:7}\t[SIZE] {3:5}
                '''.format(obj.get('type'),
                           self.utils.get_object_name(obj.get('type'), self.dwg_classes.get('classes')),
                           obj.get('meta_offset'), obj.get('meta_size'), width=12)
            output = output.replace('\n', '')
            output = output.rstrip()
            output += self.print_xref_info(obj)
            output += '\n'
            # print(output)
            f.write(output)

            # if obj.get('body') is not None:
            #     obj_str = json.dumps(obj, sort_keys=False, indent=4, ensure_ascii=False)
            #     # print(obj_str)
            #     f.write(obj_str)

        # check if there are empty spaces in compressed areas
        # for idx in range(len(objects)-1):
        #     if objects[idx].get('meta_offset') + objects[idx].get('meta_size') != objects[idx+1].get('meta_offset'):
        #         start = objects[idx].get('meta_offset') + objects[idx].get('meta_size')
        #         end   = objects[idx+1].get('meta_offset')
        #         # print("[ALERT] Abnormal point: unused areas in object stream")
        #         f.write("[ALERT] Abnormal point: unused areas in object stream\n")

        f.close()
        return

    def print_xref_info(self, obj):
        info = ""
        body = obj.get('body')
        if body is None:
            return info

        if body.get('handle') is not None:
            h = body.get('handle')
            info += "\tH({}.{}.{})\n".format(h.get('code'), h.get('counter'), h.get('value'))

        if body.get('entry_name') is not None:
            value = body.get('entry_name')
            if value != "":
                info += "\tNAME({})\n".format(value)

        if body.get('handle_block_control') is not None:
            h = body.get('handle_block_control')
            info += "\tH_BLOCK_CONTROL({}.{}.{}-{})\n".format(h.get('code'), h.get('counter'), h.get('value'),
                                                              h.get('absolute_reference'))

        if body.get('handle_block_header') is not None:
            h = body.get('handle_block_header')
            info += "\tH_BLOCK_HEADER({}.{}.{}-{})\n".format(h.get('code'), h.get('counter'), h.get('value'),
                                                             h.get('absolute_reference'))

        if body.get('handle_block_headers') is not None:
            hs = body.get('handle_block_headers')
            for h in hs:
                info += "\tH_BLOCK_HEADER({}.{}.{}-{})\n".format(h.get('code'), h.get('counter'), h.get('value'),
                                                                 h.get('absolute_reference'))

        if body.get('handle_block_entity') is not None:
            h = body.get('handle_block_entity')
            info += "\tH_BLOCK({}.{}.{}-{})\n".format(h.get('code'), h.get('counter'), h.get('value'),
                                                      h.get('absolute_reference'))

        if body.get('handle_endblk_entity') is not None:
            h = body.get('handle_endblk_entity')
            info += "\tH_ENDBLK({}.{}.{}-{})\n".format(h.get('code'), h.get('counter'), h.get('value'),
                                                       h.get('absolute_reference'))

        if body.get('owned_obj_count') is not None:
            value = body.get('owned_obj_count')
            if value != 0:
                info += "\tOWNED_OBJS({})\n".format(value)

        if body.get('handle_entities') is not None:
            hs = body.get('handle_entities')
            if len(hs) <= 10:
                for h in hs:
                    info += "\tH_ENTITY({}.{}.{}-{})\n".format(h.get('code'), h.get('counter'), h.get('value'),
                                                               h.get('absolute_reference'))

        if body.get('handle_inserts') is not None:
            hs = body.get('handle_inserts')
            if len(hs) <= 10:
                for h in hs:
                    info += "\tH_INSERT({}.{}.{}-{})\n".format(h.get('code'), h.get('counter'), h.get('value'),
                                                               h.get('absolute_reference'))

        if body.get('xref_index_plus1') is not None:
            value = body.get('xref_index_plus1')
            if value != 0:
                info += "\tXREF_IDX({})\n".format(value-1)

        if body.get('xdep') is not None:
            value = body.get('xdep')
            if value != 0:
                info += "\tXDEP({})\n".format(value)

        info = info.rstrip('\n')
        return info

    def build_object_map(self, section):
        """Build the object map

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
                last_handle += bc.read_mc()
                last_offset += bc.read_mc()

                # Validate each object map item
                if last_offset < 0:
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
        """Build the section entry list (list of an object name and headers)

            self.dwg_section_entry_list = [section entry dict.]

                    section entry dict. {
                        obj_name: object name
                        headers : list of header dict.
                        data    : decompressed data stream
                    }

        Returns:
            Length of self.dwg_section_entry_list
        """
        for section in self.dwg_section_map.get('map'):
            section_name = section.get('name')
            if section_name == "":
                continue

            headers = []

            for idx in range(section.get('page_count')):
                section_page_entry = self.find_page_entry(section.get('pages')[idx].get('id'))
                if section_page_entry is None:
                    continue

                # offset from file header
                offset_ff = section_page_entry.get('address')

                # decrypt encrypted header data
                temp = self.file_buf[offset_ff:offset_ff+sizeof(DWG_R18_DATA_SECTION_HEADER)]
                temp = bytearray(temp)
                sec_mask = 0x4164536B ^ offset_ff
                for i in range(0, 32, 4):
                    byte4 = int.from_bytes(temp[i:i+4], byteorder='little')
                    byte4 ^= sec_mask
                    temp[i:i+4] = byte4.to_bytes(4, byteorder='little')
                temp = bytes(temp)

                # offset in data stream
                offset_id = section.get('pages')[idx].get('address')

                header = OrderedDict()
                header['offset'] = offset_ff
                header['size'] = sizeof(DWG_R18_DATA_SECTION_HEADER)
                header['body'] = self.utils.static_cast(temp[0:sizeof(DWG_R18_DATA_SECTION_HEADER)],
                                                        DWG_R18_DATA_SECTION_HEADER)
                header['body'] = self.utils.get_dict_from_ctypes_struct(header['body'])
                headers.append(header)

                # Check the data checksum
                offset_ff = offset_ff + header.get('size')
                data = self.file_buf[offset_ff:offset_ff+header.get('body').get('compressed_size')]

                v = self.verify_checksum(data, 0, header.get('body').get('data_checksum'))
                # if v is False:
                #     print("[ALERT] Abnormal point - DWG_R18_DATA_SECTION_HEADER - Checksum check failed")

            entry = OrderedDict()
            entry['name'] = section_name
            entry['headers'] = headers

            self.dwg_section_entry_list.append(entry)

        return len(self.dwg_section_entry_list)

    def get_section_data_by_name(self, s_name):
        """Get a section entry (headers + decompressed data)

        Args:
            s_name (DWGSectionName): The section name to get data

        Returns:
            Section data (dict) or None
            {
                headers: list of header dict.
                data   : decompressed data stream
            }
        """
        section_meta = None
        for item in self.dwg_section_map.get('map'):
            if item.get('name') == s_name.value:
                section_meta = item
                break

        if section_meta is None:
            msg = "[{}] Do not exist the section '{}'.".format("section map", s_name.value)
            self.logger.info("{}(): {}".format(GET_MY_NAME(), msg))
            return None

        return self.get_section_data(section_meta)

    def get_section_data(self, section_meta):
        """Get a section data (headers + decompressed data)

        Args:
            section_meta (dict): A section meta stored in the section map

        Returns:
            Section data (dict)
            {
                headers: list of page header dict.
                data   : decompressed data stream
            }
        """
        self.logger.info("{}(): Get data of the section {}.".format(
                GET_MY_NAME(),
                section_meta.get('name'))
        )

        # 0 (if not encrypted), 2 (meaning unknown)
        if section_meta.get('encrypted') == 1:
            msg = "[{}] Data is encrypted.".format(section_meta.get('name'))
            self.logger.info("{}(): {}".format(GET_MY_NAME(), msg))
            return None

        max_decompressed_size = section_meta.get('max_decompressed_size')
        total_decompressed_size = max_decompressed_size * section_meta.get('page_count')

        headers = []
        data = bytearray(total_decompressed_size)

        for idx in range(section_meta.get('page_count')):
            section_page_entry = self.find_page_entry(section_meta.get('pages')[idx].get('id'))
            if section_page_entry is None:
                continue

            # offset from file header
            offset_ff = section_page_entry.get('address')

            # decrypt encrypted header data
            temp = self.file_buf[offset_ff:offset_ff+sizeof(DWG_R18_DATA_SECTION_HEADER)]
            temp = bytearray(temp)
            sec_mask = 0x4164536B ^ offset_ff
            for i in range(0, 32, 4):
                byte4 = int.from_bytes(temp[i:i+4], byteorder='little')
                byte4 ^= sec_mask
                temp[i:i+4] = byte4.to_bytes(4, byteorder='little')
            temp = bytes(temp)

            header = dict()
            header['offset'] = offset_ff
            header['size'] = sizeof(DWG_R18_DATA_SECTION_HEADER)
            header['body'] = self.utils.static_cast(temp[0:sizeof(DWG_R18_DATA_SECTION_HEADER)],
                                                    DWG_R18_DATA_SECTION_HEADER)
            header['body'] = self.utils.get_dict_from_ctypes_struct(header['body'])

            # Validate DWG_R18_DATA_SECTION_HEADER
            if self.validate_DWG_R18_DATA_SECTION_HEADER(header['body'], header['offset'], header['size']) is False:
                msg = "Abnormal 'DWG_R18_DATA_SECTION_HEADER' structure."
                self.logger.debug("{}(): {}".format(GET_MY_NAME(), msg))
                return None

            headers.append(header)

            # get data stream (if compressed, decompress data)
            offset = offset_ff + header['size']
            temp = self.file_buf[offset:offset+header['body'].get('compressed_size')]

            if section_meta.get('compressed') == 2:
                temp = self.utils.decompress_r18(
                    temp, len(temp),
                    max_decompressed_size
                )

            offset = idx*max_decompressed_size
            data[offset:offset+len(temp)] = temp

        if len(data) != total_decompressed_size:
            self.logger.debug("{}(): decompressed_size mis-matches.".format(GET_MY_NAME()))
            msg = "[{}] decompressed_size mis-matches.".format(section_meta.get('name'))
            self.report.add(DWGVInfo(DWGVType.CORRUPTED, -1, -1, msg))

        msg = "Totally {} bytes.".format(len(data))
        self.logger.info("{}(): {}".format(GET_MY_NAME(), msg))

        return {'headers': headers,
                'data':    bytes(data)}

    def get_section_map(self, address):
        """Parse the data section map

        Args:
            address (int): The start address from beginning of the file

        Return:
            Result dict
            {
                header  (dict)
                map     (list of dict)
            }
        """
        offset = address

        self.logger.info("{}(): Get a section map.".format(GET_MY_NAME()))

        header = OrderedDict()
        header['offset'] = offset
        header['size'] = sizeof(DWG_R18_SYSTEM_SECTION_HEADER)
        header['ss_header'] = self.utils.static_cast(self.file_buf[offset:offset+sizeof(DWG_R18_SYSTEM_SECTION_HEADER)],
                                                     DWG_R18_SYSTEM_SECTION_HEADER)
        header['ss_header'] = self.utils.get_dict_from_ctypes_struct(header['ss_header'])

        # Validate DWG_R18_SYSTEM_SECTION_HEADER
        if self.validate_DWG_R18_SYSTEM_SECTION_HEADER(header['ss_header'], header['offset'], header['size']) is False:
            msg = "Abnormal 'DWG_R18_SYSTEM_SECTION_HEADER' structure."
            self.logger.debug("{}(): {}".format(GET_MY_NAME(), msg))
            return None

        # Decompress compressed 'section page map' data
        offset += header['size']
        data = self.file_buf[offset:offset+header['ss_header'].get('compressed_size')]
        if len(data) == 0:
            return header

        data = self.utils.decompress_r18(data, len(data), header['ss_header'].get('decompressed_size'))

        if len(data) != header['ss_header'].get('decompressed_size'):
            self.logger.debug("{}(): decompressed_size mis-matches.".format(GET_MY_NAME()))
            msg = "[{}] decompressed_size mis-matches.".format("section map")
            self.report.add(DWGVInfo(DWGVType.CORRUPTED, offset, header['ss_header'].get('compressed_size'), msg))

        # Get decompressed header of 'section map' data
        offset = 0
        header['section_map_header'] = self.utils.static_cast(data[offset:offset+sizeof(DWG_R18_SECTION_MAP_HEADER)],
                                                              DWG_R18_SECTION_MAP_HEADER)
        header['section_map_header'] = self.utils.get_dict_from_ctypes_struct(header['section_map_header'])

        # Validate DWG_R18_SECTION_MAP_HEADER
        if self.validate_DWG_R18_SECTION_MAP_HEADER(header['section_map_header'],
                                                    offset, sizeof(DWG_R18_SECTION_MAP_HEADER)) is False:
            msg = "Abnormal 'DWG_R18_SECTION_MAP_HEADER' structure."
            self.logger.debug("{}(): {}".format(GET_MY_NAME(), msg))
            return None

        offset += sizeof(DWG_R18_SECTION_MAP_HEADER)

        # Interpret decompressed 'section map' data
        section_map = []

        for idx in range(header.get('section_map_header').get('section_entry_count')):
            entry = self.utils.static_cast(data[offset:offset+sizeof(DWG_R18_SECTION_ENTRY)],
                                           DWG_R18_SECTION_ENTRY)
            entry = self.utils.get_dict_from_ctypes_struct(entry)

            # Validate DWG_R18_SECTION_ENTRY
            if self.validate_DWG_R18_SECTION_ENTRY(entry, offset, sizeof(DWG_R18_SECTION_ENTRY)) is False:
                msg = "Abnormal 'DWG_R18_SECTION_ENTRY' structure."
                self.logger.debug("{}(): {}".format(GET_MY_NAME(), msg))
                return None

            offset += sizeof(DWG_R18_SECTION_ENTRY)

            # Get pages related to this section
            entry['pages'] = []
            for count in range(entry.get('page_count')):
                page = self.utils.static_cast(data[offset:offset+sizeof(DWG_R18_SECTION_ENTRY_PAGE_INFO)],
                                              DWG_R18_SECTION_ENTRY_PAGE_INFO)
                page = self.utils.get_dict_from_ctypes_struct(page)

                # Validate DWG_R18_SECTION_ENTRY_PAGE_INFO
                if self.validate_DWG_R18_SECTION_ENTRY_PAGE_INFO(page, offset,
                                                                 sizeof(DWG_R18_SECTION_ENTRY_PAGE_INFO)) is False:
                    msg = "Abnormal 'DWG_R18_SECTION_ENTRY_PAGE_INFO' structure."
                    self.logger.debug("{}(): {}".format(GET_MY_NAME(), msg))
                    return None

                entry['pages'].append(page)
                offset += sizeof(DWG_R18_SECTION_ENTRY_PAGE_INFO)

            section_map.append(entry)

        self.logger.info("{}(): {} items in section map.".format(GET_MY_NAME(), len(section_map)))

        return {'header': header,
                'map':    section_map}

    def find_page_entry(self, id):
        page_map = self.dwg_page_map['map']
        for entry in page_map:
            if entry['id'] == id:
                return entry
        return None

    def get_page_map(self, offset):
        """Parse the page map

        Returns:
            Result dict
            {
                header (dict)
                map (list)
                map_unused (list)
            }
        """
        self.logger.info("{}(): Get a page map.".format(GET_MY_NAME()))

        header = OrderedDict()
        header['offset'] = offset
        header['size'] = sizeof(DWG_R18_SYSTEM_SECTION_HEADER)
        header['body'] = self.utils.static_cast(self.file_buf[offset:offset+sizeof(DWG_R18_SYSTEM_SECTION_HEADER)],
                                                DWG_R18_SYSTEM_SECTION_HEADER)
        header['body'] = self.utils.get_dict_from_ctypes_struct(header['body'])

        # Validate DWG_R18_SYSTEM_SECTION_HEADER
        if self.validate_DWG_R18_SYSTEM_SECTION_HEADER(header['body'], header['offset'], header['size']) is False:
            msg = "Abnormal 'DWG_R18_SYSTEM_SECTION_HEADER' structure."
            self.logger.debug("{}(): {}".format(GET_MY_NAME(), msg))
            return None

        # decompress compressed 'section page map' data
        offset += header['size']
        data = self.file_buf[offset:offset+header['body'].get('compressed_size')]
        if len(data) == 0:
            return None
        data = self.utils.decompress_r18(data, len(data), header['body'].get('decompressed_size'))

        if len(data) != header['body'].get('decompressed_size'):
            self.logger.debug("{}(): decompressed_size mis-matches.".format(GET_MY_NAME()))
            msg = "[{}] decompressed_size mis-matches.".format("page map")
            self.report.add(DWGVInfo(DWGVType.CORRUPTED, header['offset'], header['size'], msg))

        # Interpret decompressed 'section page map' data
        page_map = []
        page_map_unused = []
        page_address = 0x100
        offset = 0
        decompressed_size = len(data)

        while offset < decompressed_size:
            entry = dict()
            entry['id']      = struct.unpack('<i', data[offset+0 : offset+4])[0]
            entry['size']    = struct.unpack('<i', data[offset+4 : offset+8])[0]
            entry['address'] = page_address
            page_address += entry['size']
            offset += 8

            if entry['id'] < 0:
                entry['parent'] = struct.unpack('<i', data[offset+ 0 : offset+ 4])[0]
                entry['left']   = struct.unpack('<i', data[offset+ 4 : offset+ 8])[0]
                entry['right']  = struct.unpack('<i', data[offset+ 8 : offset+12])[0]
                entry['x00']    = struct.unpack('<i', data[offset+12 : offset+16])[0]
                offset += 16
                page_map_unused.append(entry)
            else:
                page_map.append(entry)

        self.logger.info("{}(): {} items in page map.".format(GET_MY_NAME(), len(page_map)))
        self.logger.info("{}(): {} items in page map (unused).".format(GET_MY_NAME(), len(page_map_unused)))

        return {'header': header,
                'map':    page_map,
                'map_unused': page_map_unused}

    def get_file_header(self, offset):
        """Parse the file header (base header (1st) + encrypted header (2nd) data)

        Returns:
            Header dict --> 2nd file header
            {
                offset
                size
                body (DWG_R21_FILE_HEADER_2ND)
            }
        """
        self.logger.info("{}(): Get the 1st and 2nd file headers.".format(GET_MY_NAME()))

        d = dict()
        d['offset'] = offset
        d['size'] = sizeof(DWG_R18_FILE_HEADER_1ST) + sizeof(DWG_R18_FILE_HEADER_2ND)
        d['body'] = self.utils.static_cast(self.file_buf[offset:offset+sizeof(DWG_R18_FILE_HEADER_1ST)],
                                           DWG_R18_FILE_HEADER_1ST)
        data = bytearray(d['body'].encrypted_header)
        d['body'] = self.utils.get_dict_from_ctypes_struct(d['body'])

        # Validate DWG_R18_FILE_HEADER_1ST
        if self.validate_DWG_R18_FILE_HEADER_1ST(d['body'], d['offset'], d['size']) is False:
            msg = "Abnormal 'DWG_R18_FILE_HEADER_1ST' structure."
            self.logger.debug("{}(): {}".format(GET_MY_NAME(), msg))
            return None

        # Set the 1st file header
        self.dwg_file_header_1st = d

        # Decrypt encrypted header data
        randseed = 1
        for i in range(0x6C):
            randseed *= 0x0343FD
            randseed += 0x269EC3
            data[i] = (data[i] ^ ((randseed >> 0x10) & 0xFF))

        d = dict()
        d['offset'] = 0x80
        d['size'] = 0x400

        data = bytes(data)
        d['body'] = self.utils.static_cast(data[offset:offset+sizeof(DWG_R18_FILE_HEADER_2ND)],
                                           DWG_R18_FILE_HEADER_2ND)
        d['body'] = self.utils.get_dict_from_ctypes_struct(d['body'])

        # Validate DWG_R18_FILE_HEADER_2ND
        if self.validate_DWG_R18_FILE_HEADER_2ND(d['body'], d['offset'], d['size']) is False:
            msg = "Abnormal 'DWG_R18_FILE_HEADER_2ND' structure."
            self.logger.debug("{}(): {}".format(GET_MY_NAME(), msg))
            return None

        # CRC check
        data = data[:-4] + (b'\x00' * 4)
        v = self.check_crc(data, d.get('body').get('crc32'))
        if v is False:
            self.logger.debug("{}(): CRC check failed.".format(GET_MY_NAME()))
            self.report.add(DWGVInfo(DWGVType.INVALID_CRC, d['offset'], d['size']))

        return d

    def verify_checksum(self, data, seed, saved_value):
        """Verify the checksum value

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

    def validate_DWG_R18_FILE_HEADER_1ST(self, data, offset=-1, size=-1):
        """Validate the internal structure

        Args:
            data (dict): DWG_R18_FILE_HEADER_1ST
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

        return True


    def validate_DWG_R18_FILE_HEADER_2ND(self, data, offset=-1, size=-1):
        """Validate the internal structure

        Args:
            data (dict): DWG_R18_FILE_HEADER_2ND
            offset (int)
            size (int)

        Returns:
            True or False
        """
        if 'AcFssFcAJMB' != data.get('id_string'):
            msg = "[{}] id_string ('AcFssFcAJMB') mis-matches.".format("2nd file header")
            self.report.add(DWGVInfo(DWGVType.SYNTAX_ERROR, offset, size, msg))
            return False

        if self.file_size <= data.get('second_header_address'):
            msg = "[{}] second_header_address is invalid.".format("2nd file header")
            self.report.add(DWGVInfo(DWGVType.SYNTAX_ERROR, offset, size, msg))
            return False

        if self.file_size <= data.get('page_map_address'):
            msg = "[{}] page_map_address is invalid.".format("2nd file header")
            self.report.add(DWGVInfo(DWGVType.SYNTAX_ERROR, offset, size, msg))
            return False

        return True


    def validate_DWG_R18_SYSTEM_SECTION_HEADER(self, data, offset=-1, size=-1):
        """Validate the internal structure

        Args:
            data (dict): DWG_R21_FILE_HEADER_1ST
            offset (int)
            size (int)

        Returns:
            True or False
        """
        if 0x41630E3B != data.get('signature') and 0x4163003B != data.get('signature') :
            msg = "[{}] signature is invalid.".format("system section header")
            self.report.add(DWGVInfo(DWGVType.SYNTAX_ERROR, offset, size, msg))
            return False

        data_size = data.get('compressed_size')
        if data_size < 0:
            data_size = -data_size

        if self.file_size-0x20 <= data_size:
            msg = "[{}] compressed_size is invalid.".format("system section header")
            self.report.add(DWGVInfo(DWGVType.SYNTAX_ERROR, offset, size, msg))
            return False

        return True


    def validate_DWG_R18_SECTION_MAP_HEADER(self, data, offset=-1, size=-1):
        """Validate the internal structure

        Args:
            data (dict): DWG_R18_SECTION_MAP_HEADER
            offset (int)
            size (int)

        Returns:
            True or False
        """
        return True


    def validate_DWG_R18_SECTION_ENTRY(self, data, offset=-1, size=-1):
        """Validate the internal structure

        Args:
            data (dict): DWG_R18_SECTION_ENTRY
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

        if data.get('compressed') in [1, 2] is False:
            msg = "[{}] compressed flag is invalid.".format("an entry of section map")
            self.report.add(DWGVInfo(DWGVType.SYNTAX_ERROR, offset, size, msg))
            return False

        return True


    def validate_DWG_R18_SECTION_ENTRY_PAGE_INFO(self, data, offset=-1, size=-1):
        """Validate the internal structure

        Args:
            data (dict): DWG_R18_SECTION_ENTRY_PAGE_INFO
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

        if self.file_size <= data.get('size'):
            msg = "[{}] compressed size is invalid.".format("an entry of section map")
            self.report.add(DWGVInfo(DWGVType.SYNTAX_ERROR, offset, size, msg))
            return False

        return True


    def validate_DWG_R18_DATA_SECTION_HEADER(self, data, offset=-1, size=-1):
        """Validate the internal structure

        Args:
            data (dict): DWG_R18_DATA_SECTION_HEADER
            offset (int)
            size (int)

        Returns:
            True or False
        """
        if 0x4163043B != data.get('signature'):
            msg = "[{}] signature is invalid.".format("system section header")
            self.report.add(DWGVInfo(DWGVType.SYNTAX_ERROR, offset, size, msg))
            return False

        data_size = data.get('compressed_size')
        if data_size < 0:
            data_size = -data_size

        if self.file_size-0x20 <= data_size:
            msg = "[{}] compressed_size is invalid.".format("system section header")
            self.report.add(DWGVInfo(DWGVType.SYNTAX_ERROR, offset, size, msg))
            return False

        return True

