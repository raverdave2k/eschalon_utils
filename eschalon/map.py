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

import os
import struct
from eschalon import constants as c
from eschalon.savefile import Savefile, LoadException, FirstItemLoadException
from eschalon.tile import Tile
from eschalon.tilecontent import Tilecontent
from eschalon.entity import Entity

class Map(object):
    """ The base Map class.  """

    DIR_N = 0x01
    DIR_NE = 0x02
    DIR_E = 0x04
    DIR_SE = 0x08
    DIR_S = 0x10
    DIR_SW = 0x20
    DIR_W = 0x40
    DIR_NW = 0x80

    def __init__(self, df):
        """
        A fresh object.
        """

        # Everything else follows...
        self.df = None
        self.df_ent = None
        self.filename_ent = ''
        self.mapname = ''
        self.music1 = ''
        self.music2 = ''
        self.skybox = ''
        self.atmos_sound_day = ''

        # Not entirely sure about the alpha channel, which
        # is always zero, but it seems to make sense
        self.color_r = 255
        self.color_g = 255
        self.color_b = 255
        self.color_a = 0

        self.parallax_x = 0
        self.parallax_y = 0

        self.extradata = ''

        # Note that book 1 doesn't actually have this, but for sanity's
        # sake we're putting it in the base class
        self.tree_set = 0

        self.cursqcol = 0
        self.cursqrow = 0

        self.tiles = []
        for i in range(200):
            self.tiles.append([])
            for j in range(100):
                self.tiles[i].append(Tile.new(c.book, j, i))

        self.tilecontents = []
        self.entities = []

        self.df = df
        self.set_df_ent()

    def set_savegame(self, savegame):
        """
        Sets the savegame flags as-requested.
        """
        for row in self.tiles:
            for tile in row:
                tile.savegame = savegame
        for entity in self.entities:
            entity.savegame = savegame
        for tilecontent in self.tilecontents:
            tilecontent.savegame = savegame

    def check_map_extension(self):
        """
        Force the map to have a .map extension.  Note that our "Save As" logic
        might not warn on overwriting, now, because of this.
        """
        if self.df.filename[-4:].lower() != '.map':
            self.df.filename = '%s.map' % (self.df.filename)

    def set_df_ent(self):
        try:
            self.df_ent = Savefile(self.df.filename[:self.df.filename.rindex('.map')] + '.ent')
        except ValueError:
            self.df_ent = Savefile('')

    def replicate(self, book = None):
        
        if book == 1 or (book == None and self.book == 1):
            newmap = B1Map(Savefile(self.df.filename))
        elif book == 2 or (book == None and self.book == 2):
            newmap = B2Map(Savefile(self.df.filename))
        elif book == 3 or (book == None and self.book == 3):
            newmap = B3Map(Savefile(self.df.filename))

        # Single vals (no need to do actual replication)
        newmap.mapname = self.mapname
        newmap.music1 = self.music1
        newmap.music2 = self.music2
        newmap.skybox = self.skybox
        newmap.atmos_sound_day = self.atmos_sound_day
        newmap.color_r = self.color_r
        newmap.color_g = self.color_g
        newmap.color_b = self.color_b
        newmap.color_a = self.color_a
        newmap.extradata = self.extradata
        newmap.tree_set = self.tree_set
        newmap.parallax_x = self.parallax_x
        newmap.parallax_y = self.parallax_y

        # Copy tiles
        for i in range(200):
            for j in range(100):
                newmap.tiles[i][j] = self.tiles[i][j].replicate(book)

        # At this point, tilecontents and entities have been replicated as well;
        # loop through our list to repopulate from the new objects, so that
        # our referential comparisons still work on the new copy.
        for entity in self.entities:
            if (entity is None):
                newmap.entities.append(None)
            else:
                if (entity.y < len(newmap.tiles) and entity.x < len(newmap.tiles[entity.y])):
                    newmap.entities.append(newmap.tiles[entity.y][entity.x].entity)
                else:
                    newmap.entities.append(entity.replicate(book))
        tilecontentidxtemp = {}
        for tilecontent in self.tilecontents:
            if (tilecontent is None):
                newmap.tilecontents.append(None)
            else:
                if (tilecontent.y < len(newmap.tiles) and tilecontent.x < len(newmap.tiles[tilecontent.y])):
                    key = '%d%02d' % (tilecontent.y, tilecontent.x)
                    if (key in tilecontentidxtemp):
                        tilecontentidxtemp[key] += 1
                    else:
                        tilecontentidxtemp[key] = 0
                    newmap.tilecontents.append(newmap.tiles[tilecontent.y][tilecontent.x].tilecontents[tilecontentidxtemp[key]])
                else:
                    newmap.tilecontents.append(tilecontent.replicate(book))

        # Call out to superclass replication
        self._sub_replicate(newmap, book = None)

        # Now return our duplicated object
        return newmap

    def _sub_replicate(self, newmap, book = None):
        """
        Stub for superclasses to override, to replicate specific vars
        """
        pass

    def set_tile_savegame(self):
        """ Sets the savegame flag appropriately for all tiles """
        savegame = self.is_savegame()
        for row in self.tiles:
            for tile in row:
                tile.savegame = savegame

    def addtile(self):
        """ Add a new tile, assuming that the tiles are stored in a
            left-to-right, top-to-bottom format in the map. """
        self.tiles[self.cursqrow][self.cursqcol].read(self.df)
        self.cursqcol = self.cursqcol + 1
        if (self.cursqcol == 100):
            self.cursqcol = 0
            self.cursqrow = self.cursqrow + 1

    def addtilecontent(self):
        """ Add a tilecontent. """
        try:
            tilecontent = Tilecontent.new(c.book, self.is_savegame())
            tilecontent.read(self.df)
            # Note that once we start deleting tilecontents, you'll have to update both constructs here.
            # Something along the lines of this should do:
            #   self.map.tiles[y][x].tilecontents.remove(tilecontent)
            #   self.tilecontents.remove(tilecontent)
            # ... does that object then get put into a garbage collector or something?  Do we have to
            # set that to None at some point, manually?
            self.tilecontents.append(tilecontent)
            if (tilecontent.x >= 0 and tilecontent.x < 100 and tilecontent.y >= 0 and tilecontent.y < 200):
                self.tiles[tilecontent.y][tilecontent.x].addtilecontent(tilecontent)
            return True
        except FirstItemLoadException, e:
            return False

    def deltilecontent(self, x, y, idx):
        """ Deletes a tilecontent, both from the associated tile, and our internal list. """
        tile = self.tiles[y][x]
        tilecontent = tile.tilecontents[idx]
        if (tilecontent is not None):
            self.tilecontents.remove(tilecontent)
            self.tiles[y][x].deltilecontent(tilecontent)

    def addentity(self):
        """ Add an entity. """
        try:
            entity = Entity.new(c.book, self.is_savegame())
            entity.read(self.df_ent)
            if self.tiles[entity.y][entity.x].entity is not None:
                # TODO: Support this better, perhaps?
                print 'WARNING: Two entities on a single tile, discarding all but the original'
            else:
                self.entities.append(entity)
                if (entity.x >= 0 and entity.x < 100 and entity.y >= 0 and entity.y < 200):
                    self.tiles[entity.y][entity.x].addentity(entity)
            return True
        except FirstItemLoadException, e:
            return False

    def delentity(self, x, y):
        """ Deletes an entity, both from the associated tile, and our internal list. """
        tile = self.tiles[y][x]
        ent = tile.entity
        if (ent is not None):
            self.entities.remove(ent)
            tile.delentity()

    def rgb_color(self):
        return (self.color_r << 24) + (self.color_g << 16) + (self.color_b << 8) + (0xFF)

    def coords_relative(self, x, y, dir):
        """
        Static method to return coordinates for the tile
        relative to the given coords.  1 = N, 2 = NE, etc
        """
        if (dir == self.DIR_N):
            if (y < 2):
                return None
            else:
                return (x, y-2)
        elif (dir == self.DIR_NE):
            if ((y % 2) == 0):
                if (y > 0):
                    return (x, y-1)
                else:
                    return None
            elif (x < 99):
                return (x+1, y-1)
            else:
                return None
        elif (dir == self.DIR_E):
            if (x < 99):
                return (x+1, y)
            else:
                return None
        elif (dir == self.DIR_SE):
            if ((y % 2) == 0):
                return (x, y+1)
            elif (x < 99 and y < 199):
                return (x+1, y+1)
            else:
                return None
        elif (dir == self.DIR_S):
            if (y < 198):
                return (x, y+2)
            else:
                return None
        elif (dir == self.DIR_SW):
            if ((y % 2) == 1):
                if (y < 199):
                    return (x, y+1)
                else:
                    return None
            elif (x > 0):
                return (x-1, y+1)
            else:
                return None
        elif (dir == self.DIR_W):
            if (x > 1):
                return (x-1, y)
            else:
                return None
        elif (dir == self.DIR_NW):
            if ((y % 2) == 1):
                return (x, y-1)
            elif (y > 0 and x > 0):
                return (x-1, y-1)
            else:
                return None
        else:
            return None

    def tile_relative(self, x, y, dir):
        """ Returns a tile object relative to the given coords. """
        coords = self.coords_relative(x, y, dir)
        if (coords):
            return self.tiles[coords[1]][coords[0]]
        else:
            return None

    @staticmethod
    def is_ascii(s):
        for c in s:
            ascii = ord(c)
            if ascii < 32 or ascii > 126:
                return False
        return True
        
    @staticmethod
    def load(filename, book=None, req_book=None):
        """
        Static method to load a map file.  This will open the file once
        and read in a bit of data to determine whether this is a Book 1 map file
        or a Book 1 map file, and then call the appropriate constructor and
        return the object.
        """
        df = Savefile(filename)

        # Book 1 files start with 10 strings, Book 2 with 9, and Book 3 with
        # more.  To see what kind of file we have, read 11 strings and check
        # whether the last two are ASCII-only
        if book is None:
            try:
                df.open_r()
                strings = []
                for i in range(11):
                    strings.append(df.readstr())
                df.close()
            except (IOError, struct.error), e:
                raise LoadException(str(e))

            if not Map.is_ascii(strings[9]):
                book = 2
            elif not Map.is_ascii(strings[10]):
                book = 1
            else:
                book = 3

        # See if we're required to conform to a specific book
        if (req_book is not None and book != req_book):
            raise LoadException('This utility can only load Book %d map files; this file is from Book %d' % (req_book, book))

        # Now actually return the object
        if book == 1:
            c.switch_to_book(1)
            return B1Map(df)
        elif book == 2:
            c.switch_to_book(2)
            return B2Map(df)
        elif book == 3:
            c.switch_to_book(3)
            return B3Map(df)

