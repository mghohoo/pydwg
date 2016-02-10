# -*- coding: utf-8 -*-

"""@package pydwg

    * Description
        DWGSectionDecoder
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

import time
from datetime import timezone
import logging
from collections import OrderedDict
from .dwg_common import *
from .dwg_utils import *
from .dwg_bit_codes import *
from .dwg_report import *
from .dwg_object import *


class DWGSectionDecoder:
    """DWGSectionDecoder class

    """
    def __init__(self, dwg_version, report):
        """The constructor"""
        self.dwg_version = dwg_version
        self.utils = DWGUtils(report)
        self.object = DWGObject(dwg_version, report)

        self.logger = logging.getLogger(__name__)
        self.report = report
        return

    def filedeplist(self, section, encoding=DWGEncoding.UTF8.value):
        """Decode the file dependencies from the 'AcDb:FileDepList' section

        Args:
            section (dict): section dictionary
                            {'header', 'data'}
            encoding (DWGEncoding)
        Returns:
            Decoding results (dict)
            {
                feature_count (int)
                feature_name (list): str
                file_count (int)
                files (list): dict { filename, dirpath, fingerprint_guid, version_guid,
                                     feature_index (int), timestamp, filesize (int),
                                     affects_graphics (bool), reference_count (int) }
            }
        """
        self.logger.info("{}(): Decode data stream.".format(GET_MY_NAME()))

        decoded = OrderedDict()

        data = section.get('data')
        if len(data) == 0:
            self.logger.debug("{}(): Data is empty.".format(GET_MY_NAME()))
            return decoded

        bc = DWGBitCodes(data, len(data))

        count = decoded['feature_count'] = bc.read_rl()
        decoded['feature_name'] = []
        for idx in range(count):
            length = bc.read_rl()
            value = bc.read_rcs(length)
            decoded['feature_name'].append(value.decode(encoding, 'ignore'))

        count = decoded['file_count'] = bc.read_rl()
        decoded['files'] = []
        for idx in range(count):
            item = OrderedDict()
            value = bc.read_rcs(bc.read_rl())
            item['filename'] = value.decode(encoding, 'ignore')
            value = bc.read_rcs(bc.read_rl())
            item['dirpath'] = value.decode(encoding, 'ignore')
            value = bc.read_rcs(bc.read_rl())
            item['fingerprint_guid'] = value.decode(encoding, 'ignore')
            value = bc.read_rcs(bc.read_rl())
            item['version_guid'] = value.decode(encoding, 'ignore')
            item['feature_index'] = bc.read_rl()
            value = datetime.datetime(1980, 1, 1).timestamp() + bc.read_rl()
            dt = datetime.datetime.utcfromtimestamp(value)
            item['timestamp'] = dt.strftime("%Y-%m-%d %H:%M:%S (UTC)")  # What does this time mean?
            item['filesize'] = bc.read_rl()
            item['affects_graphics'] = bc.read_rs()
            item['reference_count'] = bc.read_rl()
            decoded['files'].append(item)

        # Check slack areas
        slack_offset = bc.pos_byte
        slack_length = len(data)-bc.pos_byte
        for idx in range(slack_length):
            if bc.read_rc() != 0x00:
                msg = "[{}] Found data in slack area.".format(DWGSectionName.FILEDEPLIST.value)
                self.logger.debug("{}(): {}".format(GET_MY_NAME(), msg))
                self.report.add(DWGVInfo(DWGVType.UNUSED_AREA, slack_offset, slack_length, msg))

        return decoded

    def preview(self, section):
        """Decode the preview data from the 'AcDb:Preview' section

        Args:
            section (dict): section dictionary
                            {'header', 'data'}
        Returns:
            Decoding results (dict)
            {
                overall_size
                counter
                header  (if it is present)
                bmp     (if it is present)
                wmf     (if it is present)
            }
        """
        self.logger.info("{}(): Decode data stream.".format(GET_MY_NAME()))

        decoded = dict()

        data = section.get('data')
        if len(data) == 0:
            self.logger.debug("{}(): Data is empty.".format(GET_MY_NAME()))
            return decoded

        bc = DWGBitCodes(data, len(data))

        sn = bc.read_sn()
        if DWG_SENTINEL_PREVIEW_BEFORE != sn:
            msg = "[{}] DWG_SENTINEL_PREVIEW_BEFORE mis-match.".format(DWGSectionName.PREVIEW.value)
            self.logger.debug("{}(): {}".format(GET_MY_NAME(), msg))
            self.report.add(DWGVInfo(DWGVType.SYNTAX_ERROR, 0, len(sn), msg))
            return decoded

        decoded['overall_size'] = bc.read_rl()
        count = decoded['counter'] = bc.read_rc()

        header_size = 0
        bmp_size = 0
        wmf_size = 0

        for idx in range(count):
            code = bc.read_rc()
            if code == 1:
                header_start = bc.read_rl()  # from beginning of file
                header_size  = bc.read_rl()
            elif code == 2:
                bmp_start = bc.read_rl()     # from beginning of file
                bmp_size  = bc.read_rl()
            elif code == 3:
                wmf_start = bc.read_rl()     # from beginning of file
                wmf_size  = bc.read_rl()

        if bmp_size > 0:
            decoded['header'] = bc.read_rcs(header_size)  # what is this?

        if bmp_size > 0:
            decoded['bmp'] = bc.read_rcs(bmp_size)  # what is the default setting of BMP file?

        if wmf_size > 0:
            decoded['wmf'] = bc.read_rcs(wmf_size)  # what is the default setting of WMF file?

        sn = bc.read_sn()
        if DWG_SENTINEL_PREVIEW_AFTER != sn:
            msg = "[{}] DWG_SENTINEL_PREVIEW_AFTER mis-match.".format(DWGSectionName.PREVIEW.value)
            self.logger.debug("{}(): {}".format(GET_MY_NAME(), msg))
            self.report.add(DWGVInfo(DWGVType.SYNTAX_ERROR, bc.pos_byte-len(sn), len(sn), msg))

        # Check slack areas
        slack_offset = bc.pos_byte
        slack_length = len(data)-bc.pos_byte
        for idx in range(slack_length):
            if bc.read_rc() != 0x00:
                msg = "[{}] Found data in slack area.".format(DWGSectionName.FILEDEPLIST.value)
                self.logger.debug("{}(): {}".format(GET_MY_NAME(), msg))
                self.report.add(DWGVInfo(DWGVType.UNUSED_AREA, slack_offset, slack_length, msg))

        return decoded

    def appinfo(self, section, app_version):
        """Decode the application information from the 'AcDb:AppInfo' section

        Args:
            section (dict): section dictionary
                            {'header', 'data'}
            app_version (int): Application version from DWG file header
        Returns:
            Decoding results (dict)
            {
                app_info_name
                version_checksum
                version
                comment_checksum
                comment
                product_checksum
                product
                app_info_version
            }
        """
        self.logger.info("{}(): Decode data stream.".format(GET_MY_NAME()))

        decoded = OrderedDict()

        data = section.get('data')
        if len(data) == 0:
            self.logger.debug("{}(): Data is empty.".format(GET_MY_NAME()))
            return decoded

        bc = DWGBitCodes(data, len(data))

        if DWGVersion.R21 <= app_version:
            uk = bc.read_rl()  # unknown (0x00000003?)
            value = self.utils.rstrip_null(bc.read_rcs(bc.read_rs()*2), True)  # bc.read_rs() is length of data
            decoded['app_info_name'] = value.decode('UTF-16LE', 'ignore')

            uk = bc.read_rl()  # unknown (0x00000003?)
            decoded['version_checksum'] = bc.read_rcs(16)
            value = self.utils.rstrip_null(bc.read_rcs(bc.read_rs()*2), True)
            decoded['version'] = value.decode('UTF-16LE', 'ignore')

            decoded['comment_checksum'] = bc.read_rcs(16)
            value = self.utils.rstrip_null(bc.read_rcs(bc.read_rs()*2), True)
            decoded['comment'] = value.decode('UTF-16LE', 'ignore')

            decoded['product_checksum'] = bc.read_rcs(16)
            value = self.utils.rstrip_null(bc.read_rcs(bc.read_rs()*2), True)
            decoded['product'] = value.decode('UTF-16LE', 'ignore')  # XML

            value = self.utils.rstrip_null(bc.read_rcs(bc.read_rs()*2), True)
            decoded['app_info_version'] = value.decode('UTF-16LE', 'ignore')
        else:  # for R18
            value = self.utils.rstrip_null(bc.read_rcs(bc.read_rs()*2), True)
            decoded['app_info_name'] = value.decode('UTF-16LE', 'ignore')

            uk = bc.read_rl()  # unknown
            value = self.utils.rstrip_null(bc.read_rcs(bc.read_rs()*2), True)
            decoded['unknown'] = value.decode('UTF-16LE', 'ignore')

            value = self.utils.rstrip_null(bc.read_rcs(bc.read_rs()*2), True)
            decoded['product'] = value.decode('UTF-16LE', 'ignore')  # XML

            value = self.utils.rstrip_null(bc.read_rcs(bc.read_rs()*2), True)
            decoded['app_info_version'] = value.decode('UTF-16LE', 'ignore')

        # Check slack areas
        slack_offset = bc.pos_byte
        slack_length = len(data)-bc.pos_byte
        for idx in range(slack_length):
            if bc.read_rc() != 0x00:
                msg = "[{}] Found data in slack area.".format(DWGSectionName.FILEDEPLIST.value)
                self.logger.debug("{}(): {}".format(GET_MY_NAME(), msg))
                self.report.add(DWGVInfo(DWGVType.UNUSED_AREA, slack_offset, slack_length, msg))

        return decoded

    def appinfohistory(self, section, app_version):
        """Decode the application info. history from the 'AcDb:AppInfoHistory' section

        Args:
            section (dict): section dictionary
                            {'header', 'data'}
            app_version (int): Application version from DWG file header
        Returns:
            Decoding results (dict)
            {
                app_info_name
                version_checksum
                version
                comment_checksum
                comment
                property_checksum
                property (XML format)
                product_checksum
                product (XML format)
            }
        """
        self.logger.info("{}(): Decode data stream.".format(GET_MY_NAME()))

        decoded = OrderedDict()

        data = section.get('data')
        if len(data) == 0:
            self.logger.debug("{}(): Data is empty.".format(GET_MY_NAME()))
            return decoded

        bc = DWGBitCodes(data, len(data))

        if DWGVersion.R18 <= app_version:
            uk = bc.read_rcs(0x20)

            uk = bc.read_rl()  # unknown
            value = self.utils.rstrip_null(bc.read_rcs(bc.read_rs()*2), True)  # bc.read_rs() is length of data
            decoded['app_info_name'] = value.decode('UTF-16LE', 'ignore')

            uk = bc.read_rl()  # unknown
            decoded['version_checksum'] = bc.read_rcs(16)
            value = self.utils.rstrip_null(bc.read_rcs(bc.read_rs()*2), True)
            decoded['version'] = value.decode('UTF-16LE', 'ignore')

            decoded['comment_checksum'] = bc.read_rcs(16)
            value = self.utils.rstrip_null(bc.read_rcs(bc.read_rs()*2), True)
            decoded['comment'] = value.decode('UTF-16LE', 'ignore')

            decoded['property_checksum'] = bc.read_rcs(16)
            value = self.utils.rstrip_null(bc.read_rcs(bc.read_rs()*2), True)
            decoded['property'] = value.decode('UTF-16LE', 'ignore')  # XML

            decoded['product_checksum'] = bc.read_rcs(16)
            value = self.utils.rstrip_null(bc.read_rcs(bc.read_rs()*2), True)
            decoded['product'] = value.decode('UTF-16LE', 'ignore')  # XML

        # Check slack areas
        slack_offset = bc.pos_byte
        slack_length = len(data)-bc.pos_byte
        for idx in range(slack_length):
            if bc.read_rc() != 0x00:
                msg = "[{}] Found data in slack area.".format(DWGSectionName.FILEDEPLIST.value)
                self.logger.debug("{}(): {}".format(GET_MY_NAME(), msg))
                self.report.add(DWGVInfo(DWGVType.UNUSED_AREA, slack_offset, slack_length, msg))

        return decoded

    def auxheader(self, section):
        """Decode the auxiliary file header from the 'AcDb:AuxHeader' section

        Args:
            section (dict): section dictionary
                            {'header', 'data'}
        Returns:
            Decoding results (dict)
            {
                signature (3 bytes): 0xff 0x77 0x01
                dwg_version (int)
                maintenance_version (int)
                number_of_saves (int)
            }
        """
        decoded = OrderedDict()

        data = section.get('data')
        if len(data) == 0:
            return decoded

        bc = DWGBitCodes(data, len(data))

        decoded['signature'] = bc.read_rcs(3)
        decoded['dwg_version'] = bc.read_rs()
        decoded['maintenance_version'] = bc.read_rs()
        decoded['number_of_saves'] = bc.read_rl()  # starts at 1
        # uk = bc.read_rl()  # -1
        # decoded['number_of_saves_part1'] = bc.read_rs()
        # decoded['number_of_saves_part2'] = bc.read_rs()
        # uk = bc.read_rl()  # 0
        # uk = bc.read_rs()  # DWG version string
        # uk = bc.read_rs()  # Maintenance version
        # uk = bc.read_rs()  # DWG version string
        # uk = bc.read_rs()  # Maintenance version
        # uk = bc.read_rs()  # 0x0005
        # uk = bc.read_rs()  # 0x0893
        # uk = bc.read_rs()  # 0x0005
        # uk = bc.read_rs()  # 0x0893
        # uk = bc.read_rs()  # 0x0000
        # uk = bc.read_rs()  # 0x0001
        # uk = bc.read_rl()  # 0x0000
        # uk = bc.read_rl()  # 0x0000
        # uk = bc.read_rl()  # 0x0000
        # uk = bc.read_rl()  # 0x0000
        # uk = bc.read_rl()  # 0x0000
        #
        # jd = bc.read_bl()
        # ms = bc.read_bl()
        # decoded['TDCREATE'] = self.utils.jd_to_datetime(jd, ms)
        #
        # jd = bc.read_bl()
        # ms = bc.read_bl()
        # decoded['TDUPDATE'] = self.utils.jd_to_datetime(jd, ms)
        #
        # decoded['handle_seed'] = bc.read_rl()
        # decoded['educational_plot_stamp'] = bc.read_rl()
        # uk = bc.read_rs()  # 0
        # uk = bc.read_rs()  # Number of saves part 1 – number of saves part 2
        # uk = bc.read_rl()  # 0
        # uk = bc.read_rl()  # 0
        # uk = bc.read_rl()  # 0
        # uk = bc.read_rl()  # Number of saves
        # uk = bc.read_rl()  # 0
        # uk = bc.read_rl()  # 0
        # uk = bc.read_rl()  # 0
        # uk = bc.read_rl()  # 0

        # Check slack areas
        # for idx in range(len(data)-bc.pos_byte):
        #     if bc.read_rc() != 0x00:
        #         print("[Abnormal] auxheader")
        #         break

        return decoded

    def summaryinfo(self, section, encoding=DWGEncoding.UTF8.value):
        """Decode the summary information from the 'AcDb:SummaryInfo' section

        Args:
            section (dict): section dictionary
                            {'header', 'data'}
            encoding (DWGEncoding): UTF8, KOREAN, JAPANESE, CHINESE_BG, CHINESE_BIG5, UTF-16LE
        Returns:
            Decoding results (dict)
            {
                Title
                Subject
                Author
                Keywords
                Comments
                Last saved by
                Revision number
                Hyperlink base
                Total editing time
                Created time
                Modified time
                CUSTOM_NAMES (if it is present)
            }
        """
        self.logger.info("{}(): Decode data stream.".format(GET_MY_NAME()))

        decoded = OrderedDict()
        unicode = True if encoding == DWGEncoding.UTF16LE.value else False

        data = section.get('data')
        if len(data) == 0:
            self.logger.debug("{}(): Data is empty.".format(GET_MY_NAME()))
            return decoded

        bc = DWGBitCodes(data, len(data))

        base_properties = \
            ['Title', 'Subject', 'Author', 'Keywords', 'Comments',
             'Last saved by', 'Revision number', 'Hyperlink base']

        for prop in base_properties:
            length = bc.read_rs()*2 if encoding == DWGEncoding.UTF16LE.value else bc.read_rs()
            value = self.utils.rstrip_null(bc.read_rcs(length), unicode)
            decoded[prop] = value.decode(encoding, 'ignore')

        base_properties_time = \
            ['Total editing time', 'Created time', 'Modified time']

        for prop in base_properties_time:
            jd = int.from_bytes(bc.read_rcs(4), 'little')
            ms = int.from_bytes(bc.read_rcs(4), 'little')
            if prop == 'Total editing time':
                decoded[prop] = self.utils.jd_to_datetime(jd, ms, False)
            else:
                decoded[prop] = self.utils.jd_to_datetime(jd, ms)

        # Count of custom properties
        count = bc.read_rs()
        for idx in range(count):
            length = bc.read_rs()*2 if encoding == DWGEncoding.UTF16LE.value else bc.read_rs()
            name = self.utils.rstrip_null(bc.read_rcs(length), unicode)
            length = bc.read_rs()*2 if encoding == DWGEncoding.UTF16LE.value else bc.read_rs()
            value = self.utils.rstrip_null(bc.read_rcs(length), unicode)
            decoded[name.decode(encoding, 'ignore')] = value.decode(encoding, 'ignore')

        # Check slack areas
        slack_offset = bc.pos_byte
        slack_length = len(data)-bc.pos_byte
        for idx in range(slack_length):
            if bc.read_rc() != 0x00:
                msg = "[{}] Found data in slack area.".format(DWGSectionName.FILEDEPLIST.value)
                self.logger.debug("{}(): {}".format(GET_MY_NAME(), msg))
                self.report.add(DWGVInfo(DWGVType.UNUSED_AREA, slack_offset, slack_length, msg))

        return decoded

    def objects(self, section, object_map):
        """Decode all objects

        Args:
            section (dict): section dictionary {'header', 'data'}
            object_map (list): list of dict {'handle', 'offset'}

        Returns:
            list of decoded objects
        """
        self.logger.info("{}(): Decode data stream.".format(GET_MY_NAME()))

        objects = []

        data = section.get('data')
        if len(data) == 0:
            self.logger.debug("{}(): Data is empty.".format(GET_MY_NAME()))
            return objects

        bc = DWGBitCodes(data, len(data))

        for item in object_map:
            handle = item.get('handle')
            offset = item.get('offset')
            bc.set_pos(offset)

            obj = dict()
            obj['handle_from_object_map'] = handle
            obj['offset'] = offset

            size = bc.read_ms()  # size in bytes excluding 2 bytes (crc)
            if size <= 0 or len(data) <= size + 2:
                self.logger.debug("{}(): Object's size is invalid.".format(GET_MY_NAME()))
                msg = "[{}] Object's size is invalid.".format(DWGSectionName.ACDBOBJECTS.value)
                self.report.add(DWGVInfo(DWGVType.CORRUPTED, offset, -1, msg))
                continue

            plus = bc.pos_byte - offset
            size += 2  # 2 bytes for CRC
            obj['size'] = plus+size

            # self.utils.print_hex_bytes(bc.buf[offset:offset+size], size)

            if DWGVersion.R24 <= self.dwg_version:
                obj['handle_stream_size'] = bc.read_mc()  # size in bits

            obj['body'] = self.object.decode(buf=data[bc.pos_byte:bc.pos_byte+size],
                                             pos_bit=bc.pos_bit,
                                             size=size)
            if obj.get('body') is None:
                self.logger.debug("{}(): Unknown object.".format(GET_MY_NAME()))
                msg = "[{}] Unknown object.".format(DWGSectionName.ACDBOBJECTS.value)
                self.report.add(DWGVInfo(DWGVType.UNKNOWN_OBJECT, offset, size, msg))
                continue

            if obj.get('body').get('handle') is None:
                self.logger.debug("{}(): Object cannot be decoded.".format(GET_MY_NAME()))
                msg = "[{}] Object cannot be parsed.".format(DWGSectionName.ACDBOBJECTS.value)
                self.report.add(DWGVInfo(DWGVType.CORRUPTED, offset, size, msg))
                continue

            obj['type'] = obj.get('body').get('type')
            objects.append(obj)
            # self.utils.print_dict(obj)

        self.logger.info("{}(): {} objects are decoded.".format(GET_MY_NAME(), len(objects)))
        return objects

    def header(self, section):
        """Decode header variables from the 'AcDb:Classes' section

        Args:
            section (dict): section dictionary {'header', 'data'}

        Returns:
            Decoding results (dict)
            {
                -------------------------
                ...

                ...
                -------------------------
                CRC (RS): for the data section, starting after the sentinel (seed: 0xC0C1)
                -------------------------
            }
        """
        self.logger.info("{}(): Decode data stream.".format(GET_MY_NAME()))

        decoded = dict()

        data = section.get('data')
        if len(data) == 0:
            self.logger.debug("{}(): Data is empty.".format(GET_MY_NAME()))
            return decoded

        bc = DWGBitCodes(data, len(data))

        sn = bc.read_sn()
        if DWG_SENTINEL_HEADER_BEFORE != sn:
            msg = "[{}] DWG_SENTINEL_HEADER_BEFORE mis-match.".format(DWGSectionName.HEADER.value)
            self.logger.debug("{}(): {}".format(GET_MY_NAME(), msg))
            self.report.add(DWGVInfo(DWGVType.SYNTAX_ERROR, 0, len(sn), msg))
            return decoded

        decoded['size'] = bc.read_rl()  # size in byte?

        if DWGVersion.R27 <= self.dwg_version:
            decoded['REQUIRED_VERSIONS'] = bc.read_bll()

        uk = bc.read_bd()  # unknown
        uk = bc.read_bd()  # unknown
        uk = bc.read_bd()  # unknown
        uk = bc.read_bd()  # unknown
        uk = bc.read_tv()  # unknown
        uk = bc.read_tv()  # unknown
        uk = bc.read_tv()  # unknown
        uk = bc.read_tv()  # unknown
        uk = bc.read_bl()  # unknown
        uk = bc.read_bl()  # unknown

        decoded['DIMASO'] = bc.read_b()
        decoded['DIMSHO'] = bc.read_b()

        decoded['PLINEGEN'] = bc.read_b()
        decoded['ORTHOMODE'] = bc.read_b()
        decoded['REGENMODE'] = bc.read_b()
        decoded['FILLMODE'] = bc.read_b()
        decoded['QTEXTMODE'] = bc.read_b()
        decoded['PSLTSCALE'] = bc.read_b()
        decoded['LIMCHECK'] = bc.read_b()

        uk = bc.read_b()  # unknown

        decoded['USERTIMER'] = bc.read_b()
        decoded['SKPOLY'] = bc.read_b()
        decoded['ANGDIR'] = bc.read_b()
        decoded['SPLFRAME'] = bc.read_b()

        decoded['MIRRTEXT'] = bc.read_b()
        decoded['WORLDVIEW'] = bc.read_b()

        decoded['TILEMODE'] = bc.read_b()
        decoded['PLIMCHECK'] = bc.read_b()
        decoded['VISRETAIN'] = bc.read_b()

        decoded['DISPSILH'] = bc.read_b()
        decoded['PELLIPSE'] = bc.read_b()
        decoded['PROXYGRAPHICS'] = bc.read_bs()

        decoded['TREEDEPTH'] = bc.read_bs()
        decoded['LUNITS'] = bc.read_bs()
        decoded['LUPREC'] = bc.read_bs()
        decoded['AUNITS'] = bc.read_bs()
        decoded['AUPREC'] = bc.read_bs()

        decoded['ATTMODE'] = bc.read_bs()

        decoded['PDMODE'] = bc.read_bs()

        uk = bc.read_bl()
        uk = bc.read_bl()
        uk = bc.read_bl()

        decoded['USERI1'] = bc.read_bs()
        decoded['USERI2'] = bc.read_bs()
        decoded['USERI3'] = bc.read_bs()
        decoded['USERI4'] = bc.read_bs()
        decoded['USERI5'] = bc.read_bs()

        decoded['SPLINESEGS'] = bc.read_bs()
        decoded['SURFU'] = bc.read_bs()
        decoded['SURFV'] = bc.read_bs()
        decoded['SURFTYPE'] = bc.read_bs()
        decoded['SURFTAB1'] = bc.read_bs()

        decoded['SURFTAB2'] = bc.read_bs()
        decoded['SPLINETYPE'] = bc.read_bs()
        decoded['SHADEDGE'] = bc.read_bs()
        decoded['SHADEDIF'] = bc.read_bs()
        decoded['UNITMODE'] = bc.read_bs()

        decoded['MAXACTVP'] = bc.read_bs()
        decoded['ISOLINES'] = bc.read_bs()
        decoded['CMLJUST'] = bc.read_bs()
        decoded['TEXTQLTY'] = bc.read_bs()

        decoded['LTSCALE'] = bc.read_bd()
        decoded['TEXTSIZE'] = bc.read_bd()
        decoded['TRACEWID'] = bc.read_bd()
        decoded['SKETCHINC'] = bc.read_bd()
        decoded['FILLETRAD'] = bc.read_bd()

        decoded['THICKNESS'] = bc.read_bd()
        decoded['ANGBASE'] = bc.read_bd()
        decoded['PDSIZE'] = bc.read_bd()
        decoded['PLINEWID'] = bc.read_bd()

        decoded['USERR1'] = bc.read_bd()
        decoded['USERR2'] = bc.read_bd()
        decoded['USERR3'] = bc.read_bd()
        decoded['USERR4'] = bc.read_bd()
        decoded['USERR5'] = bc.read_bd()

        decoded['CHAMFERA'] = bc.read_bd()
        decoded['CHAMFERB'] = bc.read_bd()
        decoded['CHAMFERC'] = bc.read_bd()
        decoded['CHAMFERD'] = bc.read_bd()
        decoded['FACETRES'] = bc.read_bd()
        decoded['CMLSCALE'] = bc.read_bd()
        decoded['CELTSCALE'] = bc.read_bd()

        if self.dwg_version <= DWGVersion.R18:
            decoded['MENUNAME'] = bc.read_tv()

        jd = bc.read_bl()
        ms = bc.read_bl()
        decoded['TDCREATE'] = self.utils.jd_to_datetime(jd, ms)

        jd = bc.read_bl()
        ms = bc.read_bl()
        decoded['TDUPDATE'] = self.utils.jd_to_datetime(jd, ms)

        if DWGVersion.R18 <= self.dwg_version:
            uk = bc.read_bl()
            uk = bc.read_bl()
            uk = bc.read_bl()

        jd = bc.read_bl()
        ms = bc.read_bl()
        decoded['TDINDWG'] = self.utils.jd_to_datetime(jd, ms, False)

        jd = bc.read_bl()
        ms = bc.read_bl()
        decoded['TDUSRTIMER'] = self.utils.jd_to_datetime(jd, ms, False)

        decoded['CECOLOR'] = bc.read_cmc()
        decoded['HANDSEED'] = bc.read_h()
        decoded['CLAYER'] = bc.read_h()
        decoded['TEXTSTYLE'] = bc.read_h()
        decoded['CELTYPE'] = bc.read_h()

        if DWGVersion.R21 <= self.dwg_version:
            decoded['CMATERIAL'] = bc.read_h()

        decoded['DIMSTYLE'] = bc.read_h()
        decoded['CMLSTYLE'] = bc.read_h()

        decoded['PSVPSCALE'] = bc.read_bd()

        decoded['INSBASE_PSPACE'] = bc.read_3bd()
        decoded['EXTMIN_PSPACE'] = bc.read_3bd()
        decoded['EXTMAX_PSPACE'] = bc.read_3bd()
        decoded['LIMMIN_PSPACE'] = bc.read_2rd()
        decoded['LIMMAX_PSPACE'] = bc.read_2rd()

        decoded['ELEVATION_PSPACE'] = bc.read_bd()
        decoded['UCSORG_PSPACE'] = bc.read_3bd()
        decoded['UCSXDIR_PSPACE'] = bc.read_3bd()
        decoded['UCSYDIR_PSPACE'] = bc.read_3bd()
        decoded['UCSNAME_PSPACE'] = bc.read_h()

        decoded['PUCSORTHOREF'] = bc.read_h()
        decoded['PUCSORTHOVIEW'] = bc.read_bs()
        decoded['PUCSBASE'] = bc.read_h()
        decoded['PUCSORGTOP'] = bc.read_3bd()
        decoded['PUCSORGBOTTOM'] = bc.read_3bd()
        decoded['PUCSORGLEFT'] = bc.read_3bd()
        decoded['PUCSORGRIGHT'] = bc.read_3bd()
        decoded['PUCSORGFRONT'] = bc.read_3bd()
        decoded['PUCSORGBACK'] = bc.read_3bd()

        decoded['INSBASE_MSPACE'] = bc.read_3bd()
        decoded['EXTMIN_MSPACE'] = bc.read_3bd()
        decoded['EXTMAX_MSPACE'] = bc.read_3bd()
        decoded['LIMMIN_MSPACE'] = bc.read_2rd()
        decoded['LIMMAX_MSPACE'] = bc.read_2rd()

        decoded['ELEVATION_MSPACE'] = bc.read_bd()
        decoded['UCSORG_MSPACE'] = bc.read_3bd()
        decoded['UCSXDIR_MSPACE'] = bc.read_3bd()
        decoded['UCSYDIR_MSPACE'] = bc.read_3bd()
        decoded['UCSNAME_MSPACE'] = bc.read_h()

        decoded['UCSORTHOREF'] = bc.read_h()
        decoded['UCSORTHOVIEW'] = bc.read_bs()
        decoded['UCSBASE'] = bc.read_h()
        decoded['UCSORGTOP'] = bc.read_3bd()
        decoded['UCSORGBOTTOM'] = bc.read_3bd()
        decoded['UCSORGLEFT'] = bc.read_3bd()
        decoded['UCSORGRIGHT'] = bc.read_3bd()
        decoded['UCSORGFRONT'] = bc.read_3bd()
        decoded['UCSORGBACK'] = bc.read_3bd()

        decoded['DIMPOST'] = bc.read_tv()
        decoded['DIMAPOST'] = bc.read_tv()

        decoded['DIMSCALE'] = bc.read_bd()
        decoded['DIMASZ'] = bc.read_bd()
        decoded['DIMEXO'] = bc.read_bd()
        decoded['DIMDLI'] = bc.read_bd()
        decoded['DIMEXE'] = bc.read_bd()
        decoded['DIMRND'] = bc.read_bd()
        decoded['DIMDLE'] = bc.read_bd()
        decoded['DIMTP'] = bc.read_bd()
        decoded['DIMTM'] = bc.read_bd()

        if DWGVersion.R21 <= self.dwg_version:
            decoded['DIMFXL'] = bc.read_bd()
            decoded['DIMJOGANG'] = bc.read_bd()
            decoded['DIMTFILL'] = bc.read_bs()
            decoded['DIMTFILLCLR'] = bc.read_cmc()

        decoded['DIMTOL'] = bc.read_b()
        decoded['DIMLIM'] = bc.read_b()
        decoded['DIMTIH'] = bc.read_b()
        decoded['DIMTOH'] = bc.read_b()
        decoded['DIMSE1'] = bc.read_b()
        decoded['DIMSE2'] = bc.read_b()

        decoded['DIMTAD'] = bc.read_bs()
        decoded['DIMZIN'] = bc.read_bs()
        decoded['DIMAZIN'] = bc.read_bs()

        if DWGVersion.R21 <= self.dwg_version:
            decoded['DIMARCSYM'] = bc.read_bs()

        decoded['DIMTXT'] = bc.read_bd()
        decoded['DIMCEN'] = bc.read_bd()
        decoded['DIMTSZ'] = bc.read_bd()
        decoded['DIMALTF'] = bc.read_bd()
        decoded['DIMLFAC'] = bc.read_bd()
        decoded['DIMTVP'] = bc.read_bd()
        decoded['DIMTFAC'] = bc.read_bd()
        decoded['DIMGAP'] = bc.read_bd()

        decoded['DIMALTRND'] = bc.read_bd()
        decoded['DIMALT'] = bc.read_b()
        decoded['DIMALTD'] = bc.read_bs()
        decoded['DIMTOFL'] = bc.read_b()
        decoded['DIMSAH'] = bc.read_b()
        decoded['DIMTIX'] = bc.read_b()
        decoded['DIMSOXD'] = bc.read_b()

        decoded['DIMCLRD'] = bc.read_cmc()
        decoded['DIMCLRE'] = bc.read_cmc()
        decoded['DIMCLRT'] = bc.read_cmc()

        decoded['DIMADEC'] = bc.read_bs()
        decoded['DIMDEC'] = bc.read_bs()
        decoded['DIMTDEC'] = bc.read_bs()
        decoded['DIMALTU'] = bc.read_bs()
        decoded['DIMALTTD'] = bc.read_bs()

        decoded['DIMAUNIT'] = bc.read_bs()
        decoded['DIMFRAC'] = bc.read_bs()
        decoded['DIMLUNIT'] = bc.read_bs()
        decoded['DIMDSEP'] = bc.read_bs()
        decoded['DIMTMOVE'] = bc.read_bs()
        decoded['DIMJUST'] = bc.read_bs()

        decoded['DIMSD1'] = bc.read_b()
        decoded['DIMSD2'] = bc.read_b()

        decoded['DIMTOLJ'] = bc.read_bs()
        decoded['DIMTZIN'] = bc.read_bs()
        decoded['DIMALTZ'] = bc.read_bs()
        decoded['DIMALTTZ'] = bc.read_bs()

        decoded['DIMUPT'] = bc.read_b()
        decoded['DIMATFIT'] = bc.read_bs()

        if DWGVersion.R21 <= self.dwg_version:
            decoded['DIMFXLON'] = bc.read_b()

        if DWGVersion.R24 <= self.dwg_version:
            decoded['DIMTXTDIRECTION'] = bc.read_b()
            decoded['DIMALTMZF'] = bc.read_bd()
            decoded['DIMALTMZS'] = bc.read_tv()
            decoded['DIMMZF'] = bc.read_bd()
            decoded['DIMMZS'] = bc.read_tv()

        decoded['DIMTXTSTY'] = bc.read_h()
        decoded['DIMLDRBLK'] = bc.read_h()
        decoded['DIMBLK'] = bc.read_h()
        decoded['DIMBLK1'] = bc.read_h()
        decoded['DIMBLK2'] = bc.read_h()

        if DWGVersion.R21 <= self.dwg_version:
            decoded['DIMLTYPE'] = bc.read_h()
            decoded['DIMLTEX1'] = bc.read_h()
            decoded['DIMLTEX2'] = bc.read_h()

        decoded['DIMLWD'] = bc.read_bs()
        decoded['DIMLWE'] = bc.read_bs()

        decoded['BLOCK_CONTROL_OBJECT'] = bc.read_h()
        decoded['LAYER_CONTROL_OBJECT'] = bc.read_h()
        decoded['STYLE_CONTROL_OBJECT'] = bc.read_h()
        decoded['LINETYPE_CONTROL_OBJECT'] = bc.read_h()
        decoded['VIEW_CONTROL_OBJECT'] = bc.read_h()

        decoded['UCS_CONTROL_OBJECT'] = bc.read_h()
        decoded['VPORT_CONTROL_OBJECT'] = bc.read_h()
        decoded['APPID_CONTROL_OBJECT'] = bc.read_h()
        decoded['DIMSTYLE_CONTROL_OBJECT'] = bc.read_h()

        decoded['DICTIONARY_ACAD_GROUP'] = bc.read_h()
        decoded['DICTIONARY_ACAD_MLINESTYLE'] = bc.read_h()
        decoded['DICTIONARY_NAMED_OBJECTS'] = bc.read_h()

        decoded['TSTACKALIGN'] = bc.read_bs()  # 1?
        decoded['TSTACKSIZE'] = bc.read_bs()   # 70?

        decoded['HYPERLINKBASE'] = bc.read_tv()
        decoded['STYLESHEET'] = bc.read_tv()
        decoded['DICTIONARY_LAYOUTS'] = bc.read_h()
        decoded['DICTIONARY_PLOTSETTINGS'] = bc.read_h()
        decoded['DICTIONARY_PLOTSTYLES'] = bc.read_h()

        decoded['DICTIONARY_MATERIALS'] = bc.read_h()
        decoded['DICTIONARY_COLORS'] = bc.read_h()

        if DWGVersion.R21 <= self.dwg_version:
            decoded['DICTIONARY_VISUALSTYLE'] = bc.read_h()

        if DWGVersion.R27 <= self.dwg_version:
            uk = bc.read_h()

        decoded['FLAGS'] = bc.read_bl()
        decoded['INSUNITS'] = bc.read_bs()

        value = decoded['CEPSNTYPE'] = bc.read_bs()
        if value == 3:
            decoded['CPSNID'] = bc.read_h()

        decoded['FINGERPRINTGUID'] = bc.read_tv()
        decoded['VERSIONGUID'] = bc.read_tv()

        decoded['SORTENTS'] = bc.read_rc()
        decoded['IDEXCTL'] = bc.read_rc()
        decoded['HIDETEXT'] = bc.read_rc()
        decoded['XCLIPFRAME'] = bc.read_rc()
        decoded['DIMASSOC'] = bc.read_rc()
        decoded['HALOGAP'] = bc.read_rc()

        decoded['OBSCUREDCOLOR'] = bc.read_bs()
        decoded['INTERSECTIONCOLOR'] = bc.read_bs()
        decoded['OBSCUREDLTYPE'] = bc.read_rc()
        decoded['INTERSECTIONDISPLAY'] = bc.read_rc()
        decoded['PROJECTNAME'] = bc.read_tv()

        decoded['BLOCK_RECORD_PAPER_SPACE'] = bc.read_h()
        decoded['BLOCK_RECORD_MODEL_SPACE'] = bc.read_h()
        decoded['LTYPE_BYLAYER'] = bc.read_h()
        decoded['LTYPE_BYBLOCK'] = bc.read_h()
        decoded['LTYPE_CONTINUOUS'] = bc.read_h()

        if DWGVersion.R21 <= self.dwg_version:
            decoded['CAMERADISPLAY'] = bc.read_b()
            uk = bc.read_bl()
            uk = bc.read_bl()
            uk = bc.read_bd()
            decoded['STEPSPERSEC'] = bc.read_bd()
            decoded['STEPSIZE'] = bc.read_bd()
            decoded['3DDWFPREC'] = bc.read_bd()
            decoded['LENSLENGTH'] = bc.read_bd()
            decoded['CAMERAHEIGHT'] = bc.read_bd()
            decoded['SOLIDHIST'] = bc.read_rc()
            decoded['SHOWHIST'] = bc.read_rc()
            decoded['PSOLWIDTH'] = bc.read_bd()
            decoded['PSOLHEIGHT'] = bc.read_bd()
            decoded['LOFTANG1'] = bc.read_bd()
            decoded['LOFTANG2'] = bc.read_bd()
            decoded['LOFTMAG1'] = bc.read_bd()
            decoded['LOFTMAG2'] = bc.read_bd()
            decoded['LOFTPARAM'] = bc.read_bs()
            decoded['LOFTNORMALS'] = bc.read_rc()
            decoded['LATITUDE'] = bc.read_bd()
            decoded['LONGITUDE'] = bc.read_bd()
            decoded['NORTHDIRECTION'] = bc.read_bd()
            decoded['TIMEZONE'] = bc.read_bl()
            decoded['LIGHTGLYPHDISPLAY'] = bc.read_rc()
            decoded['TILEMODELIGHTSYNCH'] = bc.read_rc()
            decoded['DWFFRAME'] = bc.read_rc()
            decoded['DGNFRAME'] = bc.read_rc()
            uk = bc.read_b()
            decoded['INTERFERECOLOR'] = bc.read_cmc()
            decoded['INTERFEREOBJVS'] = bc.read_h()
            decoded['INTERFEREVPVS'] = bc.read_h()
            decoded['DRAGVS'] = bc.read_h()
            decoded['CSHADOW'] = bc.read_rc()
            uk = bc.read_bd()

        uk = bc.read_bs()
        uk = bc.read_bs()
        uk = bc.read_bs()
        uk = bc.read_bs()

        decoded['crc'] = bc.read_crc()

        sn = bc.read_sn()
        if DWG_SENTINEL_HEADER_AFTER != sn:
            msg = "[{}] DWG_SENTINEL_HEADER_AFTER mis-match.".format(DWGSectionName.HEADER.value)
            self.logger.debug("{}(): {}".format(GET_MY_NAME(), msg))
            self.report.add(DWGVInfo(DWGVType.SYNTAX_ERROR, bc.pos_byte-len(sn), len(sn), msg))

        # Check CRC value
        # v = self.utils.check_crc8(data[16:16+4+decoded['size']],
        #                           0xC0C1,
        #                           decoded['crc'])
        # if v is False:
        #     print("[ALERT] Abnormal point - Header section's data - CRC check failed")
        # else:
        #     print("[Header section's data] CRC verified")
        return decoded

    def classes(self, section):
        """Decode defined classes from the 'AcDb:Classes' section

        Args:
            section (dict): section dictionary {'header', 'data'}

        Returns:
            list of decoded classes
        """
        self.logger.info("{}(): Decode data stream.".format(GET_MY_NAME()))

        decoded = dict()

        data = section.get('data')
        if len(data) == 0:
            self.logger.debug("{}(): Data is empty.".format(GET_MY_NAME()))
            return decoded

        bc = DWGBitCodes(data, len(data))

        sn = bc.read_sn()
        if DWG_SENTINEL_CLASSES_BEFORE != sn:
            msg = "[{}] DWG_SENTINEL_CLASSES_BEFORE mis-match.".format(DWGSectionName.CLASSES.value)
            self.logger.debug("{}(): {}".format(GET_MY_NAME(), msg))
            self.report.add(DWGVInfo(DWGVType.SYNTAX_ERROR, 0, len(sn), msg))
            return decoded

        decoded['size'] = bc.read_rl()  # excluding itself (4 bytes) and crc (2 bytes)

        if DWGVersion.R21 <= self.dwg_version:
            # only present if the maintenance version is greater than 3 ?
            decoded['end_bit'] = bc.read_rl()

        decoded['max_class_number'] = bc.read_bs()
        uk = bc.read_rc()  # 0x00
        uk = bc.read_rc()  # 0x00
        uk = bc.read_b()   # true

        # Get string stream data (UNICODE strings)
        #   - Open Design Specification for .dwg files v5.3 (page 99)
        #   - Below code is not fully implemented.
        if DWGVersion.R21 <= self.dwg_version:
            # Check the string stream present flag
            pos_byte_bak, pos_bit_bak = bc.get_pos()  # Backup the current position
            base_offset = 20  # SN (16 bytes) + size (4 bytes)
            new_end_bit = decoded['end_bit'] - 1
            bc.set_bit_pos(base_offset*8 + new_end_bit)
            string_stream_present_flag = bc.read_b()
            bc.set_pos(pos_byte_bak, pos_bit_bak)  # Restore the saved position
        #
        #     if string_stream_present_flag is True:
        #         # Get the start position of string stream
        #         pos_byte_bak, pos_bit_bak = bc.get_pos()  # Backup the current position
        #         new_end_bit = decoded['end_bit'] - 128  # 16 bytes * 8
        #         bc.set_bit_pos(base_offset*8 + new_end_bit)
        #
        #         str_data_size = bc.read_rs()  # bs?
        #         if str_data_size & 0x8000 == 0x8000:
        #             str_data_size &= ~0x8000
        #             new_end_bit -= 16*8
        #             bc.set_bit_pos(base_offset*8 + new_end_bit)
        #             hi_size = bc.read_rs()  # bs?
        #             str_data_size = (str_data_size | (hi_size << 15))
        #
        #         # new_end_bit -= (str_data_size * 8)
        #         new_end_bit = decoded['end_bit'] - (str_data_size * 8)
        #         bc.set_bit_pos(base_offset*8 + new_end_bit)
        #
        #         # stream = bc.read_rcs(str_data_size)
        #         # self.utils.print_hex_bytes(stream)
        #         # temp_bc = DWGBitCodes(stream, len(stream))
        #         # temp = temp_bc.read_tu()
        #         bc.set_pos(pos_byte_bak, pos_bit_bak)  # Restore the saved position

        decoded['classes'] = []

        while bc.pos_byte <= decoded['size']:
            class_data = OrderedDict()
            class_data['class_number'] = bc.read_bs()
            class_data['proxy_flags'] = bc.read_bs()

            if DWGVersion.R21 <= self.dwg_version:
                class_data['app_name'] = ""
                class_data['cpp_name'] = ""
                class_data['dxf_name'] = ""
            else:
                class_data['app_name'] = bc.read_tv()
                class_data['cpp_name'] = bc.read_tv()
                class_data['dxf_name'] = bc.read_tv()

            class_data['was_a_zombie'] = bc.read_b()
            class_data['item_class_id'] = bc.read_bs()  # 0x1F2 = entity, 0x1F3 = object
            class_data['number_of_objects'] = bc.read_bl()

            if DWGVersion.R21 <= self.dwg_version:
                class_data['dwg_version'] = bc.read_bl()
                class_data['maintenance_version'] = bc.read_bl()
            else:
                class_data['dwg_version'] = bc.read_bs()
                class_data['maintenance_version'] = bc.read_bs()

            uk = bc.read_bl()  # unknown (normally 0)
            uk = bc.read_bl()  # unknown (normally 0)
            decoded['classes'].append(class_data)

            if decoded['max_class_number'] == class_data['class_number']:
                break

        # stream = bc.read_rcs(bc.size - bc.pos_byte)
        # self.utils.print_hex_bytes(stream)

        # Get UNICODE strings
        # (this will be replaced when we can get the start position of string stream)
        if DWGVersion.R21 <= self.dwg_version:
            if string_stream_present_flag == 1:
                for class_data in decoded.get('classes'):
                    class_data['app_name'] = bc.read_tu()
                    class_data['cpp_name'] = bc.read_tu()
                    class_data['dxf_name'] = bc.read_tu()
                base_offset = 20  # SN (16 bytes) + size (4 bytes)
                new_end_bit = decoded['end_bit']
                bc.set_bit_pos(base_offset*8 + new_end_bit)

        decoded['crc'] = bc.read_crc()

        sn = bc.read_sn()
        if DWG_SENTINEL_CLASSES_AFTER != sn:
            msg = "[{}] DWG_SENTINEL_CLASSES_AFTER mis-match.".format(DWGSectionName.CLASSES.value)
            self.logger.debug("{}(): {}".format(GET_MY_NAME(), msg))
            self.report.add(DWGVInfo(DWGVType.SYNTAX_ERROR, bc.pos_byte-len(sn), len(sn), msg))

        # Check slack areas
        slack_offset = bc.pos_byte
        slack_length = len(data)-bc.pos_byte
        for idx in range(slack_length):
            if bc.read_rc() != 0x00:
                msg = "[{}] Found data in slack area.".format(DWGSectionName.FILEDEPLIST.value)
                self.logger.debug("{}(): {}".format(GET_MY_NAME(), msg))
                self.report.add(DWGVInfo(DWGVType.UNUSED_AREA, slack_offset, slack_length, msg))

        return decoded

    def security(self, section):
        """Decode the security info. from the 'AcDb:Security' section

        Args:
            section (dict): section dictionary
                            {'header', 'data'}
        Returns:
            Decoding results (dict)
            {
                feature_count (int)
                feature_name (list): str
                file_count (int)
                files (list): dict { filename, dirpath, fingerprint_guid, version_guid,
                                     feature_index (int), timestamp, filesize (int),
                                     affects_graphics (bool), reference_count (int) }
            }
        """
        self.logger.info("{}(): Decode data stream.".format(GET_MY_NAME()))

        decoded = dict()

        data = section.get('data')
        if len(data) == 0:
            self.logger.debug("{}(): Data is empty.".format(GET_MY_NAME()))
            return decoded

        bc = DWGBitCodes(data, len(data))

        unknown = bc.read_rl()
        unknown = bc.read_rl()
        decoded['signature'] = bc.read_rcs(4)  # 0xABCDABCD
        decoded['crypto_provider_id'] = bc.read_rl()
        value = bc.read_rcs(bc.read_rl())
        decoded['crypto_provider_name'] = value.decode('UTF-16LE', 'ignore')
        decoded['algorithm_id'] = bc.read_rl()
        decoded['key_length'] = bc.read_rl()
        buf_length = bc.read_rl()
        decoded['test_encrypted_sequence'] = bc.read_rcs(buf_length)  # 'SamirBajajSamirB'

        # Test code for verifying the user-password (later time)
        # pw = '12321'
        # pw = pw.encode('UTF-16LE')

        # Check slack areas
        slack_offset = bc.pos_byte
        slack_length = len(data)-bc.pos_byte
        for idx in range(slack_length):
            if bc.read_rc() != 0x00:
                msg = "[{}] Found data in slack area.".format(DWGSectionName.FILEDEPLIST.value)
                self.logger.debug("{}(): {}".format(GET_MY_NAME(), msg))
                self.report.add(DWGVInfo(DWGVType.UNUSED_AREA, slack_offset, slack_length, msg))

        return decoded

    def template(self, section):
        """Decode the measurement system variables from the 'AcDb:Template' section

        Args:
            section (dict): section dictionary
                            {'header', 'data'}
        Returns:
            Decoding results (dict)
            {
                encoded_bytes (bytes)
                measurement_variable (int)
            }
        """
        self.logger.info("{}(): Decode data stream.".format(GET_MY_NAME()))

        decoded = dict()

        data = section.get('data')
        if len(data) == 0:
            self.logger.debug("{}(): Data is empty.".format(GET_MY_NAME()))
            return decoded

        bc = DWGBitCodes(data, len(data))

        length = bc.read_rs()
        decoded['encoded_bytes'] = bc.read_rcs(length)  # use the drawing’s codepage to encode the bytes
        decoded['measurement_variable'] = bc.read_rs()  # 0: English, 1: Metric

        # Check slack areas
        slack_offset = bc.pos_byte
        slack_length = len(data)-bc.pos_byte
        for idx in range(slack_length):
            if bc.read_rc() != 0x00:
                msg = "[{}] Found data in slack area.".format(DWGSectionName.FILEDEPLIST.value)
                self.logger.debug("{}(): {}".format(GET_MY_NAME(), msg))
                self.report.add(DWGVInfo(DWGVType.UNUSED_AREA, slack_offset, slack_length, msg))

        return decoded

    def vbaproject(self, section):
        self.logger.info("{}(): not yet implemented.".format(GET_MY_NAME()))
        return

    def revhistory(self, section):
        self.logger.info("{}(): not yet implemented.".format(GET_MY_NAME()))
        return

    def objfreespace(self, section):
        self.logger.info("{}(): not yet implemented.".format(GET_MY_NAME()))
        return

    def signature(self, section):
        self.logger.info("{}(): not yet implemented.".format(GET_MY_NAME()))
        return

