# File:		LCD.py
# Author:	Douglas McIlrath
# Date:		July 2014
# Description:	Library for the Beaglebone black to communicate with the ili9340 driver chip

# adafruit hw pin libraries
import Adafruit_BBIO.SPI as spi
import Adafruit_BBIO.GPIO as io

import time
import os

class LCD:
	# constructor defaults are 15 for reset and 16 for d/c
	def __init__(self, rst='P9_15', dc='P9_16'):
		# d/c and reset pins are not part of spi interface, must be set manually
		self.dc = dc
		self.rst = rst
		io.setup(dc,  io.OUT)
		io.setup(rst, io.OUT)
		# use hw spi interface (spidev1.0)
		self.conn = spi.SPI(0,0)
		# screen dimensions
		self.width = 240
		self.height = 320
		# define some colors
		self.RED 	= self.color16Bit(0xff0000)
		self.GREEN 	= self.color16Bit(0x00ff00)
		self.BLUE 	= self.color16Bit(0x0000ff)
		self.YELLOW	= self.color16Bit(0xffff00)
		self.CYAN	= self.color16Bit(0x00ffff)
		self.PURPLE	= self.color16Bit(0x0000ff)
		self.WHITE	= self.color16Bit(0xffffff)
		self.BLACK	= self.color16Bit(0x000000)
		# initialize font array
		self.fonts = []
	# send hex command to display
	def writeCommand(self, command):
		# set dcx to command mode (low)
		io.output(self.dc, 0)
		# write to spi
		self.conn.writebytes([command])
	# send hex data to display (parameters for commands, pixel values)
	def writeData(self, args):
		# set dcx to data mode (high)
		io.output(self.dc, 1)
		# write to spi
		while len(args) > 1024:
			self.conn.writebytes(args[:1024])
			args = args[1024:]
		self.conn.writebytes(args)
	# load a font
	def loadFont(self, fontfile, width, height, charw, charh):
		newfont = []
		f = open(fontfile, 'rb')
		# skip boring header
		tmp = f.read(54)
		# load bitmap
		for y in range(0, height):
			row = []
			for x in range(0, width):
				# font definition files should be black/white with black for character pixels
				byte  = ord(f.read(1))
				byte |= ord(f.read(1))
				byte |= ord(f.read(1))
				row.append(byte == 0)
			newfont.append(row)
		f.close()
		self.fonts.append([charw, charh, width, height, newfont])
	# begin connection, set up display
	def begin(self):
		# toggle reset line
		io.output(self.rst, 1)
		time.sleep(.005)
		io.output(self.rst, 0)
		time.sleep(.020)
		io.output(self.rst, 1)
		time.sleep(.150)
		# begin start sequence
		self.writeCommand(0xEF)
		self.writeData([0x03, 0x80, 0x02])
		self.writeCommand(0xCF)				# Power Control B
		self.writeData([0x00, 0xC1, 0x30])
		self.writeCommand(0xED)				# Power On Sequence Control
		self.writeData([0x85, 0x00, 0x78])
		self.writeCommand(0xCB)				# Power Control A
		self.writeData([0x39, 0x2C, 0x00, 0x34, 0x02])
		self.writeCommand(0xF7)				# Pump Ratio Control
		self.writeData([0x20])
		self.writeCommand(0xEA)				# Driver Timing Control
		self.writeData([0x00, 0x00])
		self.writeCommand(0xC0)				# Power Control 1
		self.writeData([0x23])
		self.writeCommand(0xC1)				# Power Control 2
		self.writeData([0x10])
		self.writeCommand(0xC5)				# VCOM Control 1
		self.writeData([0x3E, 0x28])
		self.writeCommand(0xC7)				# VCOM Control 2
		self.writeData([0x86])
		self.writeCommand(0x36)				# Memory Acess Control
		self.writeData([0x48])
		self.writeCommand(0x3A)				# Pixel Format Set
		self.writeData([0x55])
		self.writeCommand(0xB1)				# Frame Rate Control
		self.writeData([0x00, 0x18])
		self.writeCommand(0xB6)				# Display Function Control
		self.writeData([0x08, 0x82, 0x27])
		self.writeCommand(0xF2)				# Enable 3 Gamma Control
		self.writeData([0x00])
		self.writeCommand(0x26)				# Gamma Set
		self.writeData([0x01])
		self.writeCommand(0xE0)				# Set Positive Gamma Correction
		self.writeData([0x0F, 0x31, 0x2B, 0x0C, 0x0E])
		self.writeData([0x08, 0x4E, 0xF1, 0x37, 0x07])
		self.writeData([0x10, 0x03, 0x0E, 0x09, 0x00])
		self.writeCommand(0xE1)				# Set Negative Gamma Correction
		self.writeData([0x00, 0x0E, 0x14, 0x03, 0x11])
		self.writeData([0x07, 0x31, 0xC1, 0x48, 0x08])
		self.writeData([0x0F, 0x0C, 0x31, 0x36, 0x0F])
		# exit sleep mode
		self.writeCommand(0x11)
		time.sleep(.120)
		# turn on display
		self.writeCommand(0x29)
	# define self.write space
	def setAddressWindow(self, x1, y1, x2, y2):
		# Column Address Set
		self.writeCommand(0x2A)
		self.writeData([x1 >> 8, x1 & 0xFF])	# X begin
		self.writeData([x2 >> 8, x2 & 0xFF]) 	# X end
		# Row Address Set
		self.writeCommand(0x2B)
		self.writeData([y1 >> 8, y1 & 0xFF]) 	# Y begin
		self.writeData([y2 >> 8, y2 & 0xFF]) 	# Y end
	# convert 24-bit hex color to 16-bit packed color
	def color16Bit(self, color):
		r = color >> 16
		g = (color >> 8) & 0xFF
		b = color & 0xFF
		return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
	# draw a filled rectangle with a color (use 16-bit format, coords are tl and br)
	def fillRect(self, x1, y1, x2, y2, color):
		# clipping
		if x1 >= self.width or x2 <= 0 or y1 >= self.height or y2 <= 0 or x1 > x2 or y1 > y2:
			return False
		if x1 < 0:
			x1 = 0
		if y1 < 0:
			y1 = 0
		if x2 >= self.width:
			x2 = self.width - 1
		if y2 >= self.height:
			y2 = self.height - 1
		# set write space
		self.setAddressWindow(x1, y1, x2, y2)
		# separate color bytes
		msB = color >> 8
		lsB = color & 0xFF
		# write
		self.writeCommand(0x2C) # ramwr command
		io.output(self.dc, 1)	# sending data
		for h in range(0, (y2-y1)+1):
			for w in range(0, (x2-x1)+1):
				self.conn.writebytes([msB, lsB])
		self.writeCommand(0x00) # empty command (end xfer)
	# fill the screen with a color (use 16-bit format)
	def fillScreen(self, color):
		self.fillRect(0, 0, self.width, self.height, color)
	# draw a pixel
	def drawPixel(self, x, y, color):
		self.fillRect(x, y, x, y, color)
	# draw lines
	def drawFastVLine(self, x, y1, y2, color):
		self.fillRect(x, y1, x, y2, color)
	def drawFastHLine(self, y, x1, x2, color):
		self.fillRect(x1, y, x2, y, color)
	# write a single character
	def writeChar(self, char, xpos, ypos, color, fontid=0):
		# is the font loaded?
		if len(self.fonts) <= fontid:
			print 'Error: font not loaded'
			print 'You can fix this with <instance>.loadFont(filename, file width, height, character width, height)'
			return False
		# get character position
		i = ord(char) - 32
		# check for font boundary error
		if i >= 96:
			return False
		x = i & 0xF
		y = i >> 4
		# get font characteristics
		c_width = self.fonts[fontid][0]
		c_height = self.fonts[fontid][1]
		f_width = self.fonts[fontid][2]
		f_height = self.fonts[fontid][3]

		# check for screen boundary error
		if xpos < 0 or xpos+c_width > self.width or ypos < 0 or ypos+c_height > self.height:
			return False

		# get character definition
		for h in range(1, c_height+1):
			for w in range(0, c_width):
				if self.fonts[fontid][4][f_height-(y*c_height+h)][x*c_width+w]:
					self.drawPixel(xpos+w, ypos+h, color)
		return True
	# write text at a given x, y position
	def writeTextPosition(self, text, xpos, ypos, color, linewrap=False, overwrite=False, clear=0xFFFF, fontid=0):
		# note font characteristics
		char_width = self.fonts[fontid][0]
		char_height = self.fonts[fontid][1]
		# option to print a solid background behind text, useful for writing over previous text
		if overwrite:
			self.fillRect(xpos, ypos, xpos+len(text)*char_width, ypos+char_height, clear)
		# keep track of offset
		xoffset = 0
		yoffset = 0
		for char in text:
			# write character, stop if any writes fail (out of bounds, not in font, etc)
			if xpos+xoffset+char_width > self.width:
				if linewrap:
					yoffset += char_height
					xoffset = 0
				else:
					break
			if not self.writeChar(char, xpos+xoffset, ypos+yoffset, color, fontid):
				break
			# move over for next character
			xoffset += char_width
	# load a bitmap from a file
	def drawBitmap(self, filename, xpos=0, ypos=0, width=240, height=320):
		# initialize array
		data = []
		# open file
		f = open(filename, 'rb')
		# skip header
		tmp = f.read(54)
		# load
		for y in range(0, height):
			row = []
			for x in range(0, width):
				# use 'ord()' to convert from char to int
				b = ord(f.read(1))
				g = ord(f.read(1))
				r = ord(f.read(1))
				row.append(self.color16Bit((r << 16) | (g << 8) | b))
			data.append(row)
		# set write space
		self.setAddressWindow(xpos, ypos, xpos+width, ypos+height)
		# write data
		self.writeCommand(0x2C) # ramwr command
		io.output(self.dc, 1)	# sending data
		for y in range(1, height+1):
			for x in range(0, width):
				color = data[height-y][x]
				self.conn.writebytes([color >> 8, color & 0xFF])
		self.writeCommand(0x00)	# empty command (end xfer)
	# put the display to sleep
	def sleep(self):
		self.writeCommand(0x28)
	# wake the display up
	def wake(self):
		self.writeCommand(0x29)