class B1Map(Map):
    """
    Book 1 Map definitions
    """

    book = 1

    def __init__(self, df):

        # Book 1-specific vars
        self.mapid = ''
        self.exit_north = ''
        self.exit_east = ''
        self.exit_south = ''
        self.exit_west = ''
        self.clouds = 0
        self.savegame_1 = 0
        self.savegame_2 = 0
        self.savegame_3 = 0
        self.map_unknownh1 = 0
        self.map_b1_last_xpos = 0
        self.map_b1_last_ypos = 0
        self.map_b1_outsideflag = 0

        # Base class attributes
        super(B1Map, self).__init__(df)

    def read(self):
        """ Read in the whole map from a file descriptor. """

        try:

            # Open the file
            self.df.open_r()

            # Start processing
            self.mapid = self.df.readstr()
            self.mapname = self.df.readstr()
            self.music1 = self.df.readstr()
            self.music2 = self.df.readstr()
            self.exit_north = self.df.readstr()
            self.exit_east = self.df.readstr()
            self.exit_south = self.df.readstr()
            self.exit_west = self.df.readstr()
            self.skybox = self.df.readstr()
            self.atmos_sound_day = self.df.readstr()
            self.map_b1_last_xpos = self.df.readuchar()
            self.map_b1_last_ypos = self.df.readuchar()
            self.map_b1_outsideflag = self.df.readshort()
            self.map_unknownh1 = self.df.readshort()

            self.color_r = self.df.readuchar()
            self.color_g = self.df.readuchar()
            self.color_b = self.df.readuchar()
            self.color_a = self.df.readuchar()

            self.parallax_x = self.df.readint()
            self.parallax_y = self.df.readint()
            self.clouds = self.df.readint()
            self.savegame_1 = self.df.readint()
            self.savegame_2 = self.df.readint()
            self.savegame_3 = self.df.readint()

            # Tiles
            self.set_tile_savegame()
            for i in range(200*100):
                self.addtile()

            # Tilecontents...  Just keep going until EOF
            try:
                while (self.addtilecontent()):
                    pass
            except FirstItemLoadException, e:
                pass

            # Entities...  Just keep going until EOF (note that this is in a separate file)
            # Also note that we have to support situations where there is no entity file
            if (self.df_ent.exists()):
                self.df_ent.open_r()
                try:
                    while (self.addentity()):
                        pass
                except FirstItemLoadException, e:
                    pass
                self.df_ent.close()

            # If there's extra data at the end, we likely don't have
            # a valid char file
            self.extradata = self.df.read()
            if (len(self.extradata)>0):
                raise LoadException('Extra data at end of file')

            # Close the file
            self.df.close()

        except (IOError, struct.error), e:
            raise LoadException(str(e))

    def write(self):
        """ Writes out the map to the file descriptor. """

        # We require a '.map' extension
        self.check_map_extension()

        # Open the file
        self.df.open_w()

        # Start
        self.df.writestr(self.mapid)
        self.df.writestr(self.mapname)
        self.df.writestr(self.music1)
        self.df.writestr(self.music2)
        self.df.writestr(self.exit_north)
        self.df.writestr(self.exit_east)
        self.df.writestr(self.exit_south)
        self.df.writestr(self.exit_west)
        self.df.writestr(self.skybox)
        self.df.writestr(self.atmos_sound_day)
        self.df.writeuchar(self.map_b1_last_xpos)
        self.df.writeuchar(self.map_b1_last_ypos)
        self.df.writeshort(self.map_b1_outsideflag)
        self.df.writeshort(self.map_unknownh1)
        self.df.writeuchar(self.color_r)
        self.df.writeuchar(self.color_g)
        self.df.writeuchar(self.color_b)
        self.df.writeuchar(self.color_a)
        self.df.writeint(self.parallax_x)
        self.df.writeint(self.parallax_y)
        self.df.writeint(self.clouds)
        self.df.writeint(self.savegame_1)
        self.df.writeint(self.savegame_2)
        self.df.writeint(self.savegame_3)

        # Tiles
        for row in self.tiles:
            for tile in row:
                tile.write(self.df)

        # Tilecontents
        for tilecontent in self.tilecontents:
            tilecontent.write(self.df)

        # Any extra data we might have
        if (len(self.extradata) > 0):
            self.df.writestr(self.extradata)

        # Clean up
        self.df.close()

        # Now write out entities, which actually happens in a different file
        # We open regardless of entities, because we'd have to zero out the
        # file.
        self.set_df_ent()
        self.df_ent.open_w()
        for entity in self.entities:
            entity.write(self.df_ent)
        self.df_ent.close()

    def is_global(self):
        return (self.savegame_1 == 0 and self.savegame_2 == 0 and self.savegame_3 == 0)

    def is_savegame(self):
        return not self.is_global()
        # ... On the Greenhouse and direct-from-Basilisk versions, the savegame map files have
        # always had "666" in these values for me.  On at least one Steam version, it looks
        # like the first value is 320, so we're just going to invert is_global() instead.
        # Which is really what we should have been doing anyway, but whatever.
        # Savegames are... evil?  I guess?
        #return (self.savegame_1 == 666 and self.savegame_2 == 666 and self.savegame_3 == 666)

    def set_savegame(self, savegame):
        """
        Sets the state of our "savegame" vars.
        """
        # Note the comments in is_savegame() about the differences between the Steam version
        # and the non-Steam versions.  For now I'm just setting it to the values that I know
        # work on my PC - I'm really not sure how we'd go about figuring out if the installed
        # version is Steam or not.
        super(B1Map, self).set_savegame(savegame)
        if savegame:
            self.savegame_1 = 666
            self.savegame_2 = 666
            self.savegame_3 = 666
        else:
            self.savegame_1 = 0
            self.savegame_2 = 0
            self.savegame_3 = 0

    def _sub_replicate(self, newmap, book = 1):
        """
        Replicate b1-specific vars
        """
        if book == 1:
            newmap.mapid = self.mapid
            newmap.exit_north = self.exit_north
            newmap.exit_east = self.exit_east
            newmap.exit_south = self.exit_south
            newmap.exit_west = self.exit_west
            newmap.clouds = self.clouds
            newmap.savegame_1 = self.savegame_1
            newmap.savegame_2 = self.savegame_2
            newmap.savegame_3 = self.savegame_3
            newmap.map_unknownh1 = self.map_unknownh1
            newmap.map_b1_last_xpos = self.map_b1_last_xpos
            newmap.map_b1_last_ypos = self.map_b1_last_ypos
            newmap.map_b1_outsideflag = self.map_b1_outsideflag
        else:
            # These are always allowed on B1 maps
            newmap.map_flags = newmap.map_flags | 0x02 # Allow QT
            newmap.map_flags = newmap.map_flags | 0x04 # Allow Portal
            if self.map_b1_outsideflag:
                newmap.map_flags = newmap.map_flags | 0x08 # Day/night
                newmap.map_flags = newmap.map_flags | 0x40 # Regular weather
            if self.clouds:
                newmap.map_flags = newmap.map_flags | 0x20 # Clouds

