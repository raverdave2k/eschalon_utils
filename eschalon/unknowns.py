#!/usr/bin/python
# vim: set expandtab tabstop=4 shiftwidth=4:
#
# Eschalon Savefile Editor
# Copyright (C) 2008-2014 CJ Kucera, Elliot Kendall
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

from eschalon.item import Item

class B1Unknowns(object):
    """ A class to hold some unknown data, so as not to muddy up the
        main Character class. """

    def __init__(self):
        """ A fresh object with no data. """

        self.initzero = -1
        self.charstring = ''
        self.charone = -1
        self.sparseiblock = []
        self.iblock1 = []
        self.ssiblocks1 = []
        self.ssiblocks2 = []
        self.ssiblocki = []
        self.extstr1 = ''
        self.extstr2 = ''
        self.anotherzero = -1
        self.anotherint = -1
        self.shortval = -1
        self.emptystr = ''
        self.iblock2 = [] # These are weird
        self.preinvs1 = ''
        self.preinvs2 = ''
        self.preinvzero1 = -1
        self.preinvzero2 = -1
        self.extradata = ''

    def replicate(self):
        newunknown = B1Unknowns()

        # Simple Values
        newunknown.initzero = self.initzero
        newunknown.charstring = self.charstring
        newunknown.charone = self.charone
        newunknown.extstr1 = self.extstr1
        newunknown.extstr2 = self.extstr2
        newunknown.anotherzero = self.anotherzero
        newunknown.anotherint = self.anotherint
        newunknown.shortval = self.shortval
        newunknown.emptystr = self.emptystr
        newunknown.preinvs1 = self.preinvs1
        newunknown.preinvs2 = self.preinvs2
        newunknown.preinvzero1 = self.preinvzero1
        newunknown.preinvzero2 = self.preinvzero2
        newunknown.extradata = self.extradata

        # Arrays
        for val in self.sparseiblock:
            newunknown.sparseiblock.append(val)
        for val in self.iblock1:
            newunknown.iblock1.append(val)
        for val in self.ssiblocks1:
            newunknown.ssiblocks1.append(val)
        for val in self.ssiblocks2:
            newunknown.ssiblocks2.append(val)
        for val in self.ssiblocki:
            newunknown.ssiblocki.append(val)
        for val in self.iblock2:
            newunknown.iblock2.append(val)

        # ... aaand return our new object
        return newunknown

    def iblock(self, num, arr, desc='Block of integers'):
        """ Display a block of unknown integers. """
        ret = []
        ret.append("%s %d:" % (desc, num))
        for i in arr:
            ret.append("\t0x%08X - %d" % (i, i))
        return "\n".join(ret)

    def display(self):
        """ Show a textual description of all unknown fields. """

        ret = []

        ret.append("Initial Zero: %d" % self.initzero)
        ret.append("Empty Character String: %s" % self.charstring)
        ret.append("Usually 1: %d" % self.charone)
        ret.append(self.iblock(1, self.sparseiblock, 'Sparse integers (interleaved with char statuses)'))
        ret.append(self.iblock(1, self.iblock1))
        ret.append("Block of 2 Strings plus 1 Integer:")
        for i in range(len(self.ssiblocks1)):
            ret.append("\tBlock %d:" % (i+1))
            ret.append("\t\tString 1: %s" % self.ssiblocks1[i])
            ret.append("\t\tString 2: %s" % self.ssiblocks1[i])
            ret.append("\t\tInt: %d" % self.ssiblocki[i])
        ret.append("Extra string 1: %s" % self.extstr1)
        ret.append("Extra string 2: %s" % self.extstr2)
        ret.append("Another zero: %d" % self.anotherzero)
        ret.append("Another int (generally a multiple of 256): %d" % self.anotherint)
        ret.append("A short int: %d" % self.shortval)
        ret.append("A string (always blank for me): %s" % self.emptystr)
        ret.append(self.iblock(2, self.iblock2))
        ret.append("Pre-inventory blank string 1: %s" % self.preinvs1)
        ret.append("Pre-inventory blank string 2: %s" % self.preinvs2)
        ret.append("Pre-inventory zero 1: %d" % self.preinvzero1)
        ret.append("Pre-inventory zero 2: %d" % self.preinvzero2)
        if (len(self.extradata) != 0):
            ret.append("File has extra data appended at the end: %d bytes" % len(self.extradata))

        return "\n".join(ret)

