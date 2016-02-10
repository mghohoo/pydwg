# -*- coding: utf-8 -*-

"""@package pydwg

    * Description
        DWGBitCodes - DWG bit codes and data definitions
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

import struct
import logging
from collections import OrderedDict
from .dwg_common import *


class DWGBitCodes:
    """DWGBitCodes class
    """

    def __init__(self, buf, size, pos_byte=0, pos_bit=0):
        """The constructor"""
        # memory buffer
        self.buf = buf
        self.size = size

        # status
        self.pos_byte = pos_byte
        self.pos_bit  = pos_bit

        # global logger
        self.logger = logging.getLogger(__name__)
        return

    def read_b(self):
        """Read 1 bit
        """
        byte = self.buf[self.pos_byte]
        value = (byte & (0x80 >> self.pos_bit)) >> (7 - self.pos_bit)

        self.update_status(1)
        return value & 0xFF

    def read_bb(self):
        """Read 2 bits
        """
        byte = self.buf[self.pos_byte]

        if self.pos_bit == 7:
            value = (byte & 0x01) << 1
            if self.pos_byte < self.size - 1:
                byte = self.buf[self.pos_byte + 1]
                value |= (byte & 0x80) >> 7
        else:
            value = (byte & (0xC0 >> self.pos_bit)) >> (6 - self.pos_bit)

        self.update_status(2)
        return value & 0xFF

    def read_3b(self):
        """Read triplet (1-3 bits)
        """
        value = 0
        for idx in range(3):
            bit = self.read_b()
            if bit == 0:
                break
            value = ((value << 1) | bit)

        return value & 0x07

    def read_bs(self):
        """Read bitshort (16 bits)
        """
        what_it_is = self.read_bb()

        if what_it_is == 0x00:
            value = self.read_rs()
        elif what_it_is == 0x01:
            value = self.read_rc()
        elif what_it_is == 0x02:
            value = 0
        elif what_it_is == 0x03:
            value = 256

        return value & 0xFFFF

    def read_bl(self):
        """Read bitlong (32 bits)
        """
        what_it_is = self.read_bb()

        if what_it_is == 0x00:
            value = self.read_rl()
        elif what_it_is == 0x01:
            value = self.read_rc()
        elif what_it_is == 0x02:
            value = 0
        elif what_it_is == 0x03:
            msg = "'11' is not used."
            self.logger.debug("{}(): {}".format(GET_MY_NAME(), msg))
            return 0

        return value & 0xFFFFFFFF


    def read_bll(self):
        """Read bitlonglong (64 bits)
        """
        value = 0
        length = self.read_3b()
        for idx in range(length):
            byte = self.read_rc()
            value = ((value << 8) | byte)

        return value & 0xFFFFFFFFFFFFFFFF

    def read_bd(self):
        """Read bitdouble
        """
        what_it_is = self.read_bb()

        if what_it_is == 0x00:
            value = float(self.read_rd())
        elif what_it_is == 0x01:
            value = float(1.0)
        elif what_it_is == 0x02:
            value = float(0.0)
        elif what_it_is == 0x03:
            msg = "'11' is not used."
            self.logger.debug("{}(): {}".format(GET_MY_NAME(), msg))
            return float(0.0)

        return value

    def read_3bd(self):
        """Read 3d point (3 bitdoubles)
        """
        return self.read_bd(), self.read_bd(), self.read_bd()

    def read_rc(self):
        """Read a raw char
        """
        if self.pos_byte >= self.size:
            msg = "No more data."
            self.logger.debug("{}(): {}".format(GET_MY_NAME(), msg))
            return None

        byte = self.buf[self.pos_byte]

        if self.pos_bit == 0:
            value = byte
        else:
            value = byte << self.pos_bit
            if self.pos_byte < self.size - 1:
                byte = self.buf[self.pos_byte + 1]
                value |= (byte >> (8 - self.pos_bit))

        self.update_status(8)
        return value & 0xFF

    def read_rcs(self, count):
        """Read 'count' raw chars
        """
        chars = bytearray()

        if count <= 0:
            return chars

        if self.pos_bit == 0:
            if self.size >= self.pos_byte+count:
                chars.extend(self.buf[self.pos_byte:self.pos_byte+count])
                self.pos_byte += count
            else:
                chars.extend(self.buf[self.pos_byte:self.size])
                self.pos_byte = self.size
        else:
            for idx in range(count):
                chars.append(self.read_rc())
        return bytes(chars)

    def read_rs(self, endian='little'):
        """Read a raw short
        """
        byte1 = self.read_rc()
        byte2 = self.read_rc()

        if byte1 is None or byte2 is None:
            return 0

        if endian == 'little':
            value = ((byte2 << 8) | byte1)
        else:
            value = ((byte1 << 8) | byte2)

        return value & 0xFFFF

    def read_rl(self, endian='little'):
        """Read a raw long (2 shorts) (not compressed)
        """
        short1 = self.read_rs(endian)
        short2 = self.read_rs(endian)

        if endian == 'little':
            value = ((short2 << 16) | short1)
        else:
            value = ((short2 << 16) | short1)

        return value & 0xFFFFFFFF

    def read_rd(self, endian='little'):
        """Read a raw double (8 bytes) (not compressed)
        """
        data = bytearray()
        for idx in range(8):
            data.append(self.read_rc())

        if endian == 'little':
            value = struct.unpack('<d', data)[0]
        else:
            value = struct.unpack('>d', data)[0]
        return value

    def read_2rd(self, endian='little'):
        """Read 2 raw doubles
        """
        return self.read_rd(endian), self.read_rd(endian)

    def read_3rd(self, endian='little'):
        """Read 3 raw doubles
        """
        return self.read_rd(endian), self.read_rd(endian), self.read_rd(endian)

    def read_mc(self):
        """Read a modular char
            - method for storing compressed integer values
            - maximum 4 bytes
        """
        value = 0
        negative = 0
        shift = 0
        modular_buf = bytearray([0x00, 0x00, 0x00, 0x00])

        for idx in range(3, -1, -1):
            modular_buf[idx] = self.read_rc()
            if not modular_buf[idx] & 0x80:
                if modular_buf[idx] & 0x40:
                    negative = 1
                    modular_buf[idx] &= 0xBF
                value |= (modular_buf[idx] << shift)
                value = -value if negative == 1 else value
                break
            else:
                modular_buf[idx] &= 0x7F
                value |= (modular_buf[idx] << shift)
            shift += 7

        # print("[Abnormal] read_mc")
        return value

    def read_ms(self):
        """Read a modular short
            - method for storing compressed integer values
            - maximum 2 shorts
        """
        value = 0
        shift = 0
        modular_buf = [0x00, 0x00]

        for idx in range(1, -1, -1):
            modular_buf[idx] = self.read_rs()
            if not modular_buf[idx] & 0x8000:
                value |= (modular_buf[idx] << shift)
                break
            else:
                modular_buf[idx] &= 0x7FFF
                value |= (modular_buf[idx] << shift)
            shift += 15

        return value

    def read_h(self):
        """Read a handle reference
        """
        handle = OrderedDict()

        handle['code'] = self.read_rc()
        handle['counter'] = handle['code'] & 0x0F
        handle['code'] = ((handle['code'] & 0xF0) >> 4)
        handle['value'] = 0

        if handle['counter'] > 4:
            msg = "Invalid handle counter {} is detected.".format(handle['counter'])
            self.logger.debug("{}(): {}".format(GET_MY_NAME(), msg))
            return None

        for idx in range(handle['counter']-1, -1, -1):
            value = self.read_rc()
            handle['value'] = (handle['value'] | (value << idx*8))

        return handle

    def read_tu(self):
        """Read unicode text
            Length (BS) + unicode string
        """
        text = bytearray()
        length = self.read_bs()
        for idx in range(length):
            unicode = self.read_rs()
            text += unicode.to_bytes(2, 'little')
        text = text.decode("utf-16LE", "ignore")
        return text

    def read_tv(self):
        """Read variable text (for R18-)
            TODO 1: non-ASCII character
            TODO 2: {font; }, \P
        """
        text = b""
        length = self.read_bs()
        for idx in range(length):
            char = self.read_rc()
            if char == 0x00:
                continue
            elif char >= 0x7F:
                char = 0x2A
            text += char.to_bytes(1, 'little')
        text = text.decode("utf-8", "ignore")
        return text

    def read_sn(self):
        """Read a sentinel (16 bytes)
        """
        sn = []
        for idx in range(16):
            sn.append(self.read_rc())
        return sn

    def read_be(self):
        """Read bit extrusion
        """
        what_it_is = self.read_b()
        if what_it_is == 1:
            return 0.0, 0.0, 0.1
        return self.read_bd(), self.read_bd(), self.read_bd()

    def read_dd(self, default_value):
        """Read bitdouble with default
        """
        value = 0.0
        what_it_is = self.read_bb()

        if what_it_is == 0:
            value = default_value
        elif what_it_is == 1:
            data = struct.pack('<d', default_value)
            data = bytearray(data)
            data[0] = self.read_rc()
            data[1] = self.read_rc()
            data[2] = self.read_rc()
            data[3] = self.read_rc()
            value = struct.unpack('<d', data)[0]
        elif what_it_is == 2:
            data = struct.pack('<d', default_value)
            data = bytearray(data)
            data[4] = self.read_rc()
            data[5] = self.read_rc()
            data[0] = self.read_rc()
            data[1] = self.read_rc()
            data[2] = self.read_rc()
            data[3] = self.read_rc()
            value = struct.unpack('<d', data)[0]
        elif what_it_is == 3:
            value = self.read_rd()

        return value

    def read_2dd(self, default1, default2):
        """Read 2 bitdoubles with default
        """
        return self.read_dd(default1), self.read_dd(default2)

    def read_3dd(self, default1, default2, default3):
        """Read 3 bitdoubles with default
        """
        return self.read_dd(default1), self.read_dd(default2), self.read_dd(default3)

    def read_bt(self):
        """Read bit thickness
        """
        what_it_is = self.read_b()
        value = 0.0 if what_it_is == 1 else self.read_bd()
        return value

    def read_cmc(self):
        """Read a CmColor value
        """
        color = OrderedDict()
        color['index'] = self.read_bs()
        color['rbg'] = self.read_bl()
        byte = color['byte'] = self.read_rc()
        if byte & 1:
            color['color_name'] = self.read_tv()
        if byte & 2:
            color['book_name'] = self.read_tv()
        return color

    def read_crc(self):
        """Read CRC
        """
        if self.pos_bit > 0:
            self.set_pos(self.pos_byte+1)

        value = self.read_rs(endian='little')
        return value

    def update_status(self, plus_bit):
        """Update the current 'bit' and 'byte' position info.
        """
        pos_end = self.pos_bit + plus_bit
        if self.pos_byte >= self.size - 1 and pos_end > 7:
            self.pos_bit = 7
            return
        self.pos_byte += int(pos_end / 8)
        self.pos_bit   = int(pos_end % 8)
        return

    def set_pos(self, pos_byte, pos_bit=0):
        """Set the current position info.
        """
        self.pos_byte = pos_byte
        self.pos_bit  = pos_bit
        return

    def plus_pos(self, pos_byte, pos_bit=0):
        """Plus the position info.
        """
        self.pos_byte += pos_byte
        self.pos_bit  += pos_bit
        return

    def set_bit_pos(self, pos_bit):
        """Set the current position info. using bit value
        """
        pos_byte_new, pos_bit_new = divmod(pos_bit, 8)
        self.set_pos(pos_byte_new, pos_bit_new)
        return

    def get_pos(self):
        """Get the current position info.
        """
        return self.pos_byte, self.pos_bit