class B2Map(Map):
    """
    Book 2 Map definitions
    """

    book = 2

    def __init__(self, df):

        # Book 2 specific vars
        self.entrancescript = ''
        self.returnscript = ''
        self.exitscript = ''
        self.random_sound1 = ''
        self.loadhook = 1
        self.unusedc1 = 1
        self.random_entity_1 = 0
        self.random_entity_2 = 0
        self.map_flags = 0
        self.start_tile = 0
        self.tree_set = 0
        self.last_turn = 0
        self.unusedstr1 = ''
        self.unusedstr2 = ''
        self.unusedstr3 = ''
        
        # Now the base attributes
        super(B2Map, self).__init__(df)

    def read(self):
        """ Read in the whole map from a file descriptor. """

        try:

            # Open the file
            self.df.open_r()

            # Start processing
            self.mapname = self.df.readstr()
            self.entrancescript = self.df.readstr()
            self.returnscript = self.df.readstr()
            self.exitscript = self.df.readstr()
            self.skybox = self.df.readstr()
            self.music1 = self.df.readstr()
            self.music2 = self.df.readstr()
            self.atmos_sound_day = self.df.readstr()
            self.random_sound1 = self.df.readstr()
            self.loadhook = self.df.readuchar()
            self.unusedc1 = self.df.readuchar()
            self.random_entity_1 = self.df.readuchar()
            self.random_entity_2 = self.df.readuchar()
            self.color_r = self.df.readuchar()
            self.color_g = self.df.readuchar()
            self.color_b = self.df.readuchar()
            self.color_a = self.df.readuchar()
            self.parallax_x = self.df.readint()
            self.parallax_y = self.df.readint()
            self.map_flags = self.df.readint()
            self.start_tile = self.df.readint()
            self.tree_set = self.df.readint()

            self.last_turn = self.df.readint()

            self.unusedstr1 = self.df.readstr()
            self.unusedstr2 = self.df.readstr()
            self.unusedstr3 = self.df.readstr()

            # Tiles
            self.set_tile_savegame()
            for i in range(200*100):
                self.addtile()

            # Tilecontents...  Just keep going until EOF
            try:
                while (self.addtilecontent()):
                    pass
            except FirstItemLoadException, e:
                pass

            # Entities...  Just keep going until EOF (note that this is in a separate file)
            # Also note that we have to support situations where there is no entity file
            if (self.df_ent.exists()):
                self.df_ent.open_r()
                try:
                    while (self.addentity()):
                        pass
                except FirstItemLoadException, e:
                    pass
                self.df_ent.close()

            # If there's extra data at the end, we likely don't have
            # a valid char file
            self.extradata = self.df.read()
            if (len(self.extradata)>0):
                raise LoadException('Extra data at end of file')

            # Close the file
            self.df.close()

        except (IOError, struct.error), e:
            raise LoadException(str(e))

    def write(self):
        """ Writes out the map to the file descriptor. """

        # We require a '.map' extension
        self.check_map_extension()
        
        # Open the file
        self.df.open_w()

        # Start
        self.df.writestr(self.mapname)
        self.df.writestr(self.entrancescript)
        self.df.writestr(self.returnscript)
        self.df.writestr(self.exitscript)
        self.df.writestr(self.skybox)
        self.df.writestr(self.music1)
        self.df.writestr(self.music2)
        self.df.writestr(self.atmos_sound_day)
        self.df.writestr(self.random_sound1)
        self.df.writeuchar(self.loadhook)
        self.df.writeuchar(self.unusedc1)
        self.df.writeuchar(self.random_entity_1)
        self.df.writeuchar(self.random_entity_2)
        self.df.writeuchar(self.color_r)
        self.df.writeuchar(self.color_g)
        self.df.writeuchar(self.color_b)
        self.df.writeuchar(self.color_a)
        self.df.writeint(self.parallax_x)
        self.df.writeint(self.parallax_y)
        self.df.writeint(self.map_flags)
        self.df.writeint(self.start_tile)
        self.df.writeint(self.tree_set)
        self.df.writeint(self.last_turn)
        self.df.writestr(self.unusedstr1)
        self.df.writestr(self.unusedstr2)
        self.df.writestr(self.unusedstr3)

        # Tiles
        for row in self.tiles:
            for tile in row:
                tile.write(self.df)

        # Tilecontents
        for tilecontent in self.tilecontents:
            tilecontent.write(self.df)

        # Any extra data we might have
        if (len(self.extradata) > 0):
            self.df.writestr(self.extradata)

        # Clean up
        self.df.close()

        # Now write out entities, which actually happens in a different file
        # We open regardless of entities, because we'd have to zero out the
        # file.
        self.set_df_ent()
        self.df_ent.open_w()
        for entity in self.entities:
            entity.write(self.df_ent)
        self.df_ent.close()

    def is_global(self):
        return (self.last_turn == 0)

    def is_savegame(self):
        return not self.is_global()

    def set_savegame(self, savegame):
        """
        Sets the state of our "savegame" vars.
        """
        super(B2Map, self).set_savegame(savegame)
        if savegame:
            self.last_turn = 1
        else:
            self.last_turn = 0

    def _sub_replicate(self, newmap, book = 2):
        """
        Replicate b2-specific vars
        """
        if book == 2:
            newmap.entrancescript = self.entrancescript
            newmap.returnscript = self.returnscript
            newmap.exitscript = self.exitscript
            newmap.random_sound1 = self.random_sound1
            newmap.loadhook = self.loadhook
            newmap.unusedc1 = self.unusedc1
            newmap.random_entity_1 = self.random_entity_1
            newmap.random_entity_2 = self.random_entity_2
            newmap.map_flags = self.map_flags
            newmap.start_tile = self.start_tile
            newmap.tree_set = self.tree_set
            newmap.last_turn = self.last_turn
            newmap.unusedstr1 = self.unusedstr1
            newmap.unusedstr2 = self.unusedstr2
            newmap.unusedstr3 = self.unusedstr3

