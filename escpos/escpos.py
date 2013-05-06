#!/usr/bin/python
'''
@author: Manuel F Martinez <manpaz@bashlinux.com>
@organization: Bashlinux
@copyright: Copyright (c) 2012 Bashlinux
@license: GPL
'''

import Image
import ImageOps
import qrcode
import time

from constants import *
from exceptions import *

class Escpos:
    """ ESC/POS Printer object """
    device    = None


    def image(self, path_img):
        """ Open image file """
        if type(path_img) is str or type(path_img) is unicode:
            im = Image.open(path_img)
        else:
            im = path_img

        bitmap_mode = 0
        max_width = 256
        height_factor = 0.66666666 # to adjust for different x and y DPI
        resize_filter = Image.ANTIALIAS
        line_spacing = 49 # n/360 inches

        # If image has an alpha channel, place it on a white background
        if im.mode == "RGBA":
            imtmp = Image.new('RGB', im.size, (255, 255, 255))
            imtmp.paste(im, (0, 0), im)
            im = imtmp

        # Resize to fit and/or adjust the aspect ratio (DPI may be different for x and y)
        if im.size[0] > max_width:
            height = int(im.size[1]*(float(max_width)/float(im.size[0]))*height_factor)
            im = im.resize((max_width, height), resize_filter)
        else:
            height = int(im.size[1]*height_factor)
            im = im.resize((max_width, height), resize_filter)

        # Invert
        im = ImageOps.invert(im)

        # Convert to 1-bit
        im = im.convert("1")

        # Set line spacing to remove gaps
        self._raw('\x1b\x33' + chr(line_spacing))

        # Request access to the pixels
        pixels = im.load()

        # Output, 8 pixel rows at a time
        for y in range(0, im.size[1], 8):
            output = '' # the bytes that we will transmit for this group of pixel rows
            for x in range(0, im.size[0]):
                byte = 0 # representing 8 pixels in a vertical column
                for offset in range(0, 8):
                    try:
                        if pixels[x, y+offset] > 0:
                            byte += (2**(7-offset))
                    except IndexError:
                        pass
                output += chr(byte)
            n1 = len(output) % 256
            n2 = len(output) / 256
            self._raw('\x1b\x2a')
            self._raw(chr(bitmap_mode)+chr(n1)+chr(n2))
            self._raw(output)


    def qr(self,text):
        """ Print QR Code for the provided string """
        qr_code = qrcode.QRCode(version=4, box_size=4, border=1)
        qr_code.add_data(text)
        qr_code.make(fit=True)
        qr_img = qr_code.make_image()
        self.image(qr_img._img)


    def barcode(self, code, bc, width, height, pos, font):
        """ Print Barcode """
        # Align Bar Code()
        self._raw(TXT_ALIGN_CT)
        # Height
        if height >=2 or height <=6:
            self._raw(BARCODE_HEIGHT)
        else:
            raise BarcodeSizeError()
        # Width
        if width >= 1 or width <=255:
            self._raw(BARCODE_WIDTH)
        else:
            raise BarcodeSizeError()
        # Font
        if font.upper() == "B":
            self._raw(BARCODE_FONT_B)
        else: # DEFAULT FONT: A
            self._raw(BARCODE_FONT_A)
        # Position
        if pos.upper() == "OFF":
            self._raw(BARCODE_TXT_OFF)
        elif pos.upper() == "BOTH":
            self._raw(BARCODE_TXT_BTH)
        elif pos.upper() == "ABOVE":
            self._raw(BARCODE_TXT_ABV)
        else:  # DEFAULT POSITION: BELOW 
            self._raw(BARCODE_TXT_BLW)
        # Type 
        if bc.upper() == "UPC-A":
            self._raw(BARCODE_UPC_A)
        elif bc.upper() == "UPC-E":
            self._raw(BARCODE_UPC_E)
        elif bc.upper() == "EAN13":
            self._raw(BARCODE_EAN13)
        elif bc.upper() == "EAN8":
            self._raw(BARCODE_EAN8)
        elif bc.upper() == "CODE39":
            self._raw(BARCODE_CODE39)
        elif bc.upper() == "ITF":
            self._raw(BARCODE_ITF)
        elif bc.upper() == "NW7":
            self._raw(BARCODE_NW7)
        else:
            raise BarcodeTypeError()
        # Print Code
        if code:
            self._raw(code)
        else:
            raise exception.BarcodeCodeError()

        
    def text(self, txt):
        """ Print alpha-numeric text """
        if txt:
            self._raw(txt)
        else:
            raise TextError()


    def set(self, align='left', font='a', type='normal', width=1, height=1):
        """ Set text properties """
        # Align
        if align.upper() == "CENTER":
            self._raw(TXT_ALIGN_CT)
        elif align.upper() == "RIGHT":
            self._raw(TXT_ALIGN_RT)
        elif align.upper() == "LEFT":
            self._raw(TXT_ALIGN_LT)
        # Font
        if font.upper() == "B":
            self._raw(TXT_FONT_B)
        else:  # DEFAULT FONT: A
            self._raw(TXT_FONT_A)
        # Type
        if type.upper() == "B":
            self._raw(TXT_BOLD_ON)
            self._raw(TXT_UNDERL_OFF)
        elif type.upper() == "U":
            self._raw(TXT_BOLD_OFF)
            self._raw(TXT_UNDERL_ON)
        elif type.upper() == "U2":
            self._raw(TXT_BOLD_OFF)
            self._raw(TXT_UNDERL2_ON)
        elif type.upper() == "BU":
            self._raw(TXT_BOLD_ON)
            self._raw(TXT_UNDERL_ON)
        elif type.upper() == "BU2":
            self._raw(TXT_BOLD_ON)
            self._raw(TXT_UNDERL2_ON)
        elif type.upper == "NORMAL":
            self._raw(TXT_BOLD_OFF)
            self._raw(TXT_UNDERL_OFF)
        # Width
        if width == 2 and height != 2:
            self._raw(TXT_NORMAL)
            self._raw(TXT_2WIDTH)
        elif height == 2 and width != 2:
            self._raw(TXT_NORMAL)
            self._raw(TXT_2HEIGHT)
        elif height == 2 and width == 2:
            self._raw(TXT_2WIDTH)
            self._raw(TXT_2HEIGHT)
        else: # DEFAULT SIZE: NORMAL
            self._raw(TXT_NORMAL)


    def cut(self, mode=''):
        """ Cut paper """
        # Fix the size between last line and cut
        # TODO: handle this with a line feed
        self._raw("\n\n\n\n\n\n")
        if mode.upper() == "PART":
            self._raw(PAPER_PART_CUT)
        else: # DEFAULT MODE: FULL CUT
            self._raw(PAPER_FULL_CUT)


    def cashdraw(self, pin):
        """ Send pulse to kick the cash drawer """
        if pin == 2:
            self._raw(CD_KICK_2)
        elif pin == 5:
            self._raw(CD_KICK_5)
        else:
            raise CashDrawerError()


    def hw(self, hw):
        """ Hardware operations """
        if hw.upper() == "INIT":
            self._raw(HW_INIT)
        elif hw.upper() == "SELECT":
            self._raw(HW_SELECT)
        elif hw.upper() == "RESET":
            self._raw(HW_RESET)
        else: # DEFAULT: DOES NOTHING
            pass


    def control(self, ctl):
        """ Feed control sequences """
        if ctl.upper() == "LF":
            self._raw(CTL_LF)
        elif ctl.upper() == "FF":
            self._raw(CTL_FF)
        elif ctl.upper() == "CR":
            self._raw(CTL_CR)
        elif ctl.upper() == "HT":
            self._raw(CTL_HT)
        elif ctl.upper() == "VT":
            self._raw(CTL_VT)
