# -*- coding: utf-8 -*-

"""@package pydwg

    * Description
        DWGObject - DWG object parser
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
from ctypes import *
from .dwg_common import *
from .dwg_utils import *
from .dwg_bit_codes import *
from .dwg_report import *


class DWGObject:
    """DWGObject class
    """

    def __init__(self, version, report):
        """The constructor"""
        self.dwg_version = version
        self.utils = DWGUtils()
        self.bc = DWGBitCodes(None, 0)
        self.classes = []

        # The current object's class
        self.obj_type = 0x00
        self.obj_name = ""
        self.obj_class = DWGObjectTypeClass.UNUSED.value

        self.logger = logging.getLogger(__name__)
        self.report = report
        return

    def set_classes(self, classes):
        self.classes = classes

    def decode(self, buf, pos_bit, size):
        """Decode a DWG entity or object

        Args:
            buf (bytes): Data buffer
            pos_bit (int): The current bit position
            size (int): Size of buf
        Returns:
            Result dict
        """
        self.bc = DWGBitCodes(buf, size, pos_bit=pos_bit)

        obj = dict()
        self.obj_type = obj['type'] = self.bc.read_bs()

        # call the decoder function for 'type'
        func_name = self.utils.get_object_name(self.obj_type, self.classes)
        if func_name == '' or func_name == "UNUSED":
            return None

        self.obj_name  = obj['name'] = func_name
        self.obj_class = obj['class'] = self.utils.get_object_class(self.obj_type, self.classes)

        try:
            decode_object = getattr(self, func_name)
        except:
            decode_object = getattr(self, "default")

        obj.update(decode_object())
        return obj

    '''
    -------------------------------------------------------------
    DECODERS FOR OBJECTS (Entity or Object)
    -------------------------------------------------------------
    '''

    def TEXT(self):
        """Parse TEXT (0x01, 1) entity

        @return     Parsing results (Dict.)
                    -------------------------
                    COMMON_ENTITY_HEADER
                    -------------------------
                    ALL
                        data_flags (RC)
                        elevation (RD)              if not (data_flags & 0x01)
                        insertion_pt (2RD)
                        alignment_pt (2RD)          if not (data_flags & 0x02)
                        extrusion (BE)
                        thickness (BT)
                        oblique_ang (RD)            if not (data_flags & 0x04)
                        rotation_ang (RD)           if not (data_flags & 0x08)
                        height (RD)
                        width_factor (RD)           if not (data_flags & 0x10)
                        text (tv)
                        generation (BS)             if not (data_flags & 0x20)
                        horizontal_alignment (BS)   if not (data_flags & 0x40)
                        vertical_alignment (BS)     if not (data_flags & 0x80)
                    -------------------------
                    COMMON_ENTITY_HANDLE_DATA
                    -------------------------
                    ALL
                        handle_style (H)            (code 5: hard pointer)
                    -------------------------
                    CRC
                    -------------------------
        """
        obj = dict()
        obj.update(self.common_entity_header())
        if obj['handle'] is None:
            return obj

        flags = obj['data_flags'] = self.bc.read_rc()

        if not (flags & 0x01):
            obj['elevation'] = self.bc.read_rd()

        obj['insertion_pt'] = self.bc.read_2rd()

        if not (flags & 0x02):
            obj['alignment_pt'] = self.bc.read_2dd(10, 20)

        obj['extrusion'] = self.bc.read_be()
        obj['thickness'] = self.bc.read_bt()

        if not (flags & 0x04):
            obj['oblique_ang'] = self.bc.read_rd()

        if not (flags & 0x08):
            obj['rotation_ang'] = self.bc.read_rd()

        obj['height'] = self.bc.read_rd()

        if not (flags & 0x10):
            obj['width_factor'] = self.bc.read_rd()

        obj['text'] = self.bc.read_tv() if self.dwg_version < DWGVersion.R21 else self.bc.read_tu()

        if not (flags & 0x20):
            obj['generation'] = self.bc.read_bs()

        if not (flags & 0x40):
            obj['horizontal_alignment'] = self.bc.read_bs()

        if not (flags & 0x80):
            obj['vertical_alignment'] = self.bc.read_bs()

        self.bc.set_bit_pos(obj['obj_size'])
        obj.update(self.common_entity_handle_data(obj))

        obj['handle_style'] = self.bc.read_h()
        obj['crc'] = self.bc.read_crc()
        return obj

    def MTEXT(self):
        """Parse MTEXT (0x2C, 44) entity

        @return     Parsing results (Dict.)
                    -------------------------
                    COMMON_ENTITY_HEADER
                    -------------------------
                    ALL
                        insertion_pt (3BD)
                        extrusion (3BD)
                        x_axis_dir (3BD)
                        rect_width (BD)
                    R21+
                        rect_height (BD)
                    ALL
                        text_height (BD)
                        attachment (BS)
                        drawing_dir (BS)
                        extents_ht (BD)
                        extents_wid (BD)
                        text (TV)
                        linespacing_style (BS)
                        linespacing_factor (BD)
                        unknown_bit (B)
                        background_flags (BL)           0: no bg, 1: bg fill, 2: bh fill with drawing fill color
                        background_scale_factor (BD)    if background_flags == 1, default = 1.5
                        background_color (CMC)          if background_flags == 1
                        background_transparency (BL)    if background_flags == 1
                    -------------------------
                    COMMON_ENTITY_HANDLE_DATA
                    -------------------------
                    ALL
                        handle_style (H)            (code 5: hard pointer)
                    -------------------------
                    CRC
                    -------------------------
        """
        obj = dict()
        obj.update(self.common_entity_header())

        obj['insertion_pt'] = self.bc.read_3bd()
        obj['extrusion'] = self.bc.read_3bd()
        obj['x_axis_dir'] = self.bc.read_3bd()
        obj['rect_width'] = self.bc.read_bd()

        if DWGVersion.R21 <= self.dwg_version:
            obj['rect_height'] = self.bc.read_bd()

        obj['text_height'] = self.bc.read_bd()
        obj['attachment'] = self.bc.read_bs()
        obj['drawing_dir'] = self.bc.read_bs()
        obj['extents_ht'] = self.bc.read_bd()
        obj['extents_wid'] = self.bc.read_bd()

        obj['text'] = self.bc.read_tv() if self.dwg_version < DWGVersion.R21 else self.bc.read_tu()

        obj['linespacing_style'] = self.bc.read_bs()
        obj['linespacing_factor'] = self.bc.read_bd()
        obj['unknown_bit'] = self.bc.read_b()

        flags = obj['background_flags'] = self.bc.read_bl()
        if flags == 1:
            obj['background_scale_factor'] = self.bc.read_bd()  # spec is wrong (BL -> BD)
            obj['background_color'] = self.bc.read_cmc()
            obj['background_transparency'] = self.bc.read_bl()

        self.bc.set_bit_pos(obj['obj_size'])
        obj.update(self.common_entity_handle_data(obj))

        obj['handle_style'] = self.bc.read_h()
        obj['crc'] = self.bc.read_crc()
        return obj

    def BLOCK(self):
        """Parse BLOCK (0x04, 4) entity

        @return     Parsing results (Dict.)
                    -------------------------
                    COMMON_ENTITY_HEADER
                    -------------------------
                    ALL
                        block_name (tv)
                    -------------------------
                    COMMON_ENTITY_HANDLE_DATA
                    CRC
                    -------------------------
        """
        obj = dict()
        obj.update(self.common_entity_header())
        if obj['handle'] is None:
            return obj

        obj['block_name'] = self.bc.read_tv() if self.dwg_version < DWGVersion.R21 else self.bc.read_tu()
        self.bc.set_bit_pos(obj['obj_size'])
        obj.update(self.common_entity_handle_data(obj))
        obj['crc'] = self.bc.read_crc()
        return obj

    def ENDBLK(self):
        """Parse ENDBLK (0x05, 5) entity

        @return     Parsing results (Dict.)
                    -------------------------
                    COMMON_ENTITY_HEADER
                    COMMON_ENTITY_HANDLE_DATA
                    CRC
                    -------------------------
        """
        obj = dict()
        obj.update(self.common_entity_header())
        if obj['handle'] is None:
            return obj

        obj.update(self.common_entity_handle_data(obj))
        obj['crc'] = self.bc.read_crc()
        return obj

    def INSERT(self):
        """Parse INSERT (0x07, 7) entity

        @return     Parsing results (Dict.)
                    -------------------------
                    COMMON_ENTITY_HEADER
                    -------------------------
                    ALL
                        position (3BD)
                        data_flags (BB)
                            if data_flags == 0x03
                                x_scale = 1.0
                                y_scale = 1.0
                                z_scale = 1.0
                            elif data_flags == 0x01
                                x_scale = 1.0
                                y_scale (DD) with 1.0
                                z_scale (DD) with 1.0
                            elif data_flags == 0x02
                                x_scale (RD)
                                y_scale = x_scale
                                z_scale = x_scale
                            elif data_flags == 0x00
                                x_scale (RD)
                                y_scale (DD) with x_scale
                                z_scale (DD) with x_scale
                        rotation (BD)
                        extrusion (3BD)
                        has_attribs (B)
                            if has_attribs is 1
                                owned_obj_count (BL)
                    -------------------------
                    COMMON_ENTITY_HANDLE_DATA
                    -------------------------
                    ALL
                        handle_block_header (code 5: hard pointer)
                        if has_attribs is 1
                            handle_owned   (code 3: hard owner) <- repeats "owned_obj_count" times
                            handle_seqend  (code 3: hard owner)
                    -------------------------
                    CRC
                    -------------------------
        """
        obj = dict()
        obj.update(self.common_entity_header())
        if obj['handle'] is None:
            return obj

        obj['position'] = self.bc.read_3bd()
        obj['data_flags'] = self.bc.read_bb()
        if obj['data_flags'] == 0x03:
            obj['x_scale'] = 1.0
            obj['y_scale'] = 1.0
            obj['z_scale'] = 1.0
        elif obj['data_flags'] == 0x01:
            obj['x_scale'] = 1.0
            obj['y_scale'] = self.bc.read_dd(1.0)
            obj['z_scale'] = self.bc.read_dd(1.0)
        elif obj['data_flags'] == 0x02:
            obj['x_scale'] = self.bc.read_rd()
            obj['y_scale'] = obj['x_scale']
            obj['z_scale'] = obj['x_scale']
        else:
            obj['x_scale'] = self.bc.read_rd()
            obj['y_scale'] = self.bc.read_dd(obj['x_scale'])
            obj['z_scale'] = self.bc.read_dd(obj['x_scale'])

        obj['rotation'] = self.bc.read_bd()
        obj['extrusion'] = self.bc.read_3bd()
        obj['has_attribs'] = self.bc.read_b()
        obj['owned_obj_count'] = 0
        if obj['has_attribs'] == 1:
            obj['owned_obj_count'] = self.bc.read_bl()

        self.bc.set_bit_pos(obj['obj_size'])  # Skip the string stream
        obj.update(self.common_entity_handle_data(obj))

        h = self.decode_handle_reference(obj.get('handle'), DWGHandleCode.HARD_POINTER)
        obj['handle_block_header'] = h

        if obj.get('has_attribs') == 1:
            obj['handle_owned'] = []
            for idx in range(obj.get('owned_obj_count')):
                h = self.decode_handle_reference(obj.get('handle'), DWGHandleCode.HARD_OWNERSHIP)
                obj['handle_owned'].append(h)
            h = self.decode_handle_reference(obj.get('handle'), DWGHandleCode.HARD_OWNERSHIP)
            obj['handle_seqend'] = h

        obj['crc'] = self.bc.read_crc()
        return obj

    def POLYLINE_2D(self):
        """Parse POLYLINE_2D (0x0F, 15) entity

        @return     Parsing results (Dict.)
                    -------------------------
                    COMMON_ENTITY_HEADER
                    -------------------------
                    ALL
                        flags       (BS)
                        curve_type  (BS)
                        width_start (BD)
                        width_end   (BD)
                        thickness   (BT)
                        elevation   (BD)
                        extrusion   (BE)
                        owned_obj_count (BL)
                    -------------------------
                    COMMON_ENTITY_HANDLE_DATA
                    -------------------------
                    ALL
                        handle_owned (code 3: hard owner) <- repeats "owned_obj_count" times
                    -------------------------
                    CRC
                    -------------------------
        """
        obj = dict()
        obj.update(self.common_entity_header())
        if obj['handle'] is None:
            return obj

        obj['flags'] = self.bc.read_bs()
        obj['curve_type'] = self.bc.read_bs()
        obj['width_start'] = self.bc.read_bd()
        obj['width_end'] = self.bc.read_bd()
        obj['thickness'] = self.bc.read_bt()
        obj['elevation'] = self.bc.read_bd()
        obj['extrusion'] = self.bc.read_be()
        obj['owned_obj_count'] = self.bc.read_bl()
        obj.update(self.common_entity_handle_data(obj))

        obj['handle_owned'] = []
        for idx in range(obj.get('owned_obj_count')):
            h = self.decode_handle_reference(obj.get('handle'), DWGHandleCode.HARD_OWNERSHIP)
            obj['handle_owned'].append(h)

        obj['crc'] = self.bc.read_crc()
        return obj

    # def POLYLINE_3D(self):
    #     """Parse POLYLINE_3D (0x10, 16) entity
    #
    #     @return     Parsing results (Dict.)
    #     """
    #
    #     return True

    def ARC(self):
        """Parse ARC (0x11, 17) entity

        @return     Parsing results (Dict.)
                    -------------------------
                    COMMON_ENTITY_HEADER
                    -------------------------
                    ALL
                        center      (3BD)
                        radius      (BD)
                        thickness   (BT)
                        extrusion   (BE)
                        angle_start (BD)
                        angle_end   (BD)
                    -------------------------
                    COMMON_ENTITY_HANDLE_DATA
                    CRC
                    -------------------------
        """
        obj = dict()
        obj.update(self.common_entity_header())
        if obj['handle'] is None:
            return obj

        obj['center'] = self.bc.read_3bd()
        obj['radius'] = self.bc.read_bd()
        obj['thickness'] = self.bc.read_bt()
        obj['extrusion'] = self.bc.read_be()
        obj['angle_start'] = self.bc.read_bd()
        obj['angle_end'] = self.bc.read_bd()
        obj.update(self.common_entity_handle_data(obj))
        obj['crc'] = self.bc.read_crc()
        return obj

    def CIRCLE(self):
        """Parse CIRCLE (0x12, 18) entity

        @return     Parsing results (Dict.)
                    -------------------------
                    COMMON_ENTITY_HEADER
                    -------------------------
                    ALL
                        center    (3BD)
                        radius    (BD)
                        thickness (BT)
                        extrusion (BE)
                    -------------------------
                    COMMON_ENTITY_HANDLE_DATA
                    CRC
                    -------------------------
        """
        obj = dict()
        obj.update(self.common_entity_header())
        if obj['handle'] is None:
            return obj

        obj['center'] = self.bc.read_3bd()
        obj['radius'] = self.bc.read_bd()
        obj['thickness'] = self.bc.read_bt()
        obj['extrusion'] = self.bc.read_be()
        obj.update(self.common_entity_handle_data(obj))
        obj['crc'] = self.bc.read_crc()
        return obj

    def LINE(self):
        """Parse LINE (0x13, 19) entity

        @return     Parsing results (Dict.)
                    -------------------------
                    COMMON_ENTITY_HEADER
                    -------------------------
                    ALL
                        z_is_zero_bit (B)
                        x_start (RD)
                        x_end   (DD)    # x_start for default
                        y_start (RD)
                        y_end   (DD)    # y_start for default
                        z_start (RD)    # only if z_is_zero_bit == 0
                        z_end   (DD)    # only if z_is_zero_bit == 0

                        thickness (BT)
                        extrusion (BE)
                    -------------------------
                    COMMON_ENTITY_HANDLE_DATA
                    CRC
                    -------------------------
        """
        obj = dict()
        obj.update(self.common_entity_header())
        if obj['handle'] is None:
            return obj

        obj['z_is_zero_bit'] = self.bc.read_b()
        obj['x_start'] = self.bc.read_rd()
        obj['x_end']   = self.bc.read_dd(obj['x_start'])
        obj['y_start'] = self.bc.read_rd()
        obj['y_end']   = self.bc.read_dd(obj['y_start'])

        if obj['z_is_zero_bit'] == 0:
            obj['z_start'] = self.bc.read_rd()
            obj['z_end']   = self.bc.read_dd(obj['z_start'])

        obj['thickness'] = self.bc.read_bt()
        obj['extrusion'] = self.bc.read_be()

        obj.update(self.common_entity_handle_data(obj))
        obj['crc'] = self.bc.read_crc()
        return obj

    # def POLYLINE_PFACE(self):
    #     """Parse POLYLINE_PFACE entity
    #
    #     @return     Parsing results (Dict.)
    #     """
    #     return True

    # def POLYLINE_MESH(self):
    #     """Parse POLYLINE_MESH entity
    #
    #     @return     Parsing results (Dict.)
    #     """
    #     return True

    # def LWPOLYLINE(self):
    #     """Parse LWPOLYLINE (0x4D, 77) entity
    #
    #     @return     Parsing results (Dict.)
    #     """
    #     obj = dict()
    #     obj.update(self.common_entity_header())
    #     return obj

    def DICTIONARY(self):
        """Parse DICTIONARY (0x2A, 42) object

        @return     Parsing results (Dict.)
                    -------------------------
                    COMMON_OBJECT_HEADER
                    -------------------------
                    ALL
                        num_of_entries (BL)
                        cloning flag (BS)
                        hard_owner_flag (RC)
                        entry_name (TV)
                        handle_parent       (code 4: soft pointer)
                        handle_reactors     (code 4: soft pointer) -> 'num_of_reactors'
                        handle_xdic_obj     (code 3: hard owner)   only if 'xdic_missing_flag' is 1
                        handle_owned        (code 4: soft pointer) -> 'num_of_entries'
                    -------------------------
                    CRC
                    -------------------------
        """
        obj = dict()
        obj.update(self.common_object_header())
        if obj['handle'] is None:
            return obj

        obj['num_of_entries'] = self.bc.read_bl()
        obj['cloning'] = self.bc.read_bs()
        obj['hard_owner_flag'] = self.bc.read_rc()

        obj['entry_name'] = []
        for idx in range(obj.get('num_of_entries')):
            name = self.bc.read_tv() if self.dwg_version < DWGVersion.R21 else ""
            obj['entry_name'].append(name)

        if DWGVersion.R21 <= self.dwg_version:
            self.bc.set_bit_pos(obj['obj_size'])  # Skip the string stream

        h = self.decode_handle_reference(obj.get('handle'), DWGHandleCode.SOFT_POINTER)
        obj['handle_parent'] = h

        obj['handle_reactors'] = []
        for idx in range(obj.get('num_of_reactors')):
            h = self.decode_handle_reference(obj.get('handle'), DWGHandleCode.SOFT_POINTER)
            obj['handle_reactors'].append(h)

        if obj.get('xdic_missing_flag') == 0:
            obj['handle_xdic_obj'] = self.decode_handle_reference(obj.get('handle'),
                                                                  DWGHandleCode.HARD_OWNERSHIP)
        # obj['handle_owned'] = []
        # for idx in range(obj.get('num_of_entries')):
        #     h = self.decode_handle_reference(obj.get('handle'), DWGHandleCode.SOFT_OWNERSHIP)
        #     obj['handle_owned'].append(h)
        #
        # obj['crc'] = self.bc.read_crc()
        return obj

    def BLOCK_CONTROL(self):
        """Parse BLOCK_CONTROL (0x30, 48) object

        @return     Parsing results (Dict.)
                    -------------------------
                    COMMON_OBJECT_HEADER
                    -------------------------
                    ALL
                        num_of_entries (BL)
                        handle_null         (code 4: soft pointer)
                        handle_xdic_obj     (code 3: hard owner)   only if 'xdic_missing_flag' is 1
                        handle_owned        (code 4: soft pointer) -> 'num_of_entries'
                        handle_model_space  (code 3: hard owner)
                        handle_paper_space  (code 3: hard owner)
                    -------------------------
                    CRC
                    -------------------------
        """
        obj = dict()
        obj.update(self.common_object_header())
        if obj['handle'] is None:
            return obj

        obj['num_of_entries'] = self.bc.read_bl()

        if DWGVersion.R21 <= self.dwg_version:
            self.bc.set_bit_pos(obj['obj_size'])  # Skip the string stream

        obj['handle_null'] = self.decode_handle_reference(obj.get('handle'),
                                                          DWGHandleCode.SOFT_POINTER)
        if obj.get('xdic_missing_flag') == 0:
            obj['handle_xdic_obj'] = self.decode_handle_reference(obj.get('handle'),
                                                                  DWGHandleCode.HARD_OWNERSHIP)
        obj['handle_owned'] = []
        for idx in range(obj.get('num_of_entries')):
            h = self.decode_handle_reference(obj.get('handle'), DWGHandleCode.SOFT_OWNERSHIP)
            obj['handle_owned'].append(h)

        obj['handle_model_space'] = self.decode_handle_reference(obj.get('handle'),
                                                                 DWGHandleCode.HARD_OWNERSHIP)
        obj['handle_paper_space'] = self.decode_handle_reference(obj.get('handle'),
                                                                 DWGHandleCode.HARD_OWNERSHIP)
        obj['crc'] = self.bc.read_crc()
        return obj

    def BLOCK_HEADER(self):
        """Parse BLOCK_HEADER (0x31, 49) object

        @return     Parsing results (Dict.)
                    -------------------------
                    COMMON_OBJECT_HEADER
                    -------------------------
                    ALL
                        entry_name (TV)
                        flag_64 (B)
                        xref_index_plus1 (BS)
                        xdep (B): This block is dependent on an xref
                        anonymous (B): if this block is an anonymous block
                        has_atts (B): if this block contains attdefs
                        blk_is_xref (B): if this block is xref
                        xref_overlaid (B): if an overlaid xref
                        loaded_bit (B): 0 indicates loaded for an xref
                        owned_obj_count (BL)
                        base_pt (3BD)
                        xref_pathname (TV)
                        insert_count (RC * N): how many insert handles will be presented
                            - A sequence of zero or more non-zero RC -> terminated by 0 RC
                            - insert_count = Length of the sequence
                        block_description (TV)
                        preview_data_size (BL)
                        preview_data (RC * preview_data_size)
                    R21+
                        insert_units (BS)
                        explodable (B)
                        block_scaling (RC)
                    ALL
                        handle_block_control(code 4: soft pointer)
                        handle_reactors     (code 4: soft pointer) -> 'num_of_reactors'
                        handle_xdic_obj     (code 3: hard owner)   only if 'xdic_missing_flag' is 1
                        handle_null         (code 5: hard pointer)
                        handle_block_entity (code 3: hard owner)
                        handle_owned        (code 3: hard owner) -> 'owned_obj_count'
                        handle_endblk_entity(code 3: hard owner)
                        handle_inserts      (code 4: soft pointer) -> 'insert_count'
                        handle_layout       (code 5: hard pointer)
                    -------------------------
                    CRC
                    -------------------------
        """
        obj = dict()
        obj.update(self.common_object_header())
        if obj['handle'] is None:
            return obj

        obj['entry_name'] = self.bc.read_tv() if self.dwg_version < DWGVersion.R21 else ""
        obj['flag_64'] = self.bc.read_b()
        obj['xref_index_plus1'] = self.bc.read_bs()
        obj['xdep'] = self.bc.read_b()
        obj['anonymous'] = self.bc.read_b()
        obj['has_atts'] = self.bc.read_b()
        obj['blk_is_xref'] = self.bc.read_b()
        obj['xref_overlaid'] = self.bc.read_b()
        obj['loaded_bit'] = self.bc.read_b()
        obj['owned_obj_count'] = self.bc.read_bl()
        obj['base_pt'] = self.bc.read_3bd()
        obj['xref_pathname'] = self.bc.read_tv() if self.dwg_version < DWGVersion.R21 else ""
        obj['insert_count'] = 0
        while self.bc.read_rc() != 0x00:
            obj['insert_count'] += 1
        obj['block_description'] = self.bc.read_tv() if self.dwg_version < DWGVersion.R21 else ""
        obj['preview_data_size'] = self.bc.read_bl()
        obj['preview_data'] = []
        for idx in range(obj['preview_data_size']):
            obj['preview_data'].append(self.bc.read_rc())
            # char = self.bc.read_rc()

        if DWGVersion.R21 <= self.dwg_version:
            obj['insert_units'] = self.bc.read_bs()
            obj['explodable'] = self.bc.read_b()
            obj['block_scaling'] = self.bc.read_rc()

        if DWGVersion.R21 <= self.dwg_version:
            # Set UNICODE strings
            # obj['entry_name'] = self.bc.read_tu()
            # obj['xref_pathname'] = self.bc.read_tu()
            # obj['block_description'] = self.bc.read_tu()
            self.bc.set_bit_pos(obj['obj_size'])  # Skip the string stream
            return obj

        h = self.decode_handle_reference(obj.get('handle'), DWGHandleCode.SOFT_POINTER)
        obj['handle_block_control'] = h

        obj['handle_reactors'] = []
        for idx in range(obj.get('num_of_reactors')):
            h = self.decode_handle_reference(obj.get('handle'), DWGHandleCode.SOFT_POINTER)
            obj['handle_reactors'].append(h)

        if obj.get('xdic_missing_flag') == 0:
            h = self.decode_handle_reference(obj.get('handle'), DWGHandleCode.HARD_OWNERSHIP)
            obj['handle_xdic_obj'] = h

        h = self.decode_handle_reference(obj.get('handle'), DWGHandleCode.HARD_POINTER)
        obj['handle_null'] = h

        h = self.decode_handle_reference(obj.get('handle'), DWGHandleCode.HARD_OWNERSHIP)
        obj['handle_block_entity'] = h

        obj['handle_owned'] = []
        for idx in range(obj.get('owned_obj_count')):
            h = self.decode_handle_reference(obj.get('handle'), DWGHandleCode.HARD_OWNERSHIP)
            obj['handle_owned'].append(h)

        h = self.decode_handle_reference(obj.get('handle'), DWGHandleCode.HARD_OWNERSHIP)
        obj['handle_endblk_entity'] = h

        obj['handle_inserts'] = []
        for idx in range(obj.get('insert_count')):
            h = self.decode_handle_reference(obj.get('handle'), DWGHandleCode.SOFT_POINTER)
            obj['handle_inserts'].append(h)

        h = self.decode_handle_reference(obj.get('handle'), DWGHandleCode.HARD_POINTER)
        obj['handle_layout'] = h

        obj['crc'] = self.bc.read_crc()
        return obj

    def LAYER_CONTROL(self):
        """Parse LAYER_CONTROL (0x32, 50) object

        @return     Parsing results (Dict.)
                    -------------------------
                    COMMON_OBJECT_HEADER
                    -------------------------
                    ALL
                        num_of_entries (BL)
                        handle_null         (code 4: soft pointer)
                        handle_xdic_obj     (code 3: hard owner)   only if 'xdic_missing_flag' is 1
                        handle_owned        (code 4: soft pointer) -> 'num_of_entries'
                    -------------------------
                    CRC
                    -------------------------
        """
        obj = dict()
        obj.update(self.common_object_header())
        if obj['handle'] is None:
            return obj

        obj['num_of_entries'] = self.bc.read_bl()

        if DWGVersion.R21 <= self.dwg_version:
            self.bc.set_bit_pos(obj['obj_size'])  # Skip the string stream

        obj['handle_null'] = self.decode_handle_reference(obj.get('handle'),
                                                          DWGHandleCode.SOFT_POINTER)
        if obj.get('xdic_missing_flag') == 0:
            obj['handle_xdic_obj'] = self.decode_handle_reference(obj.get('handle'),
                                                                  DWGHandleCode.HARD_OWNERSHIP)
        obj['handle_owned'] = []
        for idx in range(obj.get('num_of_entries')):
            h = self.decode_handle_reference(obj.get('handle'), DWGHandleCode.SOFT_OWNERSHIP)
            obj['handle_owned'].append(h)

        obj['crc'] = self.bc.read_crc()
        return obj


    def APPID_CONTROL(self):
        """Parse APPID_CONTROL (0x42, 66) object

        @return     Parsing results (Dict.)
                    -------------------------
                    COMMON_OBJECT_HEADER
                    -------------------------
                    ALL
                        num_of_entries (BL)
                        handle_null         (code 4: soft pointer)
                        handle_xdic_obj     (code 3: hard owner)   only if 'xdic_missing_flag' is 1
                        handle_owned        (code 4: soft pointer) -> 'num_of_entries'
                    -------------------------
                    CRC
                    -------------------------
        """
        obj = dict()
        obj.update(self.common_object_header())
        if obj['handle'] is None:
            return obj

        obj['num_of_entries'] = self.bc.read_bl()

        if DWGVersion.R21 <= self.dwg_version:
            self.bc.set_bit_pos(obj['obj_size'])  # Skip the string stream

        obj['handle_null'] = self.decode_handle_reference(obj.get('handle'),
                                                          DWGHandleCode.SOFT_POINTER)
        if obj.get('xdic_missing_flag') == 0:
            obj['handle_xdic_obj'] = self.decode_handle_reference(obj.get('handle'),
                                                                  DWGHandleCode.HARD_OWNERSHIP)
        obj['handle_owned'] = []
        for idx in range(obj.get('num_of_entries')):
            h = self.decode_handle_reference(obj.get('handle'), DWGHandleCode.SOFT_OWNERSHIP)
            obj['handle_owned'].append(h)

        obj['crc'] = self.bc.read_crc()
        return obj

    def APPID(self):
        """Parse APPID (0x43, 67) object

        @return     Parsing results (Dict.)
                    -------------------------
                    COMMON_OBJECT_HEADER
                    -------------------------
                    ALL
                        entry_name (TV)
                        flag_64 (B)
                        xref_index_plus1 (BS)
                        xdep (B): This block is dependent on an xref
                        unknown (RC)
                    ALL
                        handle_app_control  (code 4: soft pointer)
                        handle_reactors     (code 4: soft pointer) -> 'num_of_reactors'
                        handle_xdic_obj     (code 3: hard owner)   only if 'xdic_missing_flag' is 1
                        handle_ext_ref_block(code 5: hard pointer)
                    -------------------------
                    CRC
                    -------------------------
        """
        obj = dict()
        obj.update(self.common_object_header())
        if obj['handle'] is None:
            return obj

        # self.bc.set_pos(self.bc.pos_byte, self.bc.pos_bit-1)

        obj['entry_name'] = self.bc.read_tv() if self.dwg_version < DWGVersion.R21 else ""
        obj['flag_64'] = self.bc.read_b()
        obj['xref_index_plus1'] = self.bc.read_bs()
        obj['xdep'] = self.bc.read_b()
        if self.dwg_version < DWGVersion.R21:
            obj['unknown'] = self.bc.read_rc()

        if DWGVersion.R21 <= self.dwg_version:
            # self.bc.set_pos(9, 1)  # 73th bits
            # Set UNICODE strings
            # obj['entry_name'] = self.bc.read_tu()
            self.bc.set_bit_pos(obj['obj_size'])  # Skip the string stream

        h = self.decode_handle_reference(obj.get('handle'), DWGHandleCode.SOFT_POINTER)
        obj['handle_app_control'] = h

        obj['handle_reactors'] = []
        for idx in range(obj.get('num_of_reactors')):
            h = self.decode_handle_reference(obj.get('handle'), DWGHandleCode.SOFT_POINTER)
            obj['handle_reactors'].append(h)

        if obj.get('xdic_missing_flag') == 0:
            h = self.decode_handle_reference(obj.get('handle'), DWGHandleCode.HARD_OWNERSHIP)
            obj['handle_xdic_obj'] = h

        h = self.decode_handle_reference(obj.get('handle'), DWGHandleCode.HARD_POINTER)
        obj['handle_ext_ref_block'] = h

        obj['crc'] = self.bc.read_crc()
        return obj

    def GROUP(self):
        """Parse GROUP (0x48, 72) object

        @return     Parsing results (Dict.)
                    -------------------------
                    COMMON_OBJECT_HEADER
                    -------------------------
                    ALL
                        entry_name (TV): name of group
                        unnamed (BS)
                        selectable (BS)
                        num_of_entries (BL)
                        handle_parent       (code 4: soft pointer)
                        handle_reactors     (code 4: soft pointer) -> 'num_of_reactors'
                        handle_xdic_obj     (code 3: hard owner)   only if 'xdic_missing_flag' is 1
                        handle_owned        (code 5: hard pointer) -> 'num_of_entries'
                    -------------------------
                    CRC
                    -------------------------
        """
        obj = dict()
        obj.update(self.common_object_header())
        if obj['handle'] is None:
            return obj

        obj['entry_name'] = self.bc.read_tv() if self.dwg_version < DWGVersion.R21 else ""
        obj['unnamed'] = self.bc.read_bs()
        obj['selectable'] = self.bc.read_bs()
        obj['num_of_entries'] = self.bc.read_bl()

        if DWGVersion.R21 <= self.dwg_version:
            self.bc.set_bit_pos(obj['obj_size'])  # Skip the string stream

        h = self.decode_handle_reference(obj.get('handle'), DWGHandleCode.SOFT_POINTER)
        obj['handle_parent'] = h

        obj['handle_reactors'] = []
        for idx in range(obj.get('num_of_reactors')):
            h = self.decode_handle_reference(obj.get('handle'), DWGHandleCode.SOFT_POINTER)
            obj['handle_reactors'].append(h)

        if obj.get('xdic_missing_flag') == 0:
            h = self.decode_handle_reference(obj.get('handle'), DWGHandleCode.HARD_OWNERSHIP)
            obj['handle_xdic_obj'] = h

        obj['handle_owned'] = []
        for idx in range(obj.get('num_of_entries')):
            h = self.decode_handle_reference(obj.get('handle'), DWGHandleCode.HARD_POINTER)
            obj['handle_owned'].append(h)

        obj['crc'] = self.bc.read_crc()
        return obj
    '''
    -------------------------------------------------------------
    COMMON DECODERS
    -------------------------------------------------------------
    '''

    def default(self):
        """Parse the default structure for entities and objects

        @return     Parsing results (Dict.)
                    -------------------------
                    COMMON_ENTITY_HEADER
                    -------------------------
                    ALL
                        block_name (tv)
                    -------------------------
                    COMMON_ENTITY_HANDLE_DATA
                    CRC
                    -------------------------
        """
        obj = dict()

        if self.obj_class == DWGObjectTypeClass.ENTITY.value:
            obj.update(self.common_entity_header())
        elif self.obj_class == DWGObjectTypeClass.OBJECT.value:
            if 500 <= self.obj_type or \
               (self.obj_name.find("_CONTROL") < 0):
                obj.update(self.default_header())
                return obj
            obj.update(self.common_object_header())
            obj['num_of_entries'] = self.bc.read_bl()

        # Skip to handle data
        self.bc.set_bit_pos(obj['obj_size'])

        if self.obj_class == DWGObjectTypeClass.ENTITY.value:
            obj.update(self.common_entity_handle_data(obj))
        else:
            obj['handle_null'] = self.decode_handle_reference(obj.get('handle'),
                                                              DWGHandleCode.SOFT_POINTER)
            if obj.get('xdic_missing_flag') == 0:
                obj['handle_xdic_obj'] = self.decode_handle_reference(obj.get('handle'),
                                                                      DWGHandleCode.HARD_OWNERSHIP)
            obj['handle_owned'] = []
            for idx in range(obj.get('num_of_entries')):
                h = self.decode_handle_reference(obj.get('handle'), DWGHandleCode.SOFT_OWNERSHIP)
                obj['handle_owned'].append(h)

        return obj

    def default_header(self):
        """Parse the default structure

        @return     Parsing results (Dict.)

                    ALL
                        obj_size (RL)
                        handle (H)
                            {
                                code
                                counter
                                value
                            }
        """
        common = dict()
        common['obj_size'] = self.bc.read_rl()
        common['handle'] = self.bc.read_h()
        return common

    def common_object_header(self):
        """Parse the common object header data

        @return     Parsing results (Dict.)

                    ALL
                        obj_size (RL)
                        handle (H)
                            {
                                code
                                counter
                                value
                            }
                        ext_size (BS)
                        ext_data (RC * ext_size)
                        num_of_reactors (BL)
                        xdic_missing_flag (B)
                    R27+
                        has_ds_binary_data (B)
        """
        common = dict()
        common['obj_size'] = self.bc.read_rl()

        common['handle'] = self.bc.read_h()
        if common['handle'] is None:
            return common

        common['ext_size'] = self.bc.read_bs()
        common['ext_data'] = []
        if common['ext_size'] > 0:
            '''
            EED (Extended Entity Data) or EOD (Extended Object Data)
            Repeat [ length | application handle | data items ] until length == 0
            eed_size = sum(all lengths)
            eed_data = all data items
            '''
            size = common['ext_size']
            common['ext_size'] = 0
            while size > 0:
                common['ext_size'] += size
                handle = self.bc.read_h()
                if handle is None:
                    return common
                for idx in range(size):
                    # common['graphic_data'].append(self.bc.read_rc())  # if necessary, uncomment
                    char = self.bc.read_rc()
                size = self.bc.read_bs()

        common['num_of_reactors'] = self.bc.read_bl()
        common['xdic_missing_flag'] = self.bc.read_b()

        if DWGVersion.R27 <= self.dwg_version:
            common['has_ds_binary_data'] = self.bc.read_b()

        if DWGVersion.R21 <= self.dwg_version:
            pos_byte_bak, pos_bit_bak = self.bc.get_pos()
            self.bc.set_bit_pos(common['obj_size']-1)
            common['string_stream_flag'] = self.bc.read_b()
            if common['string_stream_flag'] == 1:
                # common['string_stream'] = self.get_string_stream(common['obj_size'])
                a = '?'
            self.bc.set_pos(pos_byte_bak, pos_bit_bak)

        return common

    def get_string_stream(self, end_bit):
        """Get the string stream (only if 'string_stream_flag' is 1) - R21+

            - TODO
            - Getting string stream data (UNICODE strings)
                - Open Design Specification for .dwg files v5.3 (page 99)
                - Below code is not fully implemented.

            < Internal structure of an object >
                -----------------------
                Common object header
                -----------------------
                object data (X)
                -----------------------
                string stream (X)* (for storing UNICODE data)
                string stream present flag (B)
                ----------------------- <------- here is the 'end_bit'
                Handle stream
                -----------------------
                CRC
                -----------------------

        Args:
            end_bit (int)

        Returns:
            string_stream (bytes)
        """
        new_end_bit = end_bit - 16*8
        self.bc.set_bit_pos(new_end_bit)  # Set the new position

        str_data_size = self.bc.read_rs()
        if str_data_size & 0x8000 == 0x8000:
            str_data_size &= ~0x8000
            new_end_bit -= 16*8
            self.bc.set_bit_pos(new_end_bit)  # Set the new position
            hi_size = self.bc.read_rs()
            str_data_size = (str_data_size | (hi_size << 15))

        new_end_bit -= str_data_size
        self.bc.set_bit_pos(new_end_bit)  # Set the new position

        stream = self.bc.read_rcs(int(str_data_size / 8))
        self.utils.print_hex_bytes(stream)
        return stream

    def common_entity_header(self):
        """Parse the common entity header data

        @return     Parsing results (Dict.)

                    ALL
                        obj_size (RL)
                        handle (H)
                            {
                                code
                                counter
                                value
                            }
                        ext_size (BS)
                        ext_data (RC * ext_size)
                        graphic_image_flag (B)
                            if graphic_present_flag == 1
                                graphic_size (RL)
                                graphic_image_data
                        entity_mode (BB)
                        num_of_reactors (BL)
                        xdic_missing_flag (B)
                    R27+
                        has_ds_binary_data (B)
                    ALL
                        no_links (B)
                        -- UNKNOWN (B)
                        ltype_scale (BD)
                        ltype_flags (BB)
                        plotstyle_flags (BB)
                    R21+
                        material_flags (BB)
                        shadow_flags (RC)
                    ALL
                        invisibility (BS)
                        line_weight (RC)
        """
        common = dict()
        common['obj_size'] = self.bc.read_rl()

        common['handle'] = self.bc.read_h()
        if common['handle'] is None:
            return common

        common['ext_size'] = self.bc.read_bs()
        common['ext_data'] = []
        if common['ext_size'] > 0:
            '''
            EED (Extended Entity Data) or EOD (Extended Object Data)
            Repeat [ length | application handle | data items ] until length == 0
            eed_size = sum(all lengths)
            eed_data = all data items
            '''
            size = common['ext_size']
            common['ext_size'] = 0
            while size > 0:
                common['ext_size'] += size
                handle = self.bc.read_h()
                if handle is None:
                    return common
                for idx in range(size):
                    # common['ext_data'].append(self.bc.read_rc())  # if necessary, uncomment
                    char = self.bc.read_rc()
                size = self.bc.read_bs()

        common['graphic_present_flag'] = self.bc.read_b()
        if common['graphic_present_flag'] == 1:
            common['graphic_size'] = self.bc.read_rl()
            common['graphic_data'] = []
            for idx in range(common['graphic_size']):
                # common['graphic_data'].append(self.bc.read_rc())  # if necessary, uncomment
                char = self.bc.read_rc()

        common['entity_mode'] = self.bc.read_bb()
        common['num_of_reactors'] = self.bc.read_bl()
        common['xdic_missing_flag'] = self.bc.read_b()

        if DWGVersion.R27 <= self.dwg_version:
            common['has_ds_binary_data'] = self.bc.read_b()

        common['no_links'] = self.bc.read_b()
        # The specification document may be wrong....
        # So, we referred to libredwg sources (dwg_decode_entity() in decode.cpp)
        if common['no_links'] == 0:
            color_mode = self.bc.read_b()
            # print("[ALERT] Color structure??")
            if color_mode == 1:
                index = self.bc.read_rc()
            else:
                flags = self.bc.read_rs()
                if flags & 0x8000 > 0:
                    rgb = self.bc.read_bl()
                    name = self.bc.read_tv()
                if flags & 0x4000 > 0:
                    flags = flags # has AcDbColor reference
                if flags & 0x2000 > 0:
                    transparency_type = self.bc.read_bl()
        else:
            # For DWGVersion.R18+, always here? no!!!
            color_unknown = self.bc.read_b() # what is this 1 bit?

        common['ltype_scale'] = self.bc.read_bd()
        common['ltype_flags'] = self.bc.read_bb()
        common['plotstyle_flags'] = self.bc.read_bb()

        if DWGVersion.R21 <= self.dwg_version:
            common['material_flags'] = self.bc.read_bb()
            common['shadow_flags'] = self.bc.read_rc()

        common['invisibility'] = self.bc.read_bs()
        common['line_weight'] = self.bc.read_rc()
        return common

    def common_entity_handle_data(self, base):
        """Parse the common entity handle data

        @return     Parsing results (Dict.)

                    ALL
                        handle_owner_ref    (code 4: soft pointer) only if 'entity_mode'
                        handle_reactors     (code 4: soft pointer) -> 'num_of_reactors'
                        handle_xdic_obj     (code 3: hard owner)   only if 'xdic_missing_flag' is 1
                        handle_color_book   (code 5: hard pointer) only if 'color_flag' is 1
                        handle_layer        (code 5: hard pointer)
                        handle_ltype        (code 5: hard pointer) only if 'ltype_flags' is 3
                        handle_plotstyle    (code 5: hard pointer) only if 'plotstyle_flags' is 3
                    R21+
                        handle_material     (any codes) only if 'material_flags' is 3
                    R24+
                        handle_full_visual_style    (code 5: hard pointer)
                        handle_face_visual_style    (code 5: hard pointer)
                        handle_edge_visual_style    (code 5: hard pointer)
        """
        common = dict()

        if base.get('entity_mode') == 0:
            common['handle_owner_ref'] = self.decode_handle_reference(base.get('handle'),
                                                                      DWGHandleCode.SOFT_POINTER)

        common['handle_reactors'] = []
        for idx in range(base.get('num_of_reactors')):
            common['handle_reactors'].append(self.decode_handle_reference(base.get('handle'),
                                                                          DWGHandleCode.SOFT_POINTER))

        if base.get('xdic_missing_flag') == 0:
            common['handle_xdic_obj'] = self.decode_handle_reference(base.get('handle'),
                                                                     DWGHandleCode.HARD_OWNERSHIP)

        # if base.get('color_flag@') == 0:
        #     common['handle_color_book'] = self.decode_handle_reference(base.get('handle'),
        #                                                                DWGHandleCode.HARD_POINTER)

        common['handle_layer'] = self.decode_handle_reference(base.get('handle'),
                                                              DWGHandleCode.HARD_POINTER)

        if base.get('ltype_flags') == 3:
            common['handle_ltype'] = self.decode_handle_reference(base.get('handle'),
                                                                  DWGHandleCode.HARD_POINTER)

        if base.get('plotstyle_flags') == 3:
            common['handle_plotstyle'] = self.decode_handle_reference(base.get('handle'),
                                                                      DWGHandleCode.HARD_POINTER)

        if DWGVersion.R21 <= self.dwg_version:
            if base.get('material_flags') == 3:
                common['handle_material'] = self.decode_handle_reference(base.get('handle'),
                                                                         DWGHandleCode.ANY)

        return common

    def decode_handle_reference(self, base, code):
        """Decode the handle reference

        @return     Parsing results (Dict.)

                    code
                    counter
                    value
                    absolute_reference
        """
        h = self.bc.read_h()
        if h is None:
            return None

        if h.get('code') == 0x06:
            h['absolute_reference'] = base.get('value') + 1
        elif h.get('code') == 0x08:
            h['absolute_reference'] = base.get('value') - 1
        elif h.get('code') == 0x0A:
            h['absolute_reference'] = base.get('value') + h.get('value')
        elif h.get('code') == 0x0C:
            h['absolute_reference'] = base.get('value') - h.get('value')
        elif h.get('code') == 0x02 or h.get('code') == 0x03 or \
             h.get('code') == 0x04 or h.get('code') == 0x05:
             h['absolute_reference'] = h.get('value')
        else:
            msg = "[{}] Invalid handle code {} is detected from {} ({}).".format(
                DWGSectionName.ACDBOBJECTS.value,
                h.get('code'),
                self.obj_name, self.obj_class
            )
            self.logger.debug("{}(): {}".format(GET_MY_NAME(), msg))
            self.report.add(DWGVInfo(DWGVType.CORRUPTED, -1, -1, msg))

        return h