class B3Map(B2Map):
    """
    Book 3 Map definitions
    """

    book = 3

    def __init__(self, df):

        # Book 3 specific vars
        self.version = '0.992'
        self.atmos_sound_night = ''
        self.random_sound2 = ''
        self.cloud_offset_x = 0
        self.cloud_offset_y = 0

        # Now the base attributes
        super(B3Map, self).__init__(df)

        # Override the parent class - without this B3 maps won't load
        self.loadhook = 2

    def read(self):
        """ Read in the whole map from a file descriptor. """

        try:

            # Open the file
            self.df.open_r()

            # Start processing
            self.version = self.df.readstr()
            self.mapname = self.df.readstr()
            self.entrancescript = self.df.readstr()
            self.returnscript = self.df.readstr()
            self.exitscript = self.df.readstr()
            self.skybox = self.df.readstr()
            self.music1 = self.df.readstr()
            self.music2 = self.df.readstr()
            self.atmos_sound_day = self.df.readstr()
            self.atmos_sound_night = self.df.readstr()
            self.random_sound1 = self.df.readstr()
            self.random_sound2 = self.df.readstr()
            self.loadhook = self.df.readuchar()
            self.unusedc1 = self.df.readuchar()
            self.random_entity_1 = self.df.readuchar()
            self.random_entity_2 = self.df.readuchar()
            self.color_r = self.df.readuchar()
            self.color_g = self.df.readuchar()
            self.color_b = self.df.readuchar()
            self.color_a = self.df.readuchar()
            self.parallax_x = self.df.readint()
            self.parallax_y = self.df.readint()
            self.cloud_offset_x = self.df.readint()
            self.cloud_offset_y = self.df.readint()
            self.map_flags = self.df.readint()
            self.start_tile = self.df.readint()
            self.tree_set = self.df.readint()

            self.last_turn = self.df.readint()

            self.unusedstr1 = self.df.readstr()
            self.unusedstr2 = self.df.readstr()
            self.unusedstr3 = self.df.readstr()

            # Tiles
            self.set_tile_savegame()
            for i in range(200*100):
                self.addtile()

            # Tilecontents...  Just keep going until EOF
            try:
                while (self.addtilecontent()):
                    pass
            except FirstItemLoadException, e:
                pass

            # Entities...  Just keep going until EOF (note that this is in a separate file)
            # Also note that we have to support situations where there is no entity file
            if (self.df_ent.exists()):
                self.df_ent.open_r()
                try:
                    while (self.addentity()):
                        pass
                except FirstItemLoadException, e:
                    pass
                self.df_ent.close()

            # If there's extra data at the end, we likely don't have
            # a valid char file
            self.extradata = self.df.read()
            if (len(self.extradata)>0):
                raise LoadException('Extra data at end of file')

            # Close the file
            self.df.close()

        except (IOError, struct.error), e:
            raise LoadException(str(e))

    def write(self):
        """ Writes out the map to the file descriptor. """

        # We require a '.map' extension
        self.check_map_extension()
        
        # Open the file
        self.df.open_w()

        # Start
        self.df.writestr(self.version)
        self.df.writestr(self.mapname)
        self.df.writestr(self.entrancescript)
        self.df.writestr(self.returnscript)
        self.df.writestr(self.exitscript)
        self.df.writestr(self.skybox)
        self.df.writestr(self.music1)
        self.df.writestr(self.music2)
        self.df.writestr(self.atmos_sound_day)
        self.df.writestr(self.atmos_sound_night)
        self.df.writestr(self.random_sound1)
        self.df.writestr(self.random_sound2)
        self.df.writeuchar(self.loadhook)
        self.df.writeuchar(self.unusedc1)
        self.df.writeuchar(self.random_entity_1)
        self.df.writeuchar(self.random_entity_2)
        self.df.writeuchar(self.color_r)
        self.df.writeuchar(self.color_g)
        self.df.writeuchar(self.color_b)
        self.df.writeuchar(self.color_a)
        self.df.writeint(self.parallax_x)
        self.df.writeint(self.parallax_y)
        self.df.writeint(self.cloud_offset_x)
        self.df.writeint(self.cloud_offset_y)
        self.df.writeint(self.map_flags)
        self.df.writeint(self.start_tile)
        self.df.writeint(self.tree_set)
        self.df.writeint(self.last_turn)
        self.df.writestr(self.unusedstr1)
        self.df.writestr(self.unusedstr2)
        self.df.writestr(self.unusedstr3)

        # Tiles
        for row in self.tiles:
            for tile in row:
                tile.write(self.df)

        # Tilecontents
        for tilecontent in self.tilecontents:
            tilecontent.write(self.df)

        # Any extra data we might have
        if (len(self.extradata) > 0):
            self.df.writestr(self.extradata)

        # Clean up
        self.df.close()

        # Now write out entities, which actually happens in a different file
        # We open regardless of entities, because we'd have to zero out the
        # file.
        self.set_df_ent()
        self.df_ent.open_w()
        for entity in self.entities:
            entity.write(self.df_ent)
        self.df_ent.close()

    def _sub_replicate(self, newmap, book = 3):
        """
        Replicate b3-specific vars
        """
        if book == 3:
            newmap.version = self.version
            newmap.atmos_sound_night = self.atmos_sound_night
            newmap.random_sound2 = self.random_sound2
            newmap.cloud_offset_x = self.cloud_offset_x
            newmap.cloud_offset_y = self.cloud_offset_y

        super(B3Map, self)._sub_replicate(newmap, book)