class B2Unknowns(object):
    """ A class to hold some unknown data, so as not to muddy up the
        main Character class. """

    def __init__(self):
        """ A fresh object with no data. """

        self.initzero = -1
        self.version = -1 # I suspect this might be savefile version
        self.zero1 = -1
        self.zeros = []
        self.strangeblock = []
        self.unknowni1 = -1
        self.unknowni2 = -1
        self.unknowni3 = -1
        self.usually_one = -1
        self.unknowns1 = -1
        self.unknownstr1 = -1
        self.twentyninezeros = []
        self.unknownstr2 = -1
        self.unknownstr3 = -1
        self.unknowns2 = -1
        self.extradata = ''

    def replicate(self):
        newunknown = B2Unknowns()

        # Simple Values
        newunknown.initzero = self.initzero
        newunknown.version = self.version
        newunknown.zero1 = self.zero1
        newunknown.unknowni1 = self.unknowni1
        newunknown.unknowni2 = self.unknowni2
        newunknown.unknowni3 = self.unknowni3
        newunknown.usually_one = self.usually_one
        newunknown.unknowns1 = self.unknowns1
        newunknown.unknownstr1 = self.unknownstr1
        newunknown.unknownstr2 = self.unknownstr2
        newunknown.unknownstr3 = self.unknownstr3
        newunknown.unknowns2 = self.unknowns2
        newunknown.extradata = self.extradata

        # Lists
        for item in self.zeros:
            newunknown.zeros.append(item)
        for item in self.strangeblock:
            newunknown.strangeblock.append(item)
        for item in self.twentyninezeros:
            newunknown.twentyninezeros.append(item)

        # ... aaand return our new object
        return newunknown

    def num_block(self, digits, arr, desc='Block of integers'):
        """ Display a block of unknown integers. """
        formatstr = "\t0x%%0%dX - %%d" % (digits)
        ret = []
        ret.append(desc)
        for i in arr:
            ret.append(formatstr % (i, i))
        return "\n".join(ret)

    def iblock(self, arr, desc='Block of integers'):
        """ Display a block of unknown integers. """
        return self.num_block(8, arr, desc)

    def cblock(self, arr, desc='Block of chars'):
        """ Display a block of unknown char values. """
        return self.num_block(2, arr, desc)

    def display(self):
        """ Show a textual description of all unknown fields. """

        ret = []

        ret.append("Initial Zero: %d" % self.initzero)
        ret.append("Possibly savefile version: %d" % (self.version))
        ret.append("Usually Zero: %d" % (self.zero1))
        ret.append(self.iblock(self.zeros, 'Some Zeros'))
        ret.append(self.cblock(self.strangeblock, 'Somewhat Strange Block'))
        ret.append("Unknown Integer 1: %d" % (self.unknowni1))
        ret.append("Unknown Integer 2: %d" % (self.unknowni2))
        ret.append("Unknown Integer 3: %d" % (self.unknowni3))
        ret.append("Usually One: %d" % (self.usually_one))
        ret.append("Unknown Short 1: %d" % (self.unknowns1))
        ret.append("Unknown String 1: %s" % (self.unknownstr1))
        ret.append(self.cblock(self.twentyninezeros, '29 Zeros'))
        ret.append("Unknown String 2: %s" % (self.unknownstr2))
        ret.append("Unknown String 3: %s" % (self.unknownstr3))
        ret.append("Unknown Short 2: %d" % (self.unknowns2))
        ret.append("Extra Data: %s" % (self.extradata))

        return "\n".join(ret)
