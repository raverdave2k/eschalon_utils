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
import csv
import sys
import time
import random
import traceback
import cStringIO
from eschalon import version, constants as c
from eschalon.gfx import Gfx
from eschalon.undo import Undo
from eschalon.item import B1Item, B2Item, B3Item
from eschalon.entity import B1Entity, B2Entity, B3Entity
from eschalon.basegui import BaseGUI, WrapLabel, ImageSelWindow

# Load our GTK modules
try:
    import gtk
    import gobject
except Exception, e:
    print 'Python GTK Modules not found: %s' % (str(e))
    print 'Hit enter to exit...'
    sys.stdin.readline()
    sys.exit(1)

# Load in Cairo
try:
    import cairo
except Exception, e:
    BaseGUI.errordialog('Error loading PyCairo', 'PyCairo could not be loaded: %s' % (str(e)))
    sys.exit(1)

# Check for minimum GTK+ version
if (gtk.check_version(2, 18, 0) is not None):
    BaseGUI.warningdialog('gtk+ Version Warning', '<b>Note:</b> The minimum required version '
            'of gtk+ is <i>probably</i> 2.18.0, though it\'s possible it will work on some '
            'older versions.  You\'re welcome to continue, but know that you may encounter '
            'weird behavior.')

from eschalon.map import Map
from eschalon.item import Item
from eschalon.tile import Tile
from eschalon.basegui import BaseGUI
from eschalon.smartdraw import SmartDraw
from eschalon.tilecontent import Tilecontent
from eschalon.savefile import LoadException
from eschalon.entity import Entity
from eschalon import app_name, version, url, authors

class NewMapDialog(gtk.Dialog):
    def __init__(self):
        super(NewMapDialog, self).__init__(
                flags = gtk.DIALOG_MODAL| gtk.DIALOG_DESTROY_WITH_PARENT,
                buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                    gtk.STOCK_OK, gtk.RESPONSE_OK))

        self.set_default_size(340, 160)

        self.title_align = gtk.Alignment(.5, 0, 0, 0)
        self.title_align.set_padding(20, 20, 15, 15)
        label = gtk.Label()
        label.set_markup('<big><b>Eschalon Book %d Map Editor v%s</b></big>' % (c.book, version))
        self.title_align.add(label)
        self.vbox.pack_start(self.title_align, False, False)

        self.open_align_1 = gtk.Alignment(0, 0, 0, 0)
        self.open_align_1.set_padding(0, 20, 15, 15)
        self.openlabel = gtk.Label()
        self.openlabel.set_markup('<b>Open an existing map file:</b>')
        self.open_align_1.add(self.openlabel)
        self.vbox.pack_start(self.open_align_1, False, False)

        rvbox = gtk.VBox()
        self.open_align_2 = gtk.Alignment(0, 0, 0, 1)
        self.open_align_2.set_padding(0, 10, 40, 15)
        self.open_align_2.add(rvbox)
        self.vbox.pack_start(self.open_align_2, False, False)

        self.open_savegame_radio = gtk.RadioButton(label="From the Savegame Directory")
        rvbox.add(self.open_savegame_radio)
        self.open_global_radio = gtk.RadioButton(label="From the Global Directory", group=self.open_savegame_radio)
        if c.book == 1:
            # There's no point in showing this radio for Book II
            rvbox.add(self.open_global_radio)

        align = gtk.Alignment(0, 0, 0, 0)
        align.set_padding(10, 20, 15, 15)
        self.createlabel = gtk.Label()
        align.add(self.createlabel)
        self.vbox.pack_start(align, False, False)

        rvbox = gtk.VBox()
        align = gtk.Alignment(0, 0, 0, 1)
        align.set_padding(0, 10, 40, 15)
        align.add(rvbox)
        self.vbox.pack_start(align, False, False)

        self.new_savegame_radio = gtk.RadioButton(label="Savegame Map File", group=self.open_savegame_radio)
        rvbox.add(self.new_savegame_radio)
        self.new_global_radio = gtk.RadioButton(label="Global Map File", group=self.open_savegame_radio)
        if c.book > 1:
            self.new_global_radio.set_tooltip_text('Book 2/3 global maps are hidden away inside the "datapak" '
                    'file, so creating a Global Book 2/3 map may not be worth it.')
        rvbox.add(self.new_global_radio)

        self.show_all()
        self.hide()
        self.set_initial()

    def set_initial(self, initial=True):
        if initial:
            self.set_title("Load or Create a Map")
            self.createlabel.set_markup("<b>Or, select the type of map you want to create:</b>")
            self.open_align_1.show()
            self.open_align_2.show()
            self.title_align.show()
            self.open_savegame_radio.set_active(True)
            self.resize(340, 288)
        else:
            self.set_title("Select New Map Type")
            self.createlabel.set_markup("<b>Select the type of map you want to create:</b>")
            self.open_align_1.hide()
            self.open_align_2.hide()
            self.title_align.hide()
            self.new_savegame_radio.set_active(True)
            self.resize(340, 160)

class ObjectSelWindow(ImageSelWindow):

    def setup_drawing_area(self, vbox, on_clicked, on_motion, on_expose):
        self.book = gtk.Notebook()
        vbox.pack_start(self.book, True, True)

        (sw, self.drawingarea_a) = self.create_drawing_area(on_clicked, on_motion, on_expose)
        self.drawingarea_a.set_name('objsel_a_area')
        self.label_a = gtk.Label('Set A (misc)')
        self.book.append_page(sw, self.label_a)

        (self.scrolltoggle, self.drawingarea_b) = self.create_drawing_area(on_clicked, on_motion, on_expose)
        self.drawingarea_b.set_name('objsel_b_area')
        self.label_b = gtk.Label('Set B (misc)')
        self.book.append_page(self.scrolltoggle, self.label_b)

        (sw, self.drawingarea_c) = self.create_drawing_area(on_clicked, on_motion, on_expose)
        self.drawingarea_c.set_name('objsel_c_area')
        self.label_c = gtk.Label('Set C (walls)')
        self.book.append_page(sw, self.label_c)

        (sw, self.drawingarea_d) = self.create_drawing_area(on_clicked, on_motion, on_expose)
        self.drawingarea_d.set_name('objsel_d_area')
        self.label_d = gtk.Label('Set D (trees)')
        self.book.append_page(sw, self.label_d)

class MapGUI(BaseGUI):

    # Editing modes that we can be in
    MODE_EDIT = 0
    MODE_MOVE = 1
    MODE_DRAW = 2
    MODE_ERASE = 3
    MODE_OBJECT = 4
    MODE_SCRIPT_ED = 5

    # Actions that a mouse click can take
    ACTION_NONE = -1
    ACTION_EDIT = 0
    ACTION_DRAG = 1
    ACTION_DRAW = 2
    ACTION_ERASE = 4
    ACTION_OBJECT = 5
    ACTION_SCRIPT_ED = 6

    # Mouse button constants
    MOUSE_LEFT = 1
    MOUSE_MIDDLE = 2
    MOUSE_RIGHT = 3

    # Mouse Mappings for the various modes
    mouse_action_maps = {
        MODE_EDIT: {
            MOUSE_LEFT: ACTION_EDIT,
            MOUSE_MIDDLE: ACTION_DRAG,
            MOUSE_RIGHT: ACTION_DRAG
            },
        MODE_MOVE: {
            MOUSE_LEFT: ACTION_DRAG,
            MOUSE_MIDDLE: ACTION_DRAG,
            MOUSE_RIGHT: ACTION_EDIT
            },
        MODE_DRAW: {
            MOUSE_LEFT: ACTION_DRAW,
            MOUSE_MIDDLE: ACTION_DRAG,
            MOUSE_RIGHT: ACTION_EDIT
            },
        MODE_ERASE: {
            MOUSE_LEFT: ACTION_ERASE,
            MOUSE_MIDDLE: ACTION_DRAG,
            MOUSE_RIGHT: ACTION_EDIT
            },
        MODE_OBJECT: {
            MOUSE_LEFT: ACTION_OBJECT,
            MOUSE_MIDDLE: ACTION_DRAG,
            MOUSE_RIGHT: ACTION_EDIT
            },
        MODE_SCRIPT_ED: {
            MOUSE_LEFT: ACTION_SCRIPT_ED,
            MOUSE_MIDDLE: ACTION_DRAG,
            MOUSE_RIGHT: ACTION_DRAG
            },
        }

    def __init__(self, options, prefs, req_book):
        self.options = options
        self.prefs = prefs
        self.path_init()
        self.req_book = req_book
        c.switch_to_book(self.req_book)

        # Call out to the base initialization
        self.base_init()

    def run(self):

        # Let's make sure our map object exists
        self.map = None

        self.tile_x = -1
        self.tile_y = -1
        self.tile_x_prev = -1
        self.tile_y_prev = -1
        self.cleantiles = []

        self.mapinit = False
        self.undo = None
        self.smartdraw = SmartDraw.new(c.book)

        # Start up our GUI
        self.builder = gtk.Builder()
        self.builder.add_from_file(self.datafile('mapgui.ui'))
        self.builder.add_from_file(self.datafile('itemgui.ui'))
        self.window = self.get_widget('mainwindow')
        self.itemwindow = self.get_widget('itemwindow')
        self.tilewindow = self.get_widget('tilewindow')
        self.itemwindow.set_transient_for(self.tilewindow)
        self.propswindow = self.get_widget('globalpropswindow')
        self.drawstatuswindow = self.get_widget('drawstatus_window')
        self.drawstatusbar = self.get_widget('drawstatus_bar')
        self.maparea = self.get_widget('maparea')
        self.mapname_mainscreen_label = self.get_widget('mapname_mainscreen')
        self.coords_label = self.get_widget('coords')
        self.mainscroll = self.get_widget('mainscroll')
        self.zoom_scale = self.get_widget('zoom_scale')
        self.zoom_in_button = self.get_widget('zoom_in_button')
        self.zoom_out_button = self.get_widget('zoom_out_button')
        self.floor_toggle = self.get_widget('floor_button')
        self.decal_toggle = self.get_widget('decal_button')
        self.object_toggle = self.get_widget('object_button')
        self.wall_toggle = self.get_widget('wall_button')
        self.tree_toggle = self.get_widget('tree_button')
        self.objectdecal_toggle = self.get_widget('objectdecal_button')
        self.entity_toggle = self.get_widget('entity_button')
        self.huge_gfx_toggle = self.get_widget('huge_gfx_button')
        self.barrier_hi_toggle = self.get_widget('barrier_hi_button')
        self.tilecontent_hi_toggle = self.get_widget('tilecontent_hi_button')
        self.entity_hi_toggle = self.get_widget('entity_hi_button')
        self.tilecontent_notebook = self.get_widget('tilecontent_notebook')
        self.itemsel = self.get_widget('itemselwindow')
        self.floorsel = self.get_widget('floorselwindow')
        self.composite_area = self.get_widget('composite_area')
        self.menu_undo = self.get_widget('menu_undo')
        self.menu_undo_label = self.menu_undo.get_children()[0]
        self.menu_redo = self.get_widget('menu_redo')
        self.menu_redo_label = self.menu_redo.get_children()[0]
        self.draw_floor_checkbox = self.get_widget('draw_floor_checkbox')
        self.draw_floor_spin = self.get_widget('draw_floor_spin')
        self.fill_map_spin = self.get_widget('fill_map_spin')
        self.draw_decal_checkbox = self.get_widget('draw_decal_checkbox')
        self.draw_decal_spin = self.get_widget('draw_decal_spin')
        self.draw_wall_checkbox = self.get_widget('draw_wall_checkbox')
        self.draw_wall_spin = self.get_widget('draw_wall_spin')
        self.draw_walldecal_checkbox = self.get_widget('draw_walldecal_checkbox')
        self.draw_walldecal_spin = self.get_widget('draw_walldecal_spin')
        self.draw_barrier = self.get_widget('draw_barrier')
        self.draw_barrier_seethrough = self.get_widget('draw_barrier_seethrough')
        self.erase_floor_checkbox = self.get_widget('erase_floor_checkbox')
        self.erase_decal_checkbox = self.get_widget('erase_decal_checkbox')
        self.erase_wall_checkbox = self.get_widget('erase_wall_checkbox')
        self.erase_walldecal_checkbox = self.get_widget('erase_walldecal_checkbox')
        self.erase_barrier = self.get_widget('erase_barrier')
        self.erase_entity_checkbox = self.get_widget('erase_entity_checkbox')
        self.erase_object_checkbox = self.get_widget('erase_object_checkbox')
        self.smartdraw_check = self.get_widget('smartdraw_check')
        self.smartdraw_container = self.get_widget('smartdraw_container')
        self.draw_smart_barrier = self.get_widget('draw_smart_barrier')
        self.draw_smart_wall = self.get_widget('draw_smart_wall')
        self.draw_smart_floor = self.get_widget('draw_smart_floor')
        self.smartdraw_floor_container = self.get_widget('smartdraw_floor_container')
        self.draw_straight_paths = self.get_widget('draw_straight_paths')
        self.draw_smart_walldecal = self.get_widget('draw_smart_walldecal')
        self.smart_randomize = self.get_widget('smart_randomize')
        self.smart_complex_objects = self.get_widget('smart_complex_objects')
        self.map_exception_window = self.get_widget('map_exception_window')
        self.map_exception_view = self.get_widget('map_exception_view')
        self.activity_label = self.get_widget('activity_label')
        self.draw_frame = self.get_widget('draw_frame')
        self.globalwarndialog = self.get_widget('globalwarndialog')
        self.globalwarn_check = self.get_widget('globalwarn_check')
        if (self.window):
            self.window.connect('destroy', gtk.main_quit)

        # Explicitly set our widget names (needed for gtk+ 2.20 compatibility)
        # See https://bugzilla.gnome.org/show_bug.cgi?id=591085
        for object in self.builder.get_objects():
            try:
                builder_name = gtk.Buildable.get_name(object)
                if builder_name:
                    object.set_name(builder_name)
            except TypeError:
                pass

        # Cursors for our editing modes
        self.edit_mode = self.MODE_EDIT
        self.cursor_move_drag = gtk.gdk.Cursor(gtk.gdk.DOT)
        self.cursor_map = {
            self.MODE_EDIT: None,
            self.MODE_MOVE: gtk.gdk.Cursor(gtk.gdk.FLEUR),
            self.MODE_DRAW: gtk.gdk.Cursor(gtk.gdk.PENCIL),
            self.MODE_ERASE: gtk.gdk.Cursor(gtk.gdk.CIRCLE),
            self.MODE_OBJECT: gtk.gdk.Cursor(gtk.gdk.BASED_ARROW_DOWN),
            self.MODE_SCRIPT_ED: None,
            }

        # Initialize item stuff
        self.curitemcategory = self.ITEM_MAP
        self.curitem = ''
        self.itemclipboard = None

        # Preferences window - also load in our graphics
        self.prefs_init(self.prefs)
        if (not self.require_gfx()):
            return
        try:
            self.gfx = Gfx.new(self.req_book, self.prefs, self.datadir)
        except Exception, e:
            self.errordialog('Error Loading Graphics', 'Graphics could not be initialized: %s' % (str(e)))
            sys.exit(1)

        # Show a slow-loading zip warning if necessary
        if c.book > 1 and not self.gfx.fast_zipfile:
            self.get_widget('render_slowzip_warning').show()
            self.drawstatuswindow.set_size_request(350, 200)
            warn = self.prefs.get_bool('mapgui', 'warn_slow_zip')
            if warn:
                dialog = self.get_widget('slowzipwarndialog')
                resp = dialog.run()
                if(self.get_widget('slowzipwarn_check').get_active() != warn):
                    self.prefs.set_bool('mapgui', 'warn_slow_zip', self.get_widget('slowzipwarn_check').get_active())
                    self.prefs.save()
                dialog.hide()
                if resp != gtk.RESPONSE_OK:
                    sys.exit(1)

        # Now that we're sure we have a data dir, load in our entities
        self.populate_entities()

        # Create these objects as soon as we have our entity list
        self.smartdraw.create_premade_objects()

        # ... and while we're at it, finish building some GUI elements
        self.map_gui_finish()

        # Event mask for processing hotkeys
        # (MOD2 is numlock; we don't care about that.  Dunno what 3-5 are, probably not used.)
        self.keymask = gtk.gdk.CONTROL_MASK|gtk.gdk.MOD1_MASK|gtk.gdk.MOD3_MASK
        self.keymask |= gtk.gdk.MOD4_MASK|gtk.gdk.MOD5_MASK

        # Manually connect a couple more signals that Glade can't handle for us automatically
        self.mainscroll.get_hadjustment().connect('changed', self.scroll_h_changed)
        self.mainscroll.get_vadjustment().connect('changed', self.scroll_v_changed)
        self.prev_scroll_h_cur = -1
        self.prev_scroll_h_max = -1
        self.prev_scroll_v_cur = -1
        self.prev_scroll_v_max = -1
        self.dragging = False
        self.drawing = False
        self.erasing = False

        # Set up the statusbar
        self.statusbar = self.get_widget('mainstatusbar')
        self.sbcontext = self.statusbar.get_context_id('Main Messages')

        # If we were given a filename, load it.  If not, create a new map,
        # or load one if the user wants.
        if (self.options['filename'] == None):
            if not self.on_new():
                return;
        else:
            if (not self.load_from_file(self.options['filename'])):
                if (not self.on_load()):
                    return
        self.get_widget('map_new_map_dialog').set_initial(False)

        # Set up our initial zoom levels and connect our signal to
        # the slider adjustment, so things work like we'd want.
        self.zoom_levels = [4, 8, 16, 24, 32, 52]
        if self.req_book > 1:
            self.zoom_levels.append(64)
        self.get_widget('map_zoom_adj').set_property('upper', len(self.zoom_levels)-1)
        default_zoom = self.prefs.get_int('mapgui', 'default_zoom')-1
        if (default_zoom >= len(self.zoom_levels)):
            default_zoom = len(self.zoom_levels)-1
        elif (default_zoom < 0):
            default_zoom = 0
        self.set_zoom_vars(default_zoom)
        self.zoom_adj = self.zoom_scale.get_adjustment()
        self.zoom_adj.set_value(default_zoom)
        self.zoom_adj.connect('value-changed', self.zoom_slider)

        # Some more vars to make sure exist
        self.guicache = None
        self.tilebuf = None
        self.blanktile = None
        self.basictile = None
        self.updating_map_checkboxes = False
        self.populating_entity_tab = False

        # Blank pixbuf to use in the tile editing window
        self.comp_pixbuf = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, True, 8, self.gfx.tile_width, self.gfx.tile_height*5)

        # Load in our mouse map (to determine which tile we're pointing at)
        self.mousemap = {}
        for zoom in self.zoom_levels:
            mapfile = self.datafile('iso_mousemap_%d.png' % (zoom))
            mapbuf = gtk.gdk.pixbuf_new_from_file(mapfile)
            if self.have_numpy:
                try:
                    self.mousemap[zoom] = mapbuf.get_pixels_array()
                except (RuntimeError, ImportError):
                    self.mousemap[zoom] = self.stupid_pixels_array(mapbuf)
            else:
                self.mousemap[zoom] = self.stupid_pixels_array(mapbuf)

        # ... initialize a couple of hidden spinboxes
        self.draw_floor_spin.set_value(1)
        self.draw_decal_spin.set_value(1)
        self.draw_wall_spin.set_value(1)
        self.draw_walldecal_spin.set_value(1)
        self.fill_map_spin.set_value(1)

        # Update our activity label
        self.update_activity_label()
        self.update_objectplace()

        # Now show our window
        self.window.show()

        # Uncomment this to have the app export a PNG of all images
        # on the commandline - also comment out the relevant stuff
        # in draw_map()
        #self.export_map_pngs()

        # ... and get into the main gtk loop
        gtk.main()

    def strip_tree_headers(self, layout, cell, model, iter, data):
        """
        A cell data function for use on ComboBoxes which use a TreeStore to
        hold data, which will make categories nonclickable, and also get rid
        of the headers in the submenu.
        """
        cell.set_property('sensitive', not model.iter_has_child(iter))

    def populate_entities(self):
        """
        Populates our entities, if need be.
        (Currently only does things for Book 2, since they can be sourced from
        a CSV file)
        """
        # x / y sizing
        # 0 / 0 1024x1024, sixteen to a row
        # 0 / 32 1024x1024, sixteen to a row
        # 32 / 0 1024x1024, ten to a row
        # 32 / 32 2048x2048, twenty-one to a row (with some left over)
        # 64 / 64 2048x2048, sixteen to a row
        if self.req_book == 1:
            return
        reader = csv.DictReader(cStringIO.StringIO(self.gfx.readfile('entities.csv', 'data')))
        for row in reader:
            if row['file'].strip() == '':
                continue
            xoff = int(row['Xoff'])
            yoff = int(row['Yoff'])
            width = 64 + xoff
            height = 64 + yoff
            name = row['Name']
            if (int(row['Dirs']) == 1):
                name = '%s *' % (name)
            script = row['Script'].strip()
            if script == '*':
                script = ''
            c.entitytable[int(row['ID'])] = c.EntHelper(name,
                int(row['HP']),
                '%s.png' % (row['file']),
                int(row['Dirs']),
                int(row['Align']),
                width,
                height,
                int(row['Frame']),
                int(row['Move']),
                script)

    def putstatus(self, text):
        """ Pushes a message to the status bar """
        self.statusbar.push(self.sbcontext, text)

    def key_handler(self, widget, event):
        """ Handles keypresses, which we'll use to simplify selecting drawing stuff. """
        # Cancel any dragging action currently active
        self.on_released()
        if (event.keyval < 256 and (event.state & self.keymask) == 0):
            key = chr(event.keyval).lower()
            if (key == 'm'):
                self.ctl_move_toggle.set_active(True)
            elif (key == 'e'):
                self.ctl_edit_toggle.set_active(True)
            elif (key == 'd'):
                self.ctl_draw_toggle.set_active(True)
            elif (key == 'r'):
                self.ctl_erase_toggle.set_active(True)
            elif (key == 'o'):
                self.ctl_object_toggle.set_active(True)

    def on_reload(self, widget=None):
        """ What to do when we're told to reload. """
        if self.map.df.filename != '':
            self.load_from_file(self.map.df.filename)
            self.update_main_map_name()
        else:
            self.infodialog('Reload Not Available', 'Sorry, this map isn\'t reloadable '
                    'because it has yet to be saved to disk.', self.window)

    def on_save(self, widget=None):
        """
        Save map to disk.  Calls out to on_save_as() if we don't have a filename yet.
        """
        if self.map.df.filename == '':
            self.on_save_as()
        else:
            self.map.write()
            self.putstatus('Saved ' + self.map.df.filename)
            self.update_main_map_name()

    def on_save_as(self, widget=None):
        """ Show the save-as dialog. """

        # Create the dialog
        dialog = gtk.FileChooserDialog('Save Map File...', None,
                                       gtk.FILE_CHOOSER_ACTION_SAVE,
                                       (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                        gtk.STOCK_SAVE_AS, gtk.RESPONSE_OK))
        dialog.set_default_response(gtk.RESPONSE_OK)
        dialog.set_transient_for(self.window)
        dialog.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
        dialog.set_do_overwrite_confirmation(True)

        # Figure out the initial path
        path = ''
        if self.map is None:
            pass
        elif self.map.df.filename == '':
            if self.map.is_savegame():
                path = self.get_current_savegame_dir()
            else:
                path = self.get_current_gamedir()
            dialog.set_current_folder(path)
        else:
            path = os.path.dirname(os.path.realpath(self.map.df.filename))

        # Set the initial path
        if (path != ''):
            dialog.set_current_folder(path)

        filter = gtk.FileFilter()
        filter.set_name("Map Files")
        filter.add_pattern("*.map")
        dialog.add_filter(filter)

        filter = gtk.FileFilter()
        filter.set_name("All files")
        filter.add_pattern("*")
        dialog.add_filter(filter)

        # Run the dialog and process its return values
        loop = True
        while loop:
            response = dialog.run()
            if response == gtk.RESPONSE_OK:

                if dialog.get_filename()[-4:].lower() != '.map':
                    new_filename = '%s.map' % (dialog.get_filename())
                    if os.path.exists(new_filename):
                        new_resp = self.confirmdialog('File Already Exists', 'A file named '
                                '"%s" already exists.  Do you want to replace it?' % (new_filename),
                                dialog)
                        if new_resp != gtk.RESPONSE_YES:
                            continue
                else:
                    new_filename = dialog.get_filename()

                # At this point we're committed to the save
                loop = False

                # If we're book 1, make sure that our Map ID is set properly
                if c.book == 1:
                    base_map_name = os.path.basename(new_filename)[:-4]
                    if base_map_name != self.map.mapid:
                        resp = self.confirmdialog('Update Map ID Field?', 'You are saving this map '
                                'to the file "%s", but the Map ID field <i>(available in the Map Properties '
                                'screen)</i> is set to "%s".  In order for your maps to save properly in '
                                'the game engine, they should be the same.  Do you want to update the Map '
                                'ID to match the filename?' % (base_map_name, self.map.mapid),
                                dialog)
                        if resp == gtk.RESPONSE_YES:
                            self.map.mapid = base_map_name

                # And now do the actual save
                self.map.df.filename = new_filename
                self.on_save()
                self.putstatus('Saved as %s' % (self.map.df.filename))
                self.infodialog('Notice', '<b>Note:</b> Any further "save" actions to this '
                        'map will be saved to the new filename, not the original filename.',
                        self.window)
                self.update_main_map_name()
            else:
                loop = False

        # Clean up
        dialog.destroy()

    def map_gui_finish(self):
        """
        This function is designed to finish drawing the base GUI, to either make up for
        shortcomings in Glade, or just because it's easier in code.  There's a nontrivial
        amount of overlap between this and what happens inside run(), but the philosophical
        difference I'm shooting for is that this function is creating actual GUI elements,
        whereas the stuff in run() should primarily just be initializing variables,
        assigning default values, etc.  It's a pretty fuzzy boundary regardless.
        """

        # Object Selection Window
        self.objsel_window = ObjectSelWindow(
            on_clicked=self.objsel_on_clicked,
            on_motion=self.objsel_on_motion,
            on_expose=self.objsel_on_expose)
        self.register_widget('objselwindow', self.objsel_window)
        self.objsel_window.set_transient_for(self.tilewindow)

        # Register ComboBoxEntry child objects since the new Glade doesn't
        comboboxentries = ['exit_north', 'exit_east', 'exit_south', 'exit_west',
                'music1', 'music2', 'atmos_sound_day', 'atmos_sound_night',
                'random_sound1', 'random_sound2', 'skybox']
        for var in comboboxentries:
            self.register_widget(var, self.get_widget('%s_combo' % (var)).child)
            self.get_widget(var).connect('changed', self.on_singleval_map_changed_str)

        # Finish populating Item windows (dependent on Book)
        self.window.set_title('Eschalon Book %d Map Editor' % (c.book))
        self.item_gui_finish(c.book)

        # Tell our ScriptEditor object (initialized in item_gui_finish) about ourselves,
        # so that it can throw up a dialog to choose a coordinate
        self.script_editor.set_gui(self)

        # Now show or hide form elements depending on the book version
        # Hide first, then show, so that we don't end up hiding elements
        # used in more than one book
        for item_class in (B1Item, B2Item, B3Item, B1Entity, B2Entity, B3Entity):
            if (item_class.book != c.book):
                self.set_book_elem_visibility(item_class, False)
        for item_class in (B1Item, B2Item, B3Item, B1Entity, B2Entity, B3Entity):
            if (item_class.book == c.book):
                self.set_book_elem_visibility(item_class, True)

        # Draw our control box
        ctlbox = self.get_widget('control_alignment')
        vbox = gtk.VBox()
        hbox = gtk.HBox()
        first = None
        for (name, text, key, image) in [
            ('edit', 'Edit', 'e', 'icon-pointer.png'),
            ('move', 'Move', 'm', 'icon-hand.png'),
            (None, None, None, None),
            ('draw', 'Draw', 'd', 'icon-draw.png'),
            ('erase', 'Erase', 'r', 'icon-erase.png'),
            ('object', 'Object', 'o', 'icon-object.png')]:
            if name is None:
                vbox.add(hbox)
                hbox = gtk.HBox()
                continue
            radio = gtk.RadioButton(first)
            radio.set_property('draw-indicator', False)
            radio.set_relief(gtk.RELIEF_NONE)
            if first is None:
                radio.set_active(True)
                first = radio
            self.register_widget('ctl_%s_toggle' % (name), radio)
            radio.add(gtk.image_new_from_file(self.datafile(image)))
            radio.set_tooltip_markup('%s <i>(%s)</i>' % (text, key))
            radio.connect('toggled', self.on_control_toggle)
            hbox.add(radio)
        vbox.add(hbox)
        ctlbox.add(vbox)
        vbox.show_all()

        # This used to happen at the start of run(), will have to do it
        # here instead.
        self.ctl_edit_toggle = self.get_widget('ctl_edit_toggle')
        self.ctl_move_toggle = self.get_widget('ctl_move_toggle')
        self.ctl_draw_toggle = self.get_widget('ctl_draw_toggle')
        self.ctl_erase_toggle = self.get_widget('ctl_erase_toggle')
        self.ctl_object_toggle = self.get_widget('ctl_object_toggle')

        # Not sure why this doesn't work properly just from Glade
        self.get_widget('music1_combo').set_tooltip_markup('Note that having an empty value here will crash Eschalon')

        # Unknown map properties
        table = self.get_widget('map_prop_unknown_table')
        if c.book == 1:
            self.input_uchar(table, 3, 'map_b1_last_xpos', '<i>Last-seen X Pos:</i>', 'Position your character was last seen at', self.on_singleval_map_changed_int)
            self.input_uchar(table, 4, 'map_b1_last_ypos', '<i>Last-seen Y Pos:</i>', 'Position your character was last seen at', self.on_singleval_map_changed_int)
        else:

            # Update sound labels for book 2
            self.get_widget('atmos_sound_day_label').set_text('Atmosphere (day)')
            self.get_widget('atmos_sound_day_combo').set_tooltip_markup('Note that having an empty value here will crash Eschalon')

        # Populate our wall type dropdown
        wstore = self.get_widget('barrier_store')
        wstore.append(['None', 0])
        wstore.append(['Normal Wall', 1])
        if c.book == 1:
            self.wallvals = (0, 1, 5)
        else:
            self.wallvals = (0, 1, 2, 5)
            wstore.append(['Restrict Movement', 2])
        wstore.append(['See-Through', 5])

        # Populate our tree set dropdown
        tstore = self.get_widget('tree_set_store')
        tstore.append(['Deciduous', 0])
        if c.book == 2:
            tstore.append(['Evergreen', 1])
            tstore.append(['Snow-Covered', 2])
        elif c.book == 3:
            tstore.append(['Swamp', 1])
            tstore.append(['Snow-Covered', 2])
            tstore.append(['Evergreen', 3])

        # Process our entity list, for use in the entity type dropdown
        # This is.... Not the greatest.  Ah well.  Keeping the monsters
        # and NPCs sorted separately seems worth it
        globalstore = self.get_widget('random_entity_store')
        globalstore.append(['(none)', 0])
        monsters = {}
        npcs = {}
        for (key, item) in c.entitytable.iteritems():
            if (item.friendly == 0):
                table = monsters
            else:
                table = npcs
            table[item.name] = key
        monsterkeys = monsters.keys()
        monsterkeys.sort()
        for key in monsterkeys:
            globalstore.append([key, monsters[key]])
        npckeys = npcs.keys()
        npckeys.sort()
        self.entitykeys = monsterkeys
        self.entitykeys.extend(npckeys)
        self.entityrev = monsters
        self.entityrev.update(npcs)
        box = self.get_widget('entid')
        self.useful_combobox(box)
        for key in self.entitykeys:
            box.append_text(key)

        # Grab some lists of files
        # Note that maplist will be empty for B2, but that's okay since B2 won't
        # end up using it.
        maplist = self.get_gamedir_filelist('data', 'map', False)
        musiclist = self.get_gamedir_filelist('music', 'ogg')
        atmoslist = self.get_gamedir_filelist('sound', 'wav', True, ['atmos_', 'wolfwood_'])
        randsoundlist = self.get_gamedir_filelist('sound', 'wav', True, ['rand_'])
        if c.book == 1:
            skyboxlist = ['back1.png', 'back2.png', 'back3.png']
        elif c.book == 2:
            skyboxlist = ['shear_wall.png']
        else:
            skyboxlist = []

        # Populate the dropdowns on our global properties window
        self.populate_comboboxentry('exit_north_combo', maplist)
        self.populate_comboboxentry('exit_east_combo', maplist)
        self.populate_comboboxentry('exit_south_combo', maplist)
        self.populate_comboboxentry('exit_west_combo', maplist)
        self.populate_comboboxentry('music1_combo', musiclist)
        self.populate_comboboxentry('music2_combo', musiclist)
        self.populate_comboboxentry('atmos_sound_day_combo', atmoslist)
        self.populate_comboboxentry('atmos_sound_night_combo', atmoslist)
        self.populate_comboboxentry('random_sound1_combo', randsoundlist)
        self.populate_comboboxentry('random_sound2_combo', randsoundlist)
        self.populate_comboboxentry('skybox_combo', skyboxlist)

        # And populate our object/tilecontent type dropdown as well
        self.object_type_list = {}
        self.object_type_list_rev = {}
        typebox = self.get_widget('tilecontentid_dd')
        self.useful_combobox(typebox)
        for (typeidx, (val, text)) in enumerate(c.tilecontenttypetable.items()):
            typebox.append_text('%d - %s' % (val, text))
            self.object_type_list[val] = typeidx
            self.object_type_list_rev[typeidx] = val

        # Populate our smartdraw decal preference dropdown
        store = self.get_widget('decalpref_store')
        store.append(['Grass', self.smartdraw.IDX_GRASS])
        store.append(['Sand', self.smartdraw.IDX_SAND])
        store.append(['Beach', self.smartdraw.IDX_BEACH])
        if c.book > 1:
            store.append(['Snow', self.smartdraw.IDX_SNOW])
            store.append(['Lava', self.smartdraw.IDX_LAVA])
        self.get_widget('decalpref').set_active(0)

        # Populate our object placement dropdown
        store = self.get_widget('objectplace_treestore')
        renderer = self.get_widget('objectplace_renderer')
        self.get_widget('objectplace_combo').set_cell_data_func(renderer, self.strip_tree_headers, None)
        set_start = False
        for (cat, objects) in self.smartdraw.premade_objects.get_all_sorted():
            catiter = store.append(None, [cat, -1, cat])
            for (idx, obj) in enumerate(objects):
                iter = store.append(catiter, [obj.name, idx, cat])
                if not set_start:
                    set_start = True
                    self.get_widget('objectplace_combo').set_active_iter(iter)

        # And set sizing for object placement variables
        lockspin = self.get_widget('objectplace_lock_spin')
        lockadj = self.get_widget('objectplace_lock_adj')
        trapstore = self.get_widget('objectplace_trap_store')
        for (key, name) in c.traptable.items():
            trapstore.append([name, key])
        self.get_widget('objectplace_trap_combo').set_active(0)
        if c.book == 1:
            lockspin.set_tooltip_markup('Lock levels run from zero to sixty.  '
                    'To create a slider lock, edit the object after creation.')
            lockadj.set_upper(60)
        else:
            self.get_widget('objectplace_loot_spin').set_tooltip_markup('Loot '
                    'levels run from zero (poor-quality) to ten (high-quality)')
            lockspin.set_tooltip_markup('Lock levels run from zero to ten.  '
                    'To create a combination lock, edit the object after creation.')
            lockadj.set_upper(10)

        # Resize some images for Book 2 sizes
        if c.book > 1:
            self.get_widget('composite_area').set_size_request(64, 160)
            self.get_widget('floorimg_image').set_size_request(64, 32)
            self.get_widget('decalimg_image').set_size_request(64, 32)
            self.get_widget('wallimg_image').set_size_request(64, 160)
            self.get_widget('walldecalimg_image').set_size_request(64, 96)
            self.get_widget('ent_tile_img').set_size_request(128, 128)
            self.get_widget('fill_map_img').set_size_request(64, 32)

        # Entity death script editor launcher
        self.setup_script_editor_launcher(self.get_widget('entscript_hbox'), self.get_widget('entscript'), self.tilewindow, True)

        # Global Props window script editor launchers
        if c.book > 1:
            self.setup_script_editor_launcher(self.get_widget('entrancescript_hbox'), self.get_widget('entrancescript'), self.propswindow, True)
            self.setup_script_editor_launcher(self.get_widget('returnscript_hbox'), self.get_widget('returnscript'), self.propswindow, True)
            self.setup_script_editor_launcher(self.get_widget('exitscript_hbox'), self.get_widget('exitscript'), self.propswindow, True)

        # Create our entity status values box
        if c.book > 1:
            container = self.get_widget('entity_data_main_vbox')
            
            vbox = gtk.VBox()
            self.register_widget('entity_status_box', vbox)
            container.pack_start(vbox, False, False)

            label = gtk.Label()
            label.set_markup('<b>Effects</b>')
            label.set_alignment(0, .5)
            label.set_padding(10, 7)
            vbox.add(label)

            align = gtk.Alignment()
            align.set_padding(0, 0, 40, 0)
            vbox.add(align)

            statvbox = gtk.VBox()
            align.add(statvbox)

            notelabel = gtk.Label()
            notelabel.set_alignment(0, .5)
            notelabel.set_markup('<b>Note:</b> Many of these don\'t actually affect the entity, '
                    'but they\'re all present in the datafile.')
            notelabel.set_line_wrap(True)
            statvbox.add(notelabel)

            table = gtk.Table(len(c.statustable), 2)
            statvbox.add(table)

            # Now add the statuses to table
            status_inv = dict([v,k] for k,v in c.statustable.items())
            for (idx, key) in enumerate(sorted(status_inv.keys())):
                name = 'ent_status_%d' % (status_inv[key])
                self.input_short(table, idx, name, key, None, self.on_ent_status_changed)

            # Don't forget to show everything
            container.show_all()

        # Add a WrapLabel in the Fill dialog
        adjust = self.get_widget('fill_map_text_adjust')
        label = WrapLabel('Select a tile to fill over the entire map.  If you '
                'check the <i>"Overwrite Existing Tiles"</i> checkbox, this will '
                'overwrite every single tile on the map.  Without the checkbox, '
                'any tiles with existing floor images will be left alone.  '
                'If you have the necessary SmartDraw options enabled, this '
                'will randomize the terrain somewhat, if possible.  Note '
                'that this operation is <b>not</b> Undoable at the moment, and '
                'will erase your Undo stack, so save your map first if you\'re '
                'not sure.')
        # set_alignment doesn't seem to work with our WrapLabel
        #label.set_alignment(gtk.JUSTIFY_CENTER)
        adjust.add(label)
        adjust.show_all()

        # "New Map" dialog (previously in Glade, but Glade continues to be awful)
        dialog = NewMapDialog()
        self.register_widget('map_new_map_dialog', dialog)

        # Increase the height of our tilewindow, if gtk thinks we have room.
        if gtk.gdk.screen_height() > 900:
            (cur_width, cur_height) = self.tilewindow.get_size_request()
            self.tilewindow.set_size_request(cur_width, 800)
            (cur_width, cur_height) = self.propswindow.get_size_request()
            self.propswindow.set_size_request(cur_width, 750)

        # Dictionary of signals.
        dic = { 'gtk_main_quit': self.gtk_main_quit,
                'on_new': self.on_new,
                'on_load': self.on_load,
                'on_reload': self.on_reload,
                'on_about': self.on_about,
                'on_save': self.on_save,
                'on_save_as': self.on_save_as,
                'on_export_clicked': self.on_export_clicked,
                'on_undo': self.on_undo,
                'on_redo': self.on_redo,
                'on_fill': self.on_fill,
                'on_clicked': self.on_clicked,
                'on_released': self.on_released,
                'on_control_toggle': self.on_control_toggle,
                'key_handler': self.key_handler,
                'zoom_in': self.zoom_in,
                'zoom_out': self.zoom_out,
                'format_zoomlevel': self.format_zoomlevel,
                'on_mouse_changed': self.on_mouse_changed,
                'expose_map': self.expose_map,
                'map_toggle': self.map_toggle,
                'on_healthmaxbutton_clicked': self.on_healthmaxbutton_clicked,
                'on_setinitial_clicked': self.on_setinitial_clicked,
                'on_entid_changed': self.on_entid_changed,
                'on_tilecontentid_changed': self.on_tilecontentid_changed,
                'on_tilecontentid_dd_changed': self.on_tilecontentid_dd_changed,
                'on_singleval_tile_changed_int': self.on_singleval_tile_changed_int,
                'on_singleval_ent_changed_int': self.on_singleval_ent_changed_int,
                'on_singleval_ent_changed_str': self.on_singleval_ent_changed_str,
                'on_singleval_map_changed_int': self.on_singleval_map_changed_int,
                'on_singleval_map_changed_str': self.on_singleval_map_changed_str,
                'on_dropdown_idx_map_changed': self.on_dropdown_idx_map_changed,
                'on_direction_changed': self.on_direction_changed,
                'on_map_flag_changed': self.on_map_flag_changed,
                'on_barrier_changed': self.on_barrier_changed,
                'on_entity_toggle': self.on_entity_toggle,
                'on_tilecontent_add': self.on_tilecontent_add,
                'on_floor_changed': self.on_floor_changed,
                'on_draw_floor_changed': self.on_draw_floor_changed,
                'on_decal_changed': self.on_decal_changed,
                'on_draw_decal_changed': self.on_draw_decal_changed,
                'on_wall_changed': self.on_wall_changed,
                'on_draw_wall_changed': self.on_draw_wall_changed,
                'on_walldecal_changed': self.on_walldecal_changed,
                'on_draw_walldecal_changed': self.on_draw_walldecal_changed,
                'on_colorsel_clicked': self.on_colorsel_clicked,
                'on_tilewindow_close': self.on_tilewindow_close,
                'on_prop_button_clicked': self.on_prop_button_clicked,
                'on_propswindow_close': self.on_propswindow_close,
                'on_prefs': self.on_prefs,
                'on_abort_render': self.on_abort_render,
                'open_floorsel': self.open_floorsel,
                'open_draw_floorsel': self.open_draw_floorsel,
                'open_decalsel': self.open_decalsel,
                'open_draw_decalsel': self.open_draw_decalsel,
                'open_walldecalsel': self.open_walldecalsel,
                'open_draw_walldecalsel': self.open_draw_walldecalsel,
                'open_draw_objsel': self.open_draw_objsel,
                'open_objsel': self.open_objsel,
                'open_fill_floorsel': self.open_fill_floorsel,
                'on_fill_floor_changed': self.on_fill_floor_changed,
                'on_draw_smart_floor_toggled': self.on_draw_smart_floor_toggled,
                'on_smartdraw_check_toggled': self.on_smartdraw_check_toggled,
                'draw_check_all': self.draw_check_all,
                'draw_uncheck_all': self.draw_uncheck_all,
                'highlight_check_all': self.highlight_check_all,
                'highlight_uncheck_all': self.highlight_uncheck_all,
                'update_activity_label': self.update_activity_label,
                'draw_map': self.draw_map,
                'update_objectplace': self.update_objectplace,
                }
        dic.update(self.item_signals())
        # Really we should only attach the signals that will actually be sent, but this
        # should be fine here, anyway.
        self.builder.connect_signals(dic)

    def on_prefs(self, widget=None):
        """ Override on_prefs a bit. """
        (changed, alert_changed) = super(MapGUI, self).on_prefs(widget)
        if (changed and alert_changed):
            self.infodialog('Preference Change Notification', '<b>Note:</b> You must '
                'restart the application for the preferences change to take effect.', self.window)

    def on_export_clicked(self, widget=None):
        """ Used to export a PNG of the current map image to disk. """

        # Create the dialog
        dialog = gtk.FileChooserDialog('Export Image...', None,
                                       gtk.FILE_CHOOSER_ACTION_SAVE,
                                       (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                        gtk.STOCK_SAVE_AS, gtk.RESPONSE_OK))
        dialog.set_default_response(gtk.RESPONSE_OK)
        dialog.set_transient_for(self.window)
        dialog.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
        dialog.set_do_overwrite_confirmation(True)
        infolabel = gtk.Label()
        infolabel.set_markup('<b>Note:</b> Only PNG images are supported.  If you name your export something other than .png, it will still be a PNG image.  Also note that an export at the fully-zoomed-in level will take about 25MB.')
        infolabel.set_line_wrap(True)
        dialog.set_extra_widget(infolabel)
        if (self.map != None):
            path = os.path.dirname(os.path.realpath(self.map.df.filename))
            if (path != ''):
                dialog.set_current_folder(path)

        filter = gtk.FileFilter()
        filter.set_name("PNG Files")
        filter.add_pattern("*.png")
        dialog.add_filter(filter)

        # Run the dialog and process its return values
        response = dialog.run()
        if response == gtk.RESPONSE_OK:
            filename = dialog.get_filename()
            self.guicache.write_to_png(filename)
            self.putstatus('Image exported to %s' % (filename))

        # Clean up
        dialog.destroy()

    def update_main_map_name(self):
        """
        Updates the text area above the map with the current map name.
        """
        if (c.book == 1 and
                self.map.df.filename != '' and
                os.path.basename(self.map.df.filename)[:-4] != self.map.mapid):
            self.mapname_mainscreen_label.set_markup('%s <span color="red">(Map ID Mismatch)</span>' %
                    (self.map.mapname))
            self.mapname_mainscreen_label.set_tooltip_text('This map is saved to a file named "%s" '
                    'but the Map ID is set to "%s" - this will cause problems with saving the map '
                    'state, inside Eschalon.  You should change this value in "Map Properties."' %
                    (os.path.basename(self.map.df.filename), self.map.mapid))
        else:
            self.mapname_mainscreen_label.set_text(self.map.mapname)
            self.mapname_mainscreen_label.set_has_tooltip(False)

    def setup_new_map(self):
        """
        Sets various GUI elements which need setting, once we have a "new"
        map object.  This is called currently from on_new() and load_from_file()
        """

        # Update the map title
        self.update_main_map_name()

        # Instansiate our "undo" object so we can handle that
        self.undo = Undo(self.map)
        self.update_undo_gui()

        # Load the new map into our SmartDraw object
        self.smartdraw.set_map(self.map)
        self.smartdraw.set_gui(self)

        # Load information from the character
        if (self.mapinit):
            self.draw_map()
            self.update_wall_selection_image()

    def on_new(self, widget=None):
        """
        Constructs a new map from scratch
        """

        # Confirm if we already have a map
        if self.map is not None:
            resp = self.confirmdialog('Create new Map?', 'Unsaved changes will be lost!  Continue?', self.window)
            if resp != gtk.RESPONSE_YES:
                return False

        # Figure out what type of map to create
        dialog = self.get_widget('map_new_map_dialog')
        resp = dialog.run()
        dialog.hide()
        if resp != gtk.RESPONSE_OK:
            return False

        # Our "new map" dialog will have a couple of "open" options on
        # it, if it's the initial dialog shown.  Check for those and
        # process on_load() instead, if we've chosen to do that.
        if dialog.open_global_radio.get_active() or dialog.open_savegame_radio.get_active():
            if self.on_load():
                return True
            else:
                # Recursion!  If a user cancels out of the load dialog, they may want to
                # create a new map instead.  They can cancel out directly from there.
                return self.on_new()

        # Now create a new map
        self.map = Map.load('', self.req_book, self.req_book)
        self.map.set_savegame(dialog.new_savegame_radio.get_active())
        
        # A few values need to be set to avoid crashes
        if c.book == 1:
            self.map.music1 = 'overland_1.ogg'
            self.map.atmos_sound_day = 'atmos_birds.wav'
        elif c.book == 2:
            self.map.music1 = 'eb2_overland1.ogg'
            self.map.atmos_sound_day = 'atmos_birds.wav'
        elif c.book == 3:
            self.map.version = '0.992'
            self.map.music1 = 'book3_steps_of_the_wayfarer_dj.ogg'
            self.map.atmos_sound_day = 'atmos_birds.wav'
        self.putstatus('Editing a new map')
        self.map.mapname = 'New Map'
        self.setup_new_map()

        # Return
        return True

    # Use this to display the loading dialog, and deal with the main window accordingly
    def on_load(self, widget=None):
        
        # Blank out the main area
        #self.mainbook.set_sensitive(False)

        # Create the dialog
        dialog = gtk.FileChooserDialog('Open New Map File...', None,
                                       gtk.FILE_CHOOSER_ACTION_OPEN,
                                       (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                        gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        dialog.set_default_response(gtk.RESPONSE_OK)
        dialog.set_transient_for(self.window)
        dialog.set_position(gtk.WIN_POS_CENTER_ON_PARENT)

        # Figure out what our initial path should be
        path = ''
        if self.map == None:
            newdialog = self.get_widget('map_new_map_dialog')
            if newdialog.open_global_radio.get_active():
                path = self.get_current_gamedir()
            else:
                path = self.get_current_savegame_dir()
        elif self.map.df.filename == '':
            if self.map.is_savegame():
                path = self.get_current_savegame_dir()
            else:
                path = self.get_current_gamedir()
        else:
            path = os.path.dirname(os.path.realpath(self.map.df.filename))

        # Set the initial path
        if (path != '' and os.path.isdir(path)):
            dialog.set_current_folder(path)

        filter = gtk.FileFilter()
        filter.set_name("Map Files")
        filter.add_pattern("*.map")
        dialog.add_filter(filter)

        filter = gtk.FileFilter()
        filter.set_name("All files")
        filter.add_pattern("*")
        dialog.add_filter(filter)

        # Run the dialog and process its return values
        retval = False
        rundialog = True
        while (rundialog):
            rundialog = False
            response = dialog.run()
            if response == gtk.RESPONSE_OK:
                if self.load_from_file(dialog.get_filename()):
                    retval = True
                else:
                    rundialog = True

        # Clean up
        dialog.destroy()
        if retval:
            self.update_main_map_name()

        # Return our results
        return retval

    # Use this to load in a map from a file
    def load_from_file(self, filename):

        # Load the file, if we can
        try:
            map = Map.load(filename, None, self.req_book)
            map.read()
        except LoadException, e:
            self.errordialog('Load Error', '<b>Error:</b> The specified file could not '
                    'be loaded.  Please choose a different file and try again.'
                    "\n\n"
                    'The actual error given was: <tt>%s</tt>' % (str(e)),
                    self.window)
            return False

        # Basic vars
        self.map = map

        # Update our status bar
        self.putstatus('Editing ' + self.map.df.filename)

        # Set up our other GUI elements
        self.setup_new_map()

        # If we appear to be editing a global map file and haven't
        # been told otherwise, show a dialog warning the user
        warn = self.prefs.get_bool('mapgui', 'warn_global_map')
        if (not map.is_savegame() and warn and filename.find(self.get_current_gamedir()) != -1):
            self.globalwarn_check.set_active(warn)
            resp = self.globalwarndialog.run()
            self.globalwarndialog.hide()
            if (self.globalwarn_check.get_active() != warn):
                self.prefs.set_bool('mapgui', 'warn_global_map', self.globalwarn_check.get_active())
                self.prefs.save()

        # Return success
        return True

    def on_abort_render(self, widget=None):
        """
        A hard quit.  Not terribly friendly, but the way we're
        processing loading doesn't lend itself to graceful failbacks.
        This is mostly going to just be called if something goes
        catastrophically wrong, anyway.
        """
        sys.exit(0)

    def gtk_main_quit(self, widget=None, event=None):
        """ Main quit function. """
        response = self.confirmdialog('Continue with Quit?', 'Unsaved changes will be lost!  Really quit?', self.window)
        if (response == gtk.RESPONSE_YES):
            gtk.main_quit()
        else:
            return True

    # Show the About dialog
    def on_about(self, widget):
        global app_name, version, url, authors

        about = self.get_widget('aboutwindow')

        # If the object doesn't exist in our cache, create it
        if (about == None):
            about = gtk.AboutDialog()
            about.set_transient_for(self.window)
            about.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
            about.set_name(app_name)
            about.set_version(version)
            about.set_website(url)
            about.set_authors(authors)
            licensepath = os.path.join(os.path.split(os.path.dirname(__file__))[0], 'COPYING.txt')
            if (os.path.isfile(licensepath)):
                try:
                    df = open(licensepath, 'r')
                    about.set_license(df.read())
                    df.close()
                except:
                    pass
            iconpath = self.datafile('eb1_icon_64.png')
            if (os.path.isfile(iconpath)):
                try:
                    about.set_logo(gtk.gdk.pixbuf_new_from_file(iconpath))
                except:
                    pass
            self.register_widget('aboutwindow', about, False)

        # Show the about dialog
        #self.mainbook.set_sensitive(False)
        about.run()
        about.hide()
        #self.mainbook.set_sensitive(True)

    def on_draw_smart_floor_toggled(self, widget):
        """ Handle the smart-floor toggling. """
        self.smartdraw_floor_container.set_sensitive(widget.get_active())

    def on_smartdraw_check_toggled(self, widget):
        """
        Deactivate/Activate smart draw functions
        """
        self.smartdraw_container.set_sensitive(widget.get_active())

    def update_undo_gui(self):
        """
        Handle updating things if undo or redo is called.  This
        will activate/deactivate the necessary menu items, etc.
        """
        if (self.undo.have_undo()):
            self.menu_undo.set_sensitive(True)
            history = self.undo.get_undo()
            self.menu_undo_label.set_text('Undo: %s to (%d, %d)' % (history.text, history.x, history.y))
        else:
            self.menu_undo.set_sensitive(False)
            self.menu_undo_label.set_text('Undo')
        if (self.undo.have_redo()):
            self.menu_redo.set_sensitive(True)
            history = self.undo.get_redo()
            self.menu_redo_label.set_text('Redo: %s to (%d, %d)' % (history.text, history.x, history.y))
        else:
            self.menu_redo.set_sensitive(False)
            self.menu_redo_label.set_text('Redo')
        #self.undo.report()

    def on_undo(self, widget=None):
        """ Process a user Undo action """
        # We're checking for hugegfx stuff here only on the "main" tile,
        # on the theory that no action would alter a hugegfx unless it was
        # directly on that tile.  I believe that to be the case currently,
        # though perhaps that needs to get revisited at some point.
        if self.undo.have_undo():
            history = self.undo.get_undo()
            self.store_hugegfx_state(self.map.tiles[history.y][history.x])
            for (x, y) in self.undo.undo():
                self.redraw_tile(x, y)
            self.update_undo_gui()
            if self.check_hugegfx_state(self.map.tiles[history.y][history.x]):
                self.draw_map()

    def on_redo(self, widget=None):
        """ Process a user Redo action """
        # See on_undo() for some notes about the hugegfx stuff
        if self.undo.have_redo():
            history = self.undo.get_redo()
            self.store_hugegfx_state(self.map.tiles[history.y][history.x])
            for (x, y) in self.undo.redo():
                self.redraw_tile(x, y)
            self.update_undo_gui()
            if self.check_hugegfx_state(self.map.tiles[history.y][history.x]):
                self.draw_map()

    def on_fill(self, widget=None):
        """
        What to do when the user selects "Fill" from the Edit menu (or wherever
        that ends up living).  Should just open the dialog box and then process.
        """
        dialog = self.get_widget('fill_map_dialog')
        resp = dialog.run()
        dialog.hide()
        if resp == gtk.RESPONSE_OK:
            val = int(self.get_widget('fill_map_spin').get_value())
            pool = []
            if self.smartdraw_check.get_active() and self.smart_randomize.get_active():
                pool = self.smartdraw.get_random_terrain_pool(val)
            # Split these out to avoid doing more checks than needed
            # inside the loop itself
            if self.get_widget('fill_map_overwrite').get_active():
                if len(pool) < 2:
                    for row in self.map.tiles:
                        for tile in row:
                            tile.floorimg = val
                else:
                    for row in self.map.tiles:
                        for tile in row:
                            tile.floorimg = random.choice(pool)
            else:
                if len(pool) < 2:
                    for row in self.map.tiles:
                        for tile in row:
                            if tile.floorimg == 0:
                                tile.floorimg = val
                else:
                    for row in self.map.tiles:
                        for tile in row:
                            if tile.floorimg == 0:
                                tile.floorimg = random.choice(pool)
            self.draw_map()

            # Clear out "Undo" - we're not hooking into this yet.
            self.undo = Undo(self.map)
            self.update_undo_gui()

    def update_objectplace(self, widget=None):
        """
        What happens when our Object Placement dropdown changes.
        """
        self.update_activity_label()
        obj = self.get_cur_object_placement()
        self.get_widget('objectplace_lock_label').set_sensitive(obj.do_lock)
        self.get_widget('objectplace_lock_spin').set_sensitive(obj.do_lock)
        self.get_widget('objectplace_trap_label').set_sensitive(obj.do_trap)
        self.get_widget('objectplace_trap_combo').set_sensitive(obj.do_trap)
        if c.book > 1:
            self.get_widget('objectplace_loot_label').set_sensitive(obj.do_loot)
            self.get_widget('objectplace_loot_spin').set_sensitive(obj.do_loot)

    def populate_color_selection(self):
        img = self.get_widget('color_img')
        pixbuf = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, True, 8, 30, 30)
        pixbuf.fill(self.map.rgb_color())
        img.set_from_pixbuf(pixbuf)
        self.get_widget('color_rgb_label').set_markup('<i>(RGB: %d, %d, %d)</i>' %
                (self.map.color_r, self.map.color_g, self.map.color_b))

    def on_prop_button_clicked(self, widget=None):
        """ Show the global properties window. """
        if (self.map.is_savegame()):
            self.get_widget('maptype').set_text('From Savegame')
        else:
            self.get_widget('maptype').set_text('Global Map File')
        self.get_widget('mapname').set_text(self.map.mapname)
        self.get_widget('music1').set_text(self.map.music1)
        self.get_widget('music2').set_text(self.map.music2)
        self.get_widget('atmos_sound_day').set_text(self.map.atmos_sound_day)
        if c.book > 1:
            self.cur_tree_set = self.map.tree_set
            for (idx, row) in enumerate(self.get_widget('tree_set').get_model()):
                if row[1] == self.map.tree_set:
                    self.get_widget('tree_set').set_active(idx)
                    continue
            for flag in [0x80, 0x40, 0x20, 0x10, 0x08, 0x04, 0x02, 0x01]:
                self.get_widget('map_flags_%02X' % (flag)).set_active(((self.map.map_flags & flag) == flag))
            ent_store = self.get_widget('random_entity_store')
            for (widget, entid) in [
                    (self.get_widget('random_entity_1'), self.map.random_entity_1),
                    (self.get_widget('random_entity_2'), self.map.random_entity_2)]:
                iter = ent_store.get_iter_first()
                while iter is not None:
                    if ent_store.get_value(iter, 1) == entid:
                        widget.set_active_iter(iter)
                        break
                    iter = ent_store.iter_next(iter)
        self.get_widget('skybox').set_text(self.map.skybox)
        self.populate_color_selection()
        self.get_widget('color_a').set_value(self.map.color_a)
        self.get_widget('parallax_x').set_value(self.map.parallax_x)
        self.get_widget('parallax_y').set_value(self.map.parallax_y)
        if c.book == 1:
            self.get_widget('mapid').set_text(self.map.mapid)
            self.get_widget('exit_north').set_text(self.map.exit_north)
            self.get_widget('exit_east').set_text(self.map.exit_east)
            self.get_widget('exit_south').set_text(self.map.exit_south)
            self.get_widget('exit_west').set_text(self.map.exit_west)
            self.get_widget('map_unknownh1').set_value(self.map.map_unknownh1)
            self.get_widget('clouds').set_value(self.map.clouds)
            self.get_widget('map_b1_last_xpos').set_value(self.map.map_b1_last_xpos)
            self.get_widget('map_b1_last_ypos').set_value(self.map.map_b1_last_ypos)
            self.get_widget('map_b1_outsideflag').set_value(self.map.map_b1_outsideflag)
        else:
            self.get_widget('entrancescript').set_text(self.map.entrancescript)
            self.get_widget('returnscript').set_text(self.map.returnscript)
            self.get_widget('exitscript').set_text(self.map.exitscript)
            self.get_widget('random_sound1').set_text(self.map.random_sound1)
            if c.book == 3:
                self.get_widget('atmos_sound_night').set_text(self.map.atmos_sound_night)
                self.get_widget('random_sound2').set_text(self.map.random_sound2)
                self.get_widget('cloud_offset_x').set_value(self.map.cloud_offset_x)
                self.get_widget('cloud_offset_y').set_value(self.map.cloud_offset_y)
        self.propswindow.show()

    def on_propswindow_close(self, widget, event=None):
        self.update_main_map_name()
        self.propswindow.hide()
        if (c.book > 1 and self.cur_tree_set != self.map.tree_set):
            self.draw_map()
            self.update_wall_selection_image()
        return True

    def update_wall_selection_image(self):
        """
        In Book 2, there are various circumstances under which our tree_set
        may change (editing the property window, loading a new map, etc), and
        if we have a tree currently selected on our drawing/editing tools,
        that graphic won't get updated unless we do so manually.
        """
        if c.book > 1:
            self.on_draw_wall_changed(self.get_widget('draw_wall_spin'))
            self.on_wall_changed(self.get_widget('wallimg'), False)

    def on_colorsel_clicked(self, widget):
        dialog = gtk.ColorSelectionDialog('Select Overlay Color')
        dialog.set_transient_for(self.window)
        dialog.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
        dialog.colorsel.set_current_color(gtk.gdk.Color(self.map.color_r*257, self.map.color_g*257, self.map.color_b*257))
        response = dialog.run()
        if (response == gtk.RESPONSE_OK):
            color = dialog.colorsel.get_current_color()
            self.map.color_r = int(color.red/257)
            self.map.color_g = int(color.green/257)
            self.map.color_b = int(color.blue/257)
            self.populate_color_selection()
        dialog.destroy()

    def on_tilecontent_str_changed(self, widget):
        """ When a tilecontent string changes. """
        wname = widget.get_name()
        (labelname, page) = wname.rsplit('_', 1)
        page = int(page)
        tilecontent = self.map.tiles[self.tile_y][self.tile_x].tilecontents[page]
        if (tilecontent is not None):
            if (labelname[:9] == 'item_name'):
                (varname, item_num) = labelname.rsplit('_', 1)
                item_num = int(item_num)
                tilecontent.items[item_num].item_name = widget.get_text()
            else:
                tilecontent.__dict__[labelname] = widget.get_text()

    def on_tilecontent_int_changed(self, widget):
        """ When a tilecontent integer changes. """
        wname = widget.get_name()
        (labelname, page) = wname.rsplit('_', 1)
        page = int(page)
        tilecontent = self.map.tiles[self.tile_y][self.tile_x].tilecontents[page]
        if (tilecontent is not None):
            tilecontent.__dict__[labelname] = int(widget.get_value())

    def on_locklevel_changed(self, widget):
        """ When our lock level changes. """
        self.on_tilecontent_int_changed(widget)
        wname = widget.get_name()
        (labelname, page) = wname.rsplit('_', 1)
        if c.book == 1:
            otherlabel = self.get_widget('other_%d_label' % (int(page)))
            if (int(widget.get_value()) == 99):
                otherlabel.set_text('Slider Combination:')
            else:
                otherlabel.set_markup('<i>Other Value (0-3):</i>')
        else:
            sliderloot = self.get_widget('slider_loot_%d_label' % (int(page)))
            if (int(widget.get_value()) == 12):
                sliderloot.set_text('Slider Combination:')
            else:
                sliderloot.set_markup('Loot Level (0-10):')

    def update_ent_tile_img(self):
        entity = self.map.tiles[self.tile_y][self.tile_x].entity
        entbuf = self.gfx.get_entity(entity.entid, entity.direction, None, True)
        if (entbuf is None):
            self.get_widget('ent_tile_img').set_from_stock(gtk.STOCK_MISSING_IMAGE, 2)
        else:
            self.get_widget('ent_tile_img').set_from_pixbuf(entbuf)

    def on_entid_changed(self, widget):
        """ Special case for changing the entity ID. """
        idx = widget.get_active()
        name = self.entitykeys[idx]
        entid = self.entityrev[name]
        entity = self.map.tiles[self.tile_y][self.tile_x].entity
        entity.entid = entid
        if (entid in c.entitytable):
            # We set the button out here in case we were editing a Global map and
            # then load a savegame, and edit a tile which has an entity that we
            # already had selected.
            button = self.get_widget('healthmaxbutton')
            health = c.entitytable[entid].health
            button.set_label('Set to Max Health (%d)' % (health))
            if not self.populating_entity_tab and entity.savegame:
                if c.book > 1:
                    # Entscript is present in non-savegame files, but the "global" script
                    # that we know about (from the CSV) appears to be filled in by the
                    # game engine after loading the main map.  The entscripts found in
                    # the global map files are "special" ones like keys that only certain
                    # monsters drop, etc.
                    self.get_widget('entscript').set_text(c.entitytable[entid].entscript)
                self.get_widget('health').set_value(health)
                self.get_widget('movement').set_value(c.entitytable[entid].movement)
                self.get_widget('friendly').set_value(c.entitytable[entid].friendly)
            self.update_ent_tile_img()

    def on_ent_status_changed(self, widget):
        """ What to do when an entity status value changes. """
        wname = widget.get_name()
        (shortname, idx) = wname.rsplit('_', 1)
        idx = int(idx)
        ent = self.map.tiles[self.tile_y][self.tile_x].entity
        ent.statuses[idx] = int(widget.get_value())

    def on_direction_changed(self, widget):
        """ Special case for changing the entity direction. """
        wname = widget.get_name()
        ent = self.map.tiles[self.tile_y][self.tile_x].entity
        ent.__dict__[wname] = widget.get_active() + 1
        self.update_ent_tile_img()

    def on_singleval_ent_changed_int(self, widget):
        """ Update the appropriate bit in memory. """
        wname = widget.get_name()
        ent = self.map.tiles[self.tile_y][self.tile_x].entity
        ent.__dict__[wname] = int(widget.get_value())

    def on_singleval_ent_changed_str(self, widget):
        """ Update the appropriate bit in memory. """
        wname = widget.get_name()
        ent = self.map.tiles[self.tile_y][self.tile_x].entity
        ent.__dict__[wname] = widget.get_text()

    def on_singleval_map_changed_int(self, widget):
        """ Update the appropriate bit in memory. """
        wname = widget.get_name()
        map = self.map
        map.__dict__[wname] = int(widget.get_value())

    def on_singleval_map_changed_str(self, widget):
        """ Update the appropriate bit in memory. """
        wname = widget.get_name()
        map = self.map
        map.__dict__[wname] = widget.get_text()

    def on_dropdown_idx_changed(self, widget, object):
        """ NOT appropriate for use as a handler, needs an object passed in. """

    def on_dropdown_idx_map_changed(self, widget):
        """ Update the appropriate bit in memory. """
        wname = widget.get_name()
        iter = widget.get_active_iter()
        model = widget.get_model()
        val = model.get_value(iter, 1)
        self.map.__dict__[wname] = val

    def on_dropdown_idx_tile_changed(self, widget):
        """ Update the appropriate bit in memory. """

    def on_singleval_tile_changed_int(self, widget):
        """ Update the appropriate bit in memory. """
        wname = widget.get_name()
        tile = self.map.tiles[self.tile_y][self.tile_x]
        tile.__dict__[wname] = int(widget.get_value())

    def on_floor_changed(self, widget):
        """ Update the appropriate image when necessary. """
        self.on_singleval_tile_changed_int(widget)
        pixbuf = self.gfx.get_floor(int(widget.get_value()), None, True)
        if (pixbuf is None):
            self.get_widget('floorimg_image').set_from_stock(gtk.STOCK_EDIT, 2)
        else:
            self.get_widget('floorimg_image').set_from_pixbuf(pixbuf)
        self.update_composite()

    def on_draw_floor_changed(self, widget):
        """ Update the appropriate image when necessary. """
        pixbuf = self.gfx.get_floor(int(widget.get_value()), None, True)
        if (pixbuf is None):
            self.get_widget('draw_floor_img').set_from_stock(gtk.STOCK_EDIT, 2)
        else:
            self.get_widget('draw_floor_img').set_from_pixbuf(pixbuf)

    def on_fill_floor_changed(self, widget):
        """ Update the appropriate image when necessary. """
        pixbuf = self.gfx.get_floor(int(widget.get_value()), None, True)
        if (pixbuf is None):
            self.get_widget('fill_map_img').set_from_stock(gtk.STOCK_EDIT, 2)
        else:
            self.get_widget('fill_map_img').set_from_pixbuf(pixbuf)

    def on_decal_changed(self, widget):
        """ Update the appropriate image when necessary. """
        self.on_singleval_tile_changed_int(widget)
        pixbuf = self.gfx.get_decal(int(widget.get_value()), None, True)
        if (pixbuf is None):
            self.get_widget('decalimg_image').set_from_stock(gtk.STOCK_EDIT, 2)
        else:
            self.get_widget('decalimg_image').set_from_pixbuf(pixbuf)
        self.update_composite()

    def on_draw_decal_changed(self, widget):
        """ Update the appropriate image when necessary. """
        pixbuf = self.gfx.get_decal(int(widget.get_value()), None, True)
        if (pixbuf is None):
            self.get_widget('draw_decal_img').set_from_stock(gtk.STOCK_EDIT, 2)
        else:
            self.get_widget('draw_decal_img').set_from_pixbuf(pixbuf)

    def on_wall_changed(self, widget, do_spin_update=True):
        """ Update the appropriate image when necessary. """
        if do_spin_update:
            self.on_singleval_tile_changed_int(widget)
        (pixbuf, height, offset) = self.gfx.get_object(int(widget.get_value()), None, True, self.map.tree_set)
        if (pixbuf is None):
            self.get_widget('wallimg_image').set_from_stock(gtk.STOCK_EDIT, 2)
        else:
            self.get_widget('wallimg_image').set_from_pixbuf(pixbuf)
        self.update_composite()

    def on_draw_wall_changed(self, widget):
        """ Update the appropriate image when necessary. """
        (pixbuf, height, offset) = self.gfx.get_object(int(widget.get_value()), None, True, self.map.tree_set)
        if (pixbuf is None):
            self.get_widget('draw_wall_img').set_from_stock(gtk.STOCK_EDIT, 2)
        else:
            self.get_widget('draw_wall_img').set_from_pixbuf(pixbuf)

    def on_walldecal_changed(self, widget):
        self.on_singleval_tile_changed_int(widget)
        """ Update the appropriate image when necessary. """
        pixbuf = self.gfx.get_object_decal(int(widget.get_value()), None, True)
        if (pixbuf is None):
            self.get_widget('walldecalimg_image').set_from_stock(gtk.STOCK_EDIT, 2)
        else:
            self.get_widget('walldecalimg_image').set_from_pixbuf(pixbuf)
        self.update_composite()

    def on_draw_walldecal_changed(self, widget):
        """ Update the appropriate image when necessary. """
        pixbuf = self.gfx.get_object_decal(int(widget.get_value()), None, True)
        if (pixbuf is None):
            self.get_widget('draw_walldecal_img').set_from_stock(gtk.STOCK_EDIT, 2)
        else:
            self.get_widget('draw_walldecal_img').set_from_pixbuf(pixbuf)

    def on_tilewindow_close(self, widget, event=None):
        """
        Closes the tile-editing window.  Our primary goal here is to redraw the
        tile that was just edited.  That's all out in its own function though, so
        we're just doing some housekeeping mostly.
        """
        # Populate our undo object with the new tile
        self.undo.finish()

        # All the "fun" stuff ends up happening in here.
        self.redraw_tile(self.tile_x, self.tile_y)
        
        # ... update our GUI stuff for Undo
        self.update_undo_gui()

        # Close out the window
        self.tilewindow.hide()

        # Check for hugegfx changes
        if c.book > 1:
            if self.check_hugegfx_state(self.map.tiles[self.tile_y][self.tile_x]):
                self.draw_map()

        return True

    def redraw_tile(self, x, y):
        """
        Redraw a single tile, and any dependant tiles nearby as well.

        Because we don't really keep composite caches
        around (should we?) this entails drawing all the tiles behind the tile we
        just edited, the tile itself, and then four more "levels" of tiles below, as
        well, because objects may be obscuring the one we just edited.  Because of the
        isometric presentation, this means that we'd be redrawing 29 total tiles,
        assuming that everything fits exactly into our tile width.

        Unfortunately, now that we support entities, some of those are wider than the
        tile width, so we're going to redraw even more than that, for a total of 67
        tiles.

        Note that we could cut down on that number by doing some logic - ie: we really
        would only have to draw the bottom-most tile if it contained the tallest tree
        graphic, and there's no need to draw the floor or floor decals on any tile below
        the one we just edited.  Still, because this is a user-initiated action, I don't
        think it's really worth it to optimize that out.  I don't think the extra processing
        will be noticeable.

        Note that the we-don't-have-to-draw-everything angle becomes even bigger now that
        we're widening the field to support entities.  The outermost 20 tiles that we're
        drawing only have to be drawn if there's an entity in there which is wider than
        the ordinary tile, and even then we'd *only* have to draw the entity (to say nothing
        of the fact that very few of those larger entities actually draw to the full edge of
        the entity graphic for all cases).  Additionally, if the tile we just edited didn't
        contain an entity at any point, we'd be able to lop off a bunch tiles in the first
        place.  Still, I'm guessing that it doesn't really matter much.  Perhaps it'll become
        necessary to do this more intelligently once I've got some actual drawing-type
        functionality in place.

        Also note that absolutely none of this is necessary if the user didn't actually change
        anything.  Whatever.
        """

        # Figure out our dimensions
        tier_1_x = []
        tier_1_y = y - 1 - 8
        tier_2_x = range(x-1, x+2)
        tier_2_y = y - 8
        global_x = (x * self.z_width) - self.z_halfwidth
        if ((y % 2) == 0):
            tier_1_x = range(x-2, x+2)
        else:
            tier_1_x = range(x-1, x+3)
            global_x = global_x + self.z_halfwidth

        # Set up a surface to use
        over_surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.z_width*2, self.z_5xheight)
        over_ctx = cairo.Context(over_surf)
        over_ctx.set_source_rgba(0, 0, 0, 1)
        over_ctx.paint()

        # Grab some local vars
        tiles = self.map.tiles
        huge_gfx_rows = self.huge_gfx_rows
        global_offset_x = global_x+1
        global_offset_y = self.z_halfheight*(y-8)+1

        # Loop through and composite the new image area
        for i in range(10):
            # Draw tier 1 tiles first, then tier 2
            if (tier_1_y > -1 and tier_1_y < 200):
                for (tier_i, tier_x) in enumerate(tier_1_x):
                    yval = self.z_halfheight+((i-5)*self.z_height)
                    if (tier_x > -1 and tier_x < 100):
                        (op_buf, offset) = self.draw_tile(tier_x, tier_1_y, False, False)
                        over_ctx.set_source_surface(op_buf, ((-3+(2*tier_i))*self.z_halfwidth)-offset+self.z_halfwidth, yval)
                        over_ctx.paint()
                # Redraw any "huge" graphics in this row
                if c.book > 1:
                    for gfx_x in huge_gfx_rows[tier_1_y]:
                        self.draw_huge_gfx(tiles[tier_1_y][gfx_x], over_ctx, global_offset_x, global_offset_y)
            if (i < 9):
                if (tier_2_y > -1 and tier_2_y < 200):
                    for (tier_i, tier_x) in enumerate(tier_2_x):
                        if (tier_x > -1 and tier_x < 100):
                            (op_buf, offset) = self.draw_tile(tier_x, tier_2_y, False, False)
                            over_ctx.set_source_surface(op_buf, ((-1+tier_i)*self.z_width)-offset+self.z_halfwidth, (i-4)*self.z_height)
                            over_ctx.paint()
                # Redraw any "huge" graphics in this row
                if c.book > 1:
                    if tier_2_y < 200:
                        for gfx_x in huge_gfx_rows[tier_2_y]:
                            self.draw_huge_gfx(tiles[tier_2_y][gfx_x], over_ctx, global_offset_x, global_offset_y)
            tier_1_y = tier_1_y + 2
            tier_2_y = tier_2_y + 2

        # This is a bit overkill, but easier than trying to figure out how far up any
        # big graphics go.
        for yval in range(tier_1_y-1, 200):
            for gfx_x in huge_gfx_rows[yval]:
                self.draw_huge_gfx(tiles[yval][gfx_x], over_ctx, global_offset_x, global_offset_y)

        # Now superimpose that onto our main map image
        self.guicache_ctx.set_source_surface(over_surf, global_offset_x, global_offset_y)
        self.guicache_ctx.paint()
        self.ctx.set_source_surface(over_surf, global_offset_x, global_offset_y)
        self.ctx.paint()
        self.cleantiles.append((x, y))
        self.maparea.queue_draw()

        return True

    def format_zoomlevel(self, widget, value):
        """ Formats the zoom slider scale. """
        return 'Lvl %d' % (value+1)

    def set_zoom_vars(self, scalenum):
        """
        Set a bunch of parameters we use to draw, based on how wide our tiles should be.
        This also incidentally sets the sensitivity flag on our zoom buttons.
        """
        width = self.zoom_levels[scalenum]
        self.curzoomidx = scalenum
        self.curzoom = width
        self.z_width = width
        self.z_height = int(self.z_width/2)
        self.z_halfwidth = self.z_height
        self.z_halfheight = int(self.z_height/2)
        self.z_mapsize_x = self.z_width*101
        self.z_mapsize_y = int(self.z_mapsize_x/2)

        # These vars help speed up tile drawing
        self.z_2xheight = self.z_height*2
        self.z_3xheight = self.z_height*3
        self.z_4xheight = self.z_height*4
        self.z_5xheight = self.z_height*5

        # Our tilebuf size (the one we draw tiles onto) may vary based on book
        self.z_tilebuf_w = int(self.z_width * self.gfx.tilebuf_mult)
        self.z_tilebuf_offset = int((self.z_tilebuf_w - self.z_width)/2)

        # Clean up our zoom icons
        if (scalenum == 0):
            self.zoom_out_button.set_sensitive(False)
        else:
            self.zoom_out_button.set_sensitive(True)
        if (scalenum == len(self.zoom_levels)-1):
            self.zoom_in_button.set_sensitive(False)
        else:
            self.zoom_in_button.set_sensitive(True)

    def scroll_h_changed(self, widget):
        """ Handle what to do when our scollwindow detects a change in dimensions. """
        if (self.prev_scroll_h_cur != -1):
            newval = int((self.prev_scroll_h_cur*widget.upper)/self.prev_scroll_h_max)
            if (widget.upper >= (newval + widget.page_size)):
                widget.set_value(newval)
        self.prev_scroll_h_max = widget.upper

    def scroll_v_changed(self, widget):
        """ Handle what to do when our scollwindow detects a change in dimensions. """
        if (self.prev_scroll_v_cur != -1):
            newval = int((self.prev_scroll_v_cur*widget.upper)/self.prev_scroll_v_max)
            if (widget.upper >= (newval + widget.page_size)):
                widget.set_value(newval)
        self.prev_scroll_v_max = widget.upper

    def zoom_to(self, level):
        """ Take care of everything that needs to be done when we change zoom levels. """
        hadjust = self.mainscroll.get_hadjustment()
        vadjust = self.mainscroll.get_vadjustment()
        self.prev_scroll_h_cur = (hadjust.page_size/4)+hadjust.value
        self.prev_scroll_v_cur = (vadjust.page_size/4)+vadjust.value
        self.set_zoom_vars(level)
        self.draw_map()

    def zoom_slider(self, widget):
        """ Handle a zoom from the slider. """
        newzoom = int(widget.get_value())
        if (newzoom < 0):
            newzoom = 0
        if (newzoom > len(self.zoom_levels)-1):
            newzoom = len(self.zoom_levels)-1
        if (newzoom != self.curzoomidx):
            self.zoom_to(newzoom)

    def zoom_out(self, widget):
        """ Handle a zoom-out. """
        if (self.curzoomidx != 0):
            self.zoom_scale.set_value(self.curzoomidx-1)

    def zoom_in(self, widget):
        """ Handle a zoom-in. """
        if (self.curzoomidx != (len(self.zoom_levels)-1)):
            self.zoom_scale.set_value(self.curzoomidx+1)

    def on_mouse_changed(self, widget, event):
        """ Keep track of where the mouse is """

        if (self.dragging):
            if sys.platform != 'win32' and gtk.events_pending():
                # A default Fedora 13 install on my old development
                # machine performs horribly slowly on click-and-drag
                # for some reason.  This is a pretty simple way to
                # let the program remain responsive, which doesn't
                # seem to create problems.  For more info, see:
                # http://forums.fedoraforum.org/showthread.php?t=250036
                return
            diff_x = self.hold_x - event.x_root
            diff_y = self.hold_y - event.y_root
            if (diff_x != 0):
                adjust = self.mainscroll.get_hadjustment()
                newvalue = adjust.get_value() + diff_x
                if (newvalue < adjust.lower):
                    newvalue = adjust.lower
                elif (newvalue > adjust.upper-adjust.page_size):
                    newvalue = adjust.upper-adjust.page_size
                adjust.set_value(newvalue)
            if (diff_y != 0):
                adjust = self.mainscroll.get_vadjustment()
                newvalue = adjust.get_value() + diff_y
                if (newvalue < adjust.lower):
                    newvalue = adjust.lower
                elif (newvalue > adjust.upper-adjust.page_size):
                    newvalue = adjust.upper-adjust.page_size
                adjust.set_value(newvalue)
            self.hold_x = event.x_root
            self.hold_y = event.y_root
            return

        # What x/y values we start with
        start_x = int(event.x/self.z_width)
        start_y = int(event.y/self.z_height)

        # Value to check inside our imagemap
        test_x = int(event.x - (start_x * self.z_width))
        test_y = int(event.y - (start_y * self.z_height))

        # We need to modify the y value before we actually process, though
        start_y = start_y * 2

        # ... and now figure out our coordinates based on the map
        # I tried out using a dict lookup instead of the series of if/then, but
        # the if/then ended up being about 40% faster or so.
        testval = self.mousemap[self.curzoom][test_y][test_x][0]
        if (testval == 50):
            self.tile_x = start_x-1
            self.tile_y = start_y-1
        elif (testval == 100):
            self.tile_x = start_x
            self.tile_y = start_y-1
        elif (testval == 150):
            self.tile_x = start_x
            self.tile_y = start_y+1
        elif (testval == 200):
            self.tile_x = start_x-1
            self.tile_y = start_y+1
        else:
            self.tile_x = start_x
            self.tile_y = start_y

        # Some sanity checks
        if (self.tile_x < 0):
            self.tile_x = 0
        elif (self.tile_x > 99):
            self.tile_x = 99
        if (self.tile_y < 0):
            self.tile_y = 0
        elif (self.tile_y > 199):
            self.tile_y = 199

        # See if we've changed, and queue some redraws if so
        if (self.tile_x != self.tile_x_prev or self.tile_y != self.tile_y_prev):
            # It's possible we cause duplication here, but it the CPU cost should be negligible
            # It's also important to append the previous value FIRST, so that our graphic clean-up
            # doesn't clobber a freshly-drawn mouse pointer
            if (self.tile_x_prev != -1):
                self.cleantiles.append((self.tile_x_prev, self.tile_y_prev))
                # We should just really check for over-wide entities here, but for now we'll
                # just do some excessive redrawing.
                if (self.map.tiles[self.tile_y_prev][self.tile_x_prev].entity is not None):
                    if (self.tile_x_prev != 0):
                        self.cleantiles.append((self.tile_x_prev-1, self.tile_y_prev))
                    if (self.tile_x_prev != 99):
                        self.cleantiles.append((self.tile_x_prev+1, self.tile_y_prev))
            self.cleantiles.append((self.tile_x, self.tile_y))
            self.tile_x_prev = self.tile_x
            self.tile_y_prev = self.tile_y

            # Draw if we're supposed to
            if (self.drawing):
                self.action_draw_tile(self.tile_x, self.tile_y)
            elif (self.erasing):
                self.action_erase_tile(self.tile_x, self.tile_y)

        self.coords_label.set_markup('<i>(%d, %d)</i>' % (self.tile_x, self.tile_y))

        # Now queue up a draw
        self.maparea.queue_draw()

    def set_entity_toggle_button(self, show_add):
        if (show_add):
            image = gtk.STOCK_ADD
            text = 'Add Entity'
            self.get_widget('entity_scroll').hide()
        else:
            image = gtk.STOCK_REMOVE
            text = 'Remove Entity'
            self.get_widget('entity_scroll').show()
            if (self.map.is_savegame()):
                self.get_widget('entity_extra_box').show()
                if c.book > 1:
                    self.get_widget('entity_status_box').show()
            else:
                self.get_widget('entity_extra_box').hide()
                if c.book > 1:
                    self.get_widget('entity_status_box').hide()
        self.get_widget('entity_toggle_img').set_from_stock(image, 4)
        self.get_widget('entity_toggle_text').set_text(text)

    def input_label(self, table, row, name, text):
        label = gtk.Label()
        label.show()
        label.set_markup('%s:' % text)
        label.set_alignment(1, 0.5)
        label.set_justify(gtk.JUSTIFY_RIGHT)
        label.set_padding(5, 4)
        self.register_widget('%s_label' % (name), label)
        table.attach(label, 0, 1, row, row+1, gtk.FILL, gtk.FILL)
        return label

    def tilecontent_input_label(self, page, table, row, name, text):
        self.input_label(table, row, '%s_%d' % (name, page), text)

    def input_text(self, table, row, name, text, tooltip=None, signal=None, width=None, hbox=False):
        self.input_label(table, row, name, text)
        align = gtk.Alignment(0, 0.5, 1, 1)
        align.set_padding(0, 0, 0, 8)
        align.show()
        entry = gtk.Entry()
        entry.show()
        self.register_widget(name, entry)
        if width is not None:
            entry.set_size_request(width, -1)
        if signal is not None:
            entry.connect('changed', signal)
        if (tooltip is not None):
            entry.set_tooltip_text(tooltip)
        if hbox:
            hbox = gtk.HBox()
            hbox.pack_start(entry, True, True)
            hbox.show()
            align.add(hbox)
        else:
            align.add(entry)
        table.attach(align, 1, 2, row, row+1)
        return entry

    def tilecontent_input_text(self, page, table, row, name, text, tooltip=None, hbox=False):
        varname = '%s_%d' % (name, page)
        entry = self.input_text(table, row, varname, text, tooltip, self.on_tilecontent_str_changed, 250, hbox)
        tilecontent = self.map.tiles[self.tile_y][self.tile_x].tilecontents[page]
        if (tilecontent is not None):
            if (name[:9] == 'item_name'):
                (varname, itemnum) = name.rsplit('_', 1)
                itemnum = int(itemnum)
                entry.set_text(tilecontent.items[itemnum].item_name)
            else:
                entry.set_text(tilecontent.__dict__[name])
        return entry

    def prop_unknown_input_text(self, table, num, row, tooltip=None):
        varname = 'map_unknownstr%d' % (num)
        text = '<i>Unknown String %d</i>' % (num)
        return self.input_text(table, row, varname, text, tooltip, self.on_singleval_map_changed_str)

    def input_spin(self, table, row, name, text, max, tooltip=None, signal=None):
        self.input_label(table, row, name, text)
        align = gtk.Alignment(0, 0.5, 0, 1)
        align.show()
        entry = gtk.SpinButton()
        entry.show()
        self.register_widget(name, entry)
        entry.set_range(0, max)
        entry.set_adjustment(gtk.Adjustment(0, 0, max, 1, 10, 0))
        if (signal is not None):
            entry.connect('value-changed', signal)
        if (tooltip is not None):
            entry.set_tooltip_text(tooltip)
        align.add(entry)
        table.attach(align, 1, 2, row, row+1)
        return entry

    def input_uchar(self, table, row, name, text, tooltip=None, signal=None):
        return self.input_spin(table, row, name, text, 0xFF, tooltip, signal)

    def input_short(self, table, row, name, text, tooltip=None, signal=None):
        return self.input_spin(table, row, name, text, 0xFFFF, tooltip, signal)

    def input_int(self, table, row, name, text, tooltip=None, signal=None):
        return self.input_spin(table, row, name, text, 0xFFFFFFFF, tooltip, signal)

    def tilecontent_input_spin(self, func, page, table, row, name, text, tooltip=None, signal=None):
        varname = '%s_%d' % (name, page)
        if signal is None:
            signal = self.on_tilecontent_int_changed
        entry = func(table, row, varname, text, tooltip, signal)
        tilecontent = self.map.tiles[self.tile_y][self.tile_x].tilecontents[page]
        if (tilecontent is not None):
            entry.set_value(tilecontent.__dict__[name])

    def prop_unknown_input_spin(self, func, type, table, num, row, tooltip=None, signal=None, prefix=''):
        textdict = {
                'i': 'Int',
                'c': 'Char',
                }
        if prefix != '':
            prefix = '%s_' % (prefix)
        varname = 'map_%sunknown%s%d' % (prefix, type, num)
        text = '<i>Unknown %s %d</i>' % (textdict.get(type, '?'), num)
        if signal is None:
            signal = self.on_singleval_map_changed_int
        entry = func(table, row, varname, text, tooltip, signal)

    def tilecontent_input_dropdown(self, page, table, row, name, text, values, tooltip=None, signal=None):
        self.input_label(table, row, '%s_%d' % (name, page), text)
        align = gtk.Alignment(0, 0.5, 0, 1)
        align.show()
        entry = gtk.combo_box_new_text()
        entry.show()
        entry.set_name('%s_%d' % (name, page))
        for value in values:
            entry.append_text(value)
        tilecontent = self.map.tiles[self.tile_y][self.tile_x].tilecontents[page]
        if (tilecontent is not None):
            entry.set_active(tilecontent.__dict__[name])
        if (signal is not None):
            entry.connect('changed', signal)
        else:
            entry.connect('changed', self.on_dropdown_changed)
        if (tooltip is not None):
            entry.set_tooltip_text(tooltip)
        align.add(entry)
        table.attach(align, 1, 2, row, row+1)

    def tilecontent_input_flag(self, page, table, row, name, flagval, text, tooltip=None):
        self.input_label(table, row, '%s_%d' % (name, page), text)
        align = gtk.Alignment(0, 0.5, 0, 1)
        align.show()
        entry = gtk.CheckButton()
        entry.show()
        entry.set_name('%s_%X_%d' % (name, flagval, page))
        tilecontentval = self.map.tiles[self.tile_y][self.tile_x].tilecontents[page].__dict__[name]
        entry.set_active((tilecontentval & flagval == flagval))
        entry.connect('toggled', self.on_tilecontent_flag_changed)
        if (tooltip is not None):
            entry.set_tooltip_text(tooltip)
        align.add(entry)
        table.attach(align, 1, 2, row, row+1)

    def on_flag_changed(self, name, flagval_str, widget, object):
        """
        What to do whan a bit field changes.  Currently just the
        destructible flag.
        """
        flagval = int(flagval_str, 16)
        if (object is not None):
            if (widget.get_active()):
                object.__dict__[name] = object.__dict__[name] | flagval
            else:
                object.__dict__[name] = object.__dict__[name] & ~flagval

    def on_map_flag_changed(self, widget):
        """
        What to do whan a bit field changes.
        """
        wname = widget.get_name()
        (name, flagval) = wname.rsplit('_', 1)
        self.on_flag_changed(name, flagval, widget, self.map)

    def on_tilecontent_flag_changed(self, widget):
        """
        What to do whan a bit field changes.  Currently just the
        destructible flag.
        """
        wname = widget.get_name()
        (name, flagval, page) = wname.rsplit('_', 2)
        page = int(page)
        tilecontent = self.map.tiles[self.tile_y][self.tile_x].tilecontents[page]
        self.on_flag_changed(name, flagval, widget, tilecontent)

    def on_barrier_changed(self, widget):
        """
        What to do when our barrier dropdown is changed.
        """
        model = widget.get_model()
        self.map.tiles[self.tile_y][self.tile_x].wall = model[widget.get_active()][1]

    def populate_mapitem_button(self, num, page):
        widget = self.get_widget('item_%d_%d_text' % (num, page))
        imgwidget = self.get_widget('item_%d_%d_image' % (num, page))
        item = self.map.tiles[self.tile_y][self.tile_x].tilecontents[page].items[num]
        self.populate_item_button(item, widget, imgwidget, self.get_widget('itemtable_%d' % (page)))

    def on_tilecontent_dropdown_changed(self, widget):
        """ Handle the trap dropdown change. """
        wname = widget.get_name()
        (varname, page) = wname.rsplit('_', 2)
        page = int(page)
        tilecontent = self.map.tiles[self.tile_y][self.tile_x].tilecontents[page]
        tilecontent.__dict__[varname] = widget.get_active()

    def on_mapitem_clicked(self, widget, doshow=True):
        """ What to do when our item button is clicked. """
        wname = widget.get_name()
        (varname, num, page, button) = wname.rsplit('_', 3)
        num = int(num)
        page = int(page)
        self.curitem = (num, page)
        self.populate_itemform_from_item(self.map.tiles[self.tile_y][self.tile_x].tilecontents[page].items[num])
        self.get_widget('item_notebook').set_current_page(0)
        if (doshow):
            self.itemwindow.show()

    def register_mapitem_change(self, num, page):
        """
        When loading in a new item, redraw the button and make sure that changes
        are entered into the system properly.
        """
        self.on_mapitem_clicked(self.get_widget('item_%d_%d_button' % (num, page)), False)
        self.on_item_close_clicked(None, False)

    def on_mapitem_action_clicked(self, widget):
        """ What to do when we cut/copy/paste/delete an item. """
        wname = widget.get_name()
        (varname, num, page, action) = wname.rsplit('_', 3)
        num = int(num)
        page = int(page)
        items = self.map.tiles[self.tile_y][self.tile_x].tilecontents[page].items
        if (action == 'cut'):
            self.on_mapitem_action_clicked(self.get_widget('item_%d_%d_copy' % (num, page)))
            self.on_mapitem_action_clicked(self.get_widget('item_%d_%d_delete' % (num, page)))
        elif (action == 'copy'):
            self.itemclipboard = items[num]
        elif (action == 'paste'):
            if (self.itemclipboard != None):
                items[num] = self.itemclipboard.replicate()
                self.register_mapitem_change(num, page)
        elif (action == 'delete'):
            items[num] = Item.new(c.book, True)
            items[num].tozero()
            self.register_mapitem_change(num, page)
        else:
            raise Exception('invalid action')

    def tilecontent_group_box(self, markup):
        box = gtk.VBox()
        box.show()
        header = gtk.Label()
        header.show()
        header.set_markup(markup)
        header.set_alignment(0, 0.5)
        header.set_padding(10, 7)
        box.pack_start(header, False, False)
        return box

    def append_tilecontent_notebook(self, tilecontent):
        """
        Given a tilecontent, adds a new tab to the tilecontent notebook, with
        all the necessary inputs.
        """
        tile = self.map.tiles[self.tile_y][self.tile_x]
        curpages = self.tilecontent_notebook.get_n_pages()

        # Label for the notebook
        label = gtk.Label('Object #%d' % (curpages+1))
        label.show()

        # Remove Button
        remove_align = gtk.Alignment(0, 0.5, 0, 1)
        remove_align.show()
        remove_align.set_border_width(8)
        remove_button = gtk.Button()
        remove_button.show()
        remove_button.set_name('tilecontent_remove_button_%d' % (curpages))
        remove_button.connect('clicked', self.on_tilecontent_del)
        remove_button_box = gtk.HBox()
        remove_button_box.show()
        rm_img = gtk.image_new_from_stock(gtk.STOCK_REMOVE, 4)
        rm_img.show()
        remove_button_box.add(rm_img)
        rm_txt = gtk.Label('Remove Object')
        rm_txt.show()
        rm_txt.set_padding(6, 0)
        remove_button_box.add(rm_txt)
        remove_button.add(remove_button_box)
        remove_align.add(remove_button)

        # Basic Information
        basic_box = self.tilecontent_group_box('<b>Basic Information</b>')
        binput = gtk.Table(10, 2)
        binput.show()

        align = gtk.Alignment(.5, .5, 1, 1)
        align.set_padding(0, 0, 11, 0)
        align.add(binput)
        align.show()
        basic_box.pack_start(align, False, False)

        # Basic Inputs
        self.tilecontent_input_text(curpages, binput, 0, 'description', '(to update)',
                '(to update)')
        self.tilecontent_input_text(curpages, binput, 1, 'extratext', '(to update)',
                '(to update)')
        entry = self.tilecontent_input_text(curpages, binput, 2, 'script', 'Script', None, True)

        # Script editor launcher
        hbox = entry.get_property('parent')
        self.setup_script_editor_launcher(hbox, entry, self.tilewindow, True)

        # We special-case this to handle the weirdly-trapped door at (25, 26) in outpost
        if (tile.tilecontents[curpages].trap in c.traptable.keys()):
            self.tilecontent_input_dropdown(curpages, binput, 4, 'trap', 'Trap', c.traptable.values(), None, self.on_tilecontent_dropdown_changed)
        else:
            self.tilecontent_input_spin(self.input_uchar, curpages, binput, 4, 'trap', 'Trap', 'The trap value should be between 0 and 8 ordinarily.  The  current trap is undefined.')

        # We special-case this just in case
        if (tile.tilecontents[curpages].state in c.containertable.keys()):
            self.tilecontent_input_dropdown(curpages, binput, 5, 'state', "State\n<i><small>(if container, door, or switch)</small></i>", c.containertable.values(), None, self.on_tilecontent_dropdown_changed)
        else:
            self.tilecontent_input_spin(self.input_uchar, curpages, binput, 5, 'state', 'State', 'The state value should be between 0 and 5 ordinarily.  The current container state is undefined.')

        # Note that row 6 is lock level, but we're skipping it right here

        if c.book == 1:
            # Book 1-specific values
            self.tilecontent_input_spin(self.input_uchar, curpages, binput, 7, 'other', 'Other', 'When the Lock Level is set to 99, this is the combination of the safe.  Otherwise, it appears to be a value from 0 to 3.')

            # If we ever get more flags, this'll have to change
            if (tile.tilecontents[curpages].flags & ~0x40 == 0):
                self.tilecontent_input_flag(curpages, binput, 8, 'flags', 0x40, 'Destructible')
            else:
                self.tilecontent_input_spin(self.input_short, curpages, binput, 8, 'flags', 'Flags', 'Ordinarily this is a bit field, but the only value that I\'ve ever seen is "64" which denotes destructible.  Since this value is different, it\'s being shown here as an integer.')

            self.tilecontent_input_spin(self.input_uchar, curpages, binput, 9, 'sturdiness', 'Sturdiness', '89 is the typical value for most objects.  Lower numbers are more flimsy.')
        else:
            # Book 2-specific values
            self.tilecontent_input_spin(self.input_short, curpages, binput, 7, 'slider_loot', 'Slider/Lootlevel', 'If the container has a slider lock, this is the combination.  If not, it\'s the relative loot level (0 being appropriate to your class, 10 being the highest in-game)')
            self.tilecontent_input_spin(self.input_uchar, curpages, binput, 8, 'on_empty', 'On-Empty', 'Typically 0 for permanent containers, 1 for bags.  There are a couple of exceptions')

            # Condition is special, we're using an hbox here
            scr = self.map.tiles[self.tile_y][self.tile_x].tilecontents[curpages]
            self.tilecontent_input_label(curpages, binput, 9, 'cur_condition', 'Condition')
            hbox = gtk.HBox()
            curentry = gtk.SpinButton()
            self.register_widget('cur_condition_%d' % (curpages), curentry)
            curentry.set_range(0, 0xFFFFFFFF)
            curentry.set_adjustment(gtk.Adjustment(0, 0, 0xFFFFFFFF, 1, 10, 0))
            maxlabel = gtk.Label('out of:')
            self.register_widget('max_condition_%d_label' % (curpages), maxlabel)
            maxentry = gtk.SpinButton()
            self.register_widget('max_condition_%d' % (curpages), maxentry)
            maxentry.set_range(0, 0xFFFFFFFF)
            maxentry.set_adjustment(gtk.Adjustment(0, 0, 0xFFFFFFFF, 1, 10, 0))
            hbox.add(curentry)
            hbox.add(maxlabel)
            hbox.add(maxentry)
            if (tilecontent is not None):
                curentry.set_value(scr.cur_condition)
                maxentry.set_value(scr.max_condition)
            curentry.connect('value-changed', self.on_tilecontent_int_changed)
            maxentry.connect('value-changed', self.on_tilecontent_int_changed)
            align = gtk.Alignment(0, 0.5, 0, 1)
            align.add(hbox)
            align.show_all()
            binput.attach(align, 1, 2, 9, 10)

        # Lock Level, done here so that our signal doesn't get called before sliderloot is available,
        # in book 2
        if c.book == 1:
            locktip = 'Zero is unlocked, 1 is the easiest lock, 60 is the highest in the game, and 99 denotes a slider lock'
        else:
            locktip = 'Zero is unlocked, 1 is the easiest lock, 10 is the highest in the game, and 12 denotes a slider lock'
        self.tilecontent_input_spin(self.input_uchar, curpages, binput, 6, 'lock', 'Lock Level', locktip, self.on_locklevel_changed)

        # Contents
        contents_box = self.tilecontent_group_box('<b>Contents</b> <i>(If Container)</i>')
        cinput = gtk.Table(8, 3)
        self.register_widget('itemtable_%d' % (curpages), cinput, True)
        cinput.show()
        cspacer = gtk.Label('')
        cspacer.show()
        cspacer.set_padding(11, 0)
        cinput.attach(cspacer, 0, 1, 0, 8, gtk.FILL, gtk.FILL|gtk.EXPAND)
        contents_box.pack_start(cinput, False, False)

        # Contents Inputs (varies based on savefile status)
        if (tile.tilecontents[curpages].savegame):
            for num in range(8):
                self.tilecontent_input_label(curpages, cinput, num, 'item_%d' % (num), 'Item %d' % (num+1))
                cinput.attach(self.gui_item('item_%d_%d' % (num, curpages), self.on_mapitem_clicked, self.on_mapitem_action_clicked),
                        2, 3, num, num+1, gtk.FILL|gtk.EXPAND, gtk.FILL|gtk.EXPAND)
                self.populate_mapitem_button(num, curpages)
        else:
            for num in range(8):
                self.tilecontent_input_text(curpages, cinput, num, 'item_name_%d' % (num), 'Item %d' % (num+1))

        # Unknowns
        unknown_box = self.tilecontent_group_box('<b>Unknowns</b>')
        uinput = gtk.Table(5, 3)
        uinput.show()
        spacer = gtk.Label('')
        spacer.show()
        spacer.set_padding(11, 0)
        uinput.attach(spacer, 0, 1, 0, 5, gtk.FILL, gtk.FILL|gtk.EXPAND)
        unknown_box.pack_start(uinput, False, False)

        # Data in Unknowns block
        if c.book == 1:
            self.tilecontent_input_spin(self.input_short, curpages, uinput, 0, 'unknownh3', '<i>Unknown</i>')
            self.tilecontent_input_spin(self.input_short, curpages, uinput, 1, 'zeroh1', '<i>Usually Zero 1</i>')
            self.tilecontent_input_spin(self.input_int, curpages, uinput, 2, 'zeroi1', '<i>Usually Zero 2</i>')
            self.tilecontent_input_spin(self.input_int, curpages, uinput, 3, 'zeroi2', '<i>Usually Zero 3</i>')
            self.tilecontent_input_spin(self.input_int, curpages, uinput, 4, 'zeroi3', '<i>Usually Zero 4</i>')

        # Tab Content
        content = gtk.VBox()
        content.show()
        content.pack_start(remove_align, False, False)
        content.pack_start(basic_box, False, False)
        content.pack_start(contents_box, False, False)
        content.pack_start(unknown_box, False, False)

        # ... aand we should slap this all into a scrolledwindow
        sw = gtk.ScrolledWindow()
        sw.show()
        sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        vp = gtk.Viewport()
        vp.show()
        vp.set_shadow_type(gtk.SHADOW_NONE)
        vp.add(content)
        sw.add(vp)

        # Update our text labels and tooltips appropriately
        # for tilecontentid type 6
        self.update_tilecontent_type_strings(curpages, tile.tilecontentid)

        # ... and update our "other" label
        self.on_locklevel_changed(self.get_widget('lock_%d' % (curpages)))

        self.tilecontent_notebook.append_page(sw, label)

    def clear_tilecontent_notebook(self):
        """ Clears out the tilecontent notebook. """
        for i in range(self.tilecontent_notebook.get_n_pages()):
            self.tilecontent_notebook.remove_page(0)

    def on_tilecontent_del(self, widget):
        """
        Called to remove a tilecontent.  This needs to handle renumbering the
        remaining tilecontents if necessary, too.
        """
        wname = widget.get_name()
        (button_name, page) = wname.rsplit('_', 1)
        page = int(page)
        tile = self.map.tiles[self.tile_y][self.tile_x]

        # We'll have to remove this regardless, so do it now.
        self.map.deltilecontent(self.tile_x, self.tile_y, page)
        self.tilecontent_notebook.remove_page(page)

        # If we didn't just lop off the last one, redraw the whole notebook.
        # This is in theory more lame than renumbering stuff, but to accurately
        # renumber everything, we'd have to change the names of all the widgets
        # in there.  Which would be even more lame.
        if (page < len(tile.tilecontents)):
            self.clear_tilecontent_notebook()
            for tilecontent in self.map.tiles[self.tile_y][self.tile_x].tilecontents:
                self.append_tilecontent_notebook(tilecontent)

        # ... and possibly clean out our note
        self.update_object_note()

    def on_tilecontent_add(self, widget):
        """
        Called when a new tilecontent is added.  Creates a new
        Script object and handles adding it to the notebook.
        """
        tile = self.map.tiles[self.tile_y][self.tile_x]
        tilecontent = Tilecontent.new(c.book, self.map.is_savegame())
        tilecontent.tozero(self.tile_x, self.tile_y)
        self.map.tilecontents.append(tilecontent)
        tile.addtilecontent(tilecontent)
        self.append_tilecontent_notebook(tilecontent)
        self.tilecontent_notebook.show()
        self.update_object_note()

    def on_healthmaxbutton_clicked(self, widget):
        """ Set the entity's health to its maximum. """
        entid = self.map.tiles[self.tile_y][self.tile_x].entity.entid
        if (entid in c.entitytable):
            health = c.entitytable[entid].health
            self.get_widget('health').set_value(health)

    def on_setinitial_clicked(self, widget):
        """ Set the entity's "initial" location to the current (x,y) """
        ent = self.map.tiles[self.tile_y][self.tile_x].entity
        ent.set_initial(self.tile_x, self.tile_y)
        self.get_widget('initial_loc').set_value(ent.initial_loc)

    def on_entity_toggle(self, widget):
        tile = self.map.tiles[self.tile_y][self.tile_x]
        if (tile.entity is None):
            # create a new entity and toggle
            ent = Entity.new(c.book, self.map.is_savegame())
            ent.tozero(self.tile_x, self.tile_y)
            self.map.entities.append(ent)
            tile.addentity(ent)
            self.populate_entity_tab(tile)
            self.set_entity_toggle_button(False)
            # Also trigger on_entid_changed, to prepopulate
            # what information we can.
            self.on_entid_changed(self.get_widget('entid'))
        else:
            # Remove the existing entity
            self.map.delentity(self.tile_x, self.tile_y)
            self.set_entity_toggle_button(True)

    def update_tilecontent_type_strings(self, page, tilecontentid):
        """
        Update the text for tilecontents on a single page, given the
        tilecontentid passed-in.
        """
        text_1 = self.get_widget('description_%d_label' % page)
        text_2 = self.get_widget('extratext_%d_label' % page)
        obj_1 = self.get_widget('description_%d' % page)
        obj_2 = self.get_widget('extratext_%d' % page)
        if (c.book == 1 and tilecontentid == 6):
            text_1.set_text('Map Link')
            text_2.set_text('Map Coordinates')
            obj_1.set_tooltip_text('Name of the map to send the player to.')
            obj_2.set_tooltip_text('The coordinates within the map specified above.  '
                'The coordinate "(56, 129)" would be written "12956"')
        else:
            text_1.set_text('Description')
            text_2.set_text('Extra Text')
            obj_1.set_tooltip_text('A basic description of the tile.')
            obj_2.set_tooltip_text('More descriptive text (such as on signs or gravestones).')

    def update_all_tilecontentid_type_strings(self, tile):
        """ Update the form text for all tilecontents on a tile. """
        for idx in range(self.tilecontent_notebook.get_n_pages()):
            self.update_tilecontent_type_strings(idx, tile.tilecontentid)

    def on_tilecontentid_changed(self, widget):
        """ Process changing our object/tilecontent ID. """
        self.on_singleval_tile_changed_int(widget)
        tile = self.map.tiles[self.tile_y][self.tile_x]
        self.update_all_tilecontentid_type_strings(tile)
        self.update_object_note()

    def on_tilecontentid_dd_changed(self, widget):
        """ Process changing our object/tilecontent type dropdown. """
        tile = self.map.tiles[self.tile_y][self.tile_x]
        tile.tilecontentid = self.object_type_list_rev[widget.get_active()]
        self.update_all_tilecontentid_type_strings(tile)
        self.update_object_note()

    def populate_tilewindow_from_tile(self, tile):
        """ Populates the tile editing screen from a given tile. """

        # Make sure we start out on the right page
        self.get_widget('tile_notebook').set_current_page(0)

        # First the main items.  Wall stuff first.
        if tile.wall in self.wallvals:
            self.get_widget('wall_label').hide()
            self.get_widget('wall').hide()
            self.get_widget('barrier_label').show()
            self.get_widget('barrier').show()
            model = self.get_widget('barrier').get_model()
            for (idx, row) in enumerate(model):
                if (row[1] == tile.wall):
                    self.get_widget('barrier').set_active(idx)
                    break
        else:
            self.get_widget('barrier_label').hide()
            self.get_widget('barrier').hide()
            self.get_widget('wall_label').show()
            self.get_widget('wall').show()
            self.get_widget('wall').set_value(tile.wall)

        # ... and now the rest
        self.get_widget('floorimg').set_value(tile.floorimg)
        self.get_widget('decalimg').set_value(tile.decalimg)
        self.get_widget('wallimg').set_value(tile.wallimg)
        self.get_widget('walldecalimg').set_value(tile.walldecalimg)
        if c.book == 1:
            self.get_widget('unknown5').set_value(tile.unknown5)
        else:
            self.get_widget('tile_flag').set_value(tile.tile_flag)
            if c.book == 3:
                self.get_widget('cartography').set_value(tile.cartography)

        # Now entites, if needed
        if (tile.entity is None):
            self.set_entity_toggle_button(True)
        else:
            self.set_entity_toggle_button(False)
            self.populate_entity_tab(tile)

        # ... and tilecontents (first the ID)
        if (tile.tilecontentid in c.tilecontenttypetable):
            self.get_widget('tilecontentid_num_align').hide()
            self.get_widget('tilecontentid_dd_align').show()
            self.get_widget('tilecontentid_dd').set_active(self.object_type_list[tile.tilecontentid])
        else:
            self.get_widget('tilecontentid_num_align').show()
            self.get_widget('tilecontentid_dd_align').hide()
            self.get_widget('tilecontentid').set_value(tile.tilecontentid)

        # ... now the tilecontents themselves.
        self.clear_tilecontent_notebook()
        if (len(tile.tilecontents) > 0):
            self.get_widget('tilecontent_add_button').hide()
            for tilecontent in tile.tilecontents:
                self.append_tilecontent_notebook(tilecontent)
            self.tilecontent_notebook.show()
        else:
            self.get_widget('tilecontent_add_button').show()
            self.tilecontent_notebook.hide()

    def populate_entity_tab(self, tile):
        """ Populates the entity tab of the tile editing screen. """
        self.populating_entity_tab = True
        if (tile.entity.entid in c.entitytable):
            if (c.entitytable[tile.entity.entid].name in self.entitykeys):
                idx = self.entitykeys.index(c.entitytable[tile.entity.entid].name)
                self.get_widget('entid').set_active(idx)
            else:
                self.errordialog('Entity Error', 'The application encountered an entity '
                        'type that we don\'t know anything about.  The values on the entity '
                        'tab may not be accurate', self.tilewindow)
                self.get_widget('entid').set_active(0)
        else:
            self.errordialog('Entity Error', 'The application encountered an entity '
                    'type that we don\'t know anything about.  The values on the entity '
                    'tab may not be accurate', self.tilewindow)
            self.get_widget('entid').set_active(0)
        self.populating_entity_tab = False
        self.get_widget('direction').set_active(tile.entity.direction-1)
        self.get_widget('entscript').set_text(tile.entity.entscript)
        if (self.map.is_savegame()):
            self.get_widget('friendly').set_value(tile.entity.friendly)
            self.get_widget('health').set_value(tile.entity.health)
            self.get_widget('frame').set_value(tile.entity.frame)
            self.get_widget('initial_loc').set_value(tile.entity.initial_loc)
            self.get_widget('movement').set_value(tile.entity.movement)
            if c.book > 1:
                for (idx, val) in enumerate(tile.entity.statuses):
                    self.get_widget('ent_status_%d' % (idx)).set_value(val)
            self.get_widget('entity_scroll').get_vadjustment().set_value(0)

    def update_object_note(self):
        """
        Updates our object note, to let the user know if there should
        be an object or not.  Also shows or hides the "Add Object" button
        as needed.
        """
        tile = self.map.tiles[self.tile_y][self.tile_x]
        note = self.get_widget('object_note')

        # First the button
        if (len(tile.tilecontents) > 0):
            self.get_widget('tilecontent_add_button').hide()
        else:
            self.get_widget('tilecontent_add_button').show()

        # Now the actual note
        if (len(tile.tilecontents) > 1):
            note.set_markup('<b>Warning:</b> There are three instances in the master map files where more than one object is defined for a tile, but doing so is discouraged.  Only one of the objects will actually be used by the game engine.')
            note.show()
        elif c.book == 1:
            if (tile.tilecontentid > 0 and tile.tilecontentid < 25):
                if (len(tile.tilecontents) > 0):
                    note.hide()
                else:
                    note.set_markup('<b>Note:</b> Given the object type specified above, an object should be created for this tile.')
                    note.show()
            else:
                if (len(tile.tilecontents) > 0):
                    note.set_markup('<b>Note:</b> Given the object type specified above, this tile should <i>not</i> have an object.')
                    note.show()
                else:
                    note.hide()
        else:
            if tile.tilecontentid == 0 and len(tile.tilecontents) > 0:
                note.set_markup('<b>Note:</b> Given the object type specified above, this tile should <i>not</i> have an object.')
                note.show()
            elif tile.tilecontentid != 19 and tile.tilecontentid != 0 and len(tile.tilecontents) == 0:
                note.set_markup('<b>Note:</b> Given the object type specified above, an object should be created for this tile.')
                note.show()
            else:
                note.hide()

    def open_floorsel(self, widget):
        """ Show the floor selection window. """
        self.imgsel_launch(self.get_widget('floorimg'),
                self.gfx.tile_width, self.gfx.tile_height, self.gfx.floor_cols, self.gfx.floor_rows,
                self.gfx.get_floor, True, 1)

    def open_draw_floorsel(self, widget):
        """ Show the floor selection window for our drawing widget. """
        self.imgsel_launch(self.draw_floor_spin,
                self.gfx.tile_width, self.gfx.tile_height, self.gfx.floor_cols, self.gfx.floor_rows,
                self.gfx.get_floor, True, 1)

    def open_fill_floorsel(self, widget):
        """ Show the floor selection window for our "fill" widget. """
        self.imgsel_launch(self.fill_map_spin,
                self.gfx.tile_width, self.gfx.tile_height, self.gfx.floor_cols, self.gfx.floor_rows,
                self.gfx.get_floor, True, 1)

    def open_decalsel(self, widget):
        """ Show the decal selection window. """
        self.imgsel_launch(self.get_widget('decalimg'),
                self.gfx.tile_width, self.gfx.tile_height, self.gfx.decal_cols, self.gfx.decal_rows,
                self.gfx.get_decal, True, 1)

    def open_draw_decalsel(self, widget):
        """ Show the decal selection window for our drawing widget. """
        self.imgsel_launch(self.draw_decal_spin,
                self.gfx.tile_width, self.gfx.tile_height, self.gfx.decal_cols, self.gfx.decal_rows,
                self.gfx.get_decal, True, 1)

    def open_walldecalsel(self, widget):
        """ Show the wall decal selection window. """
        self.imgsel_launch(self.get_widget('walldecalimg'),
                self.gfx.tile_width, self.gfx.tile_height*3, self.gfx.walldecal_cols, self.gfx.walldecal_rows,
                self.gfx.get_object_decal, True, 1)

    def open_draw_walldecalsel(self, widget):
        """ Show the walldecal selection window for our drawing widget. """
        self.imgsel_launch(self.draw_walldecal_spin,
                self.gfx.tile_width, self.gfx.tile_height*3, self.gfx.walldecal_cols, self.gfx.walldecal_rows,
                self.gfx.get_object_decal, True, 1)

    def objsel_fix_pixbuf(self, pixbuf):
        """ Function to fix the pixbuf, for object loading. """
        return pixbuf[0]

    def open_objsel(self, widget, spinwidget=None):
        """
        Launch our object selection window.  This is effectively
        an override of imgsel_launch() - we'll be playing some games
        to reduce code duplication here.  This should probably be
        in a class, somehow, instead of a dict.
        """
        if c.book == 1:
            self.objsel_window.scrolltoggle.show()
            letters = ['d', 'c', 'b', 'a']
            self.objsel_window.label_a.set_label('Set A (misc)')
            self.objsel_window.label_b.set_label('Set B (misc)')
            self.objsel_window.label_c.set_label('Set C (walls)')
            self.objsel_window.label_d.set_label('Set D (trees)')
        else:
            self.objsel_window.scrolltoggle.hide()
            letters = ['c', 'd', 'a']
            self.objsel_window.label_a.set_label('Set A (misc)')
            self.objsel_window.label_c.set_label('Set B (walls)')
            self.objsel_window.label_d.set_label('Set C (trees)')
        self.imgsel_window = self.get_widget('objselwindow')
        self.imgsel_window.set_size_request((self.gfx.obj_a_width*self.gfx.obj_a_cols)+60, 600)
        if (spinwidget is None):
            self.imgsel_widget = self.get_widget('wallimg')
        else:
            self.imgsel_widget = spinwidget
        self.imgsel_getfunc = self.gfx.get_object
        self.imgsel_getfunc_obj_func = None
        self.imgsel_getfunc_extraarg = self.map.tree_set
        self.imgsel_pixbuffunc = self.objsel_fix_pixbuf
        self.imgsel_init_bgcolor()
        self.imgsel_blank_color = self.imgsel_generate_grayscale(127)
        self.objsel_panes = {}
        self.objsel_panes['a'] = {
                'init': False,
                'clean': [],
                'area': self.objsel_window.drawingarea_a,
                'width': self.gfx.obj_a_width,
                'height': self.gfx.obj_a_height,
                'cols': self.gfx.obj_a_cols,
                'rows': self.gfx.obj_a_rows,
                'x': self.gfx.obj_a_width*self.gfx.obj_a_cols,
                'y': self.gfx.obj_a_height*self.gfx.obj_a_rows,
                'offset': self.gfx.obj_a_offset,
                'mousex': -1,
                'mousey': -1,
                'mousex_prev': -1,
                'mousey_prev': -1,
                'blank': None,
                'page': 0,
            }
        if c.book == 1:
            self.objsel_panes['b'] = {
                    'init': False,
                    'clean': [],
                    'area': self.objsel_window.drawingarea_b,
                    'width': self.gfx.obj_b_width,
                    'height': self.gfx.obj_b_height,
                    'cols': self.gfx.obj_b_cols,
                    'rows': self.gfx.obj_b_rows,
                    'x': self.gfx.obj_b_width*self.gfx.obj_b_cols,
                    'y': self.gfx.obj_b_height*self.gfx.obj_b_rows,
                    'offset': self.gfx.obj_b_offset,
                    'mousex': -1,
                    'mousey': -1,
                    'mousex_prev': -1,
                    'mousey_prev': -1,
                    'blank': None,
                    'page': 1,
                }
        self.objsel_panes['c'] = {
                'init': False,
                'clean': [],
                'area': self.objsel_window.drawingarea_c,
                'width': self.gfx.obj_c_width,
                'height': self.gfx.obj_c_height,
                'cols': self.gfx.obj_c_cols,
                'rows': self.gfx.obj_c_rows,
                'x': self.gfx.obj_c_width*self.gfx.obj_c_cols,
                'y': self.gfx.obj_c_height*self.gfx.obj_c_rows,
                'offset': self.gfx.obj_c_offset,
                'mousex': -1,
                'mousey': -1,
                'mousex_prev': -1,
                'mousey_prev': -1,
                'blank': None,
                'page': 2,
            }
        self.objsel_panes['d'] = {
                'init': False,
                'clean': [],
                'area': self.objsel_window.drawingarea_d,
                'width': self.gfx.obj_d_width,
                'height': self.gfx.obj_d_height,
                'cols': self.gfx.obj_d_cols,
                'rows': self.gfx.obj_d_rows,
                'x': self.gfx.obj_d_width*self.gfx.obj_d_cols,
                'y': self.gfx.obj_d_height*self.gfx.obj_d_rows,
                'offset': self.gfx.obj_d_offset,
                'mousex': -1,
                'mousey': -1,
                'mousex_prev': -1,
                'mousey_prev': -1,
                'blank': None,
                'page': 3,
            }
        # Set initial page
        curpage = 0
        for letter in letters:
            if (int(self.imgsel_widget.get_value()) >= self.objsel_panes[letter]['offset']):
                curpage = self.objsel_panes[letter]['page']
                break
        self.objsel_window.book.set_current_page(curpage)
        self.objsel_current = ''
        #self.load_objsel_vars(self.get_widget('objsel_%s_area' % (letters[3-curpage])))
        self.imgsel_window.show()

    def open_draw_objsel(self, widget):
        """ Show the wall selection window for our drawing widget. """
        self.open_objsel(widget, self.draw_wall_spin)

    def load_objsel_vars(self, widget):
        """
        Given a widget (should be an object selection DrawingArea),
        populate the self.imgsel_* variables with the appropriate stuff.
        """
        wname = widget.get_name()
        (foo, letter, bar) = wname.split('_', 2)
        if (letter != self.objsel_current):
            for (key, val) in self.objsel_panes[letter].items():
                self.__dict__['imgsel_%s' % key] = val
                if key == 'area':
                    self.objsel_window.drawingarea = val
            self.objsel_current = letter

    def objsel_on_clicked(self, widget, event):
        self.load_objsel_vars(widget)
        self.imgsel_on_clicked(widget, event)

    def objsel_on_expose(self, widget, event):
        self.load_objsel_vars(widget)
        self.imgsel_on_expose(widget, event)

    def objsel_on_motion(self, widget, event):
        self.load_objsel_vars(widget)
        self.imgsel_on_motion(widget, event)

    def toggle_action_frames(self, which=''):
        for widgetname in ['draw_frame', 'erase_frame', 'object_frame']:
            if widgetname == which:
                self.get_widget(widgetname).show()
            else:
                self.get_widget(widgetname).hide()

    def update_activity_label(self, widget=None):
        newlabel = ''
        if self.ctl_edit_toggle.get_active():
            self.toggle_action_frames()
            newlabel = 'Editing Single Tiles'
        elif self.ctl_move_toggle.get_active():
            self.toggle_action_frames()
            newlabel = 'Scrolling Map'
        elif self.ctl_draw_toggle.get_active():
            self.toggle_action_frames('draw_frame')
            elems = []
            if (self.draw_floor_checkbox.get_active()):
                elems.append('Floors')
            if (self.draw_decal_checkbox.get_active()):
                elems.append('Decals')
            if (self.draw_wall_checkbox.get_active()):
                elems.append('Walls')
            if (self.draw_walldecal_checkbox.get_active()):
                elems.append('Wall Decals')
            if (self.draw_barrier.get_active()):
                elems.append('Barriers')
            if (len(elems) > 0):
                newlabel = 'Drawing %s' % (', '.join(elems))
            else:
                newlabel = 'Drawing (no elements selected)'
        elif self.ctl_erase_toggle.get_active():
            self.toggle_action_frames('erase_frame')
            elems = []
            if (self.erase_floor_checkbox.get_active()):
                elems.append('Floors')
            if (self.erase_decal_checkbox.get_active()):
                elems.append('Decals')
            if (self.erase_wall_checkbox.get_active()):
                elems.append('Walls')
            if (self.erase_walldecal_checkbox.get_active()):
                elems.append('Wall Decals')
            if (self.erase_barrier.get_active()):
                elems.append('Barriers')
            if (self.erase_entity_checkbox.get_active()):
                elems.append('Entities')
            if (self.erase_object_checkbox.get_active()):
                elems.append('Objects')
            if (len(elems) > 0):
                newlabel = 'Erasing %s' % (', '.join(elems))
            else:
                newlabel = 'Erasing (no elements selected)'
        elif self.ctl_object_toggle.get_active():
            self.toggle_action_frames('object_frame')
            obj = self.get_cur_object_placement()
            newlabel = 'Placing Object "%s"' % (obj.name)
        else:
            self.toggle_action_frames()
            newlabel = '<i>Unknown</i>'
        self.activity_label.set_markup('Activity: %s' % (newlabel))

    def on_control_toggle(self, widget):
        clicked = widget.get_name()
        if (widget.get_active()):
            if (clicked == 'ctl_edit_toggle'):
                self.edit_mode = self.MODE_EDIT
            elif (clicked == 'ctl_move_toggle'):
                self.edit_mode = self.MODE_MOVE
            elif (clicked == 'ctl_draw_toggle'):
                self.edit_mode = self.MODE_DRAW
            elif (clicked == 'ctl_erase_toggle'):
                self.edit_mode = self.MODE_ERASE
            elif (clicked == 'ctl_object_toggle'):
                self.edit_mode = self.MODE_OBJECT
            else:
                # Should maybe throw an exception here, but instead we'll
                # just spit something on the console and return.  No need to
                # get all huffy about it.
                print "Unknown control toggled, should never get here"
                return
            self.maparea.window.set_cursor(self.cursor_map[self.edit_mode])
            self.update_activity_label()

    def on_clicked(self, widget, event):
        """ Handle a mouse click. """
        # TODO: verify button numbers on, say, non-three-button mice
        if (event.button not in self.mouse_action_maps[self.edit_mode]):
            return

        action = self.mouse_action_maps[self.edit_mode][event.button]
        if (action == self.ACTION_DRAG):
            adjust = self.mainscroll.get_hadjustment()
            self.dragging = True
            self.hold_x = event.x_root
            self.hold_y = event.y_root
            self.diff_x = 0
            self.diff_y = 0
            self.maparea.window.set_cursor(self.cursor_move_drag)
        if (action == self.ACTION_EDIT):
            if (self.tile_y < len(self.map.tiles)):
                if (self.tile_x < len(self.map.tiles[self.tile_y])):
                    if c.book > 1:
                        self.store_hugegfx_state(self.map.tiles[self.tile_y][self.tile_x])
                    self.undo.store(self.tile_x, self.tile_y)
                    self.populate_tilewindow_from_tile(self.map.tiles[self.tile_y][self.tile_x])
                    self.get_widget('tilelabel').set_markup('<b>Map Tile (%d, %d)</b>' % (self.tile_x, self.tile_y))
                    self.tilewindow.show()
        elif (action == self.ACTION_DRAW):
            self.drawing = True
            self.action_draw_tile(self.tile_x, self.tile_y)
        elif (action == self.ACTION_ERASE):
            self.erasing = True
            self.action_erase_tile(self.tile_x, self.tile_y)
        elif (action == self.ACTION_OBJECT):
            self.action_place_object_tile(self.tile_x, self.tile_y)
        elif (action == self.ACTION_SCRIPT_ED):
            self.action_script_edit(self.tile_x, self.tile_y)

    def on_released(self, widget=None, event=None):
        if (self.dragging or self.drawing or self.erasing):
            self.dragging = False
            self.drawing = False
            self.erasing = False
            self.maparea.window.set_cursor(self.cursor_map[self.edit_mode])

    def handle_editing_exception(self, x, y, exception_info):
        """
        What to do when we encounter an exception while editing the map.
        exception_info should be the tuple returned by sys.exc_info().
        This is mostly important so that our undo state is set to something
        sane-ish which will allow the user to keep editing.  Which is, um,
        probably not a great idea anyway, but I've personally found it
        annoying to get munged up before, so there it is.
        """

        # Report our Exception to the user (let it go to stderr as well)
        exceptionType, exceptionValue, exceptionTraceback = exception_info
        traceback.print_exception(exceptionType, exceptionValue, exceptionTraceback, file=sys.stderr)
        exceptionStr = ''.join(traceback.format_exception(exceptionType, exceptionValue, exceptionTraceback))
        buf = self.map_exception_view.get_buffer()
        buf.set_text(exceptionStr)
        buf.place_cursor(buf.get_start_iter())
        self.map_exception_window.run()
        self.map_exception_window.hide()
        
        # Cancel out of the Undo so that the app isn't locked up
        # TODO: *should* we try to finish the undo instead, so it may be able
        # to back out *some* data at least?
        self.undo.cancel()

        # Redraw our tile anyway, just in case changes have taken place
        self.redraw_tile(x, y)

        # Reset our state vars (this generally won't happen automatically, because
        # we arrested the mouse with the new window)
        self.on_released()

    def action_draw_tile(self, x, y):
        """ What to do when we're drawing on a tile on the map."""

        # First store our undo state
        self.undo.store(x, y)
        self.undo.set_text('Draw')
        
        try:
            # Grab our tile object
            tile = self.map.tiles[y][x]
            if c.book > 1:
                self.store_hugegfx_state(tile)

            # Now draw anything that the user's requesed
            if (self.draw_floor_checkbox.get_active()):
                tile.floorimg = int(self.draw_floor_spin.get_value())
            if (self.draw_decal_checkbox.get_active()):
                tile.decalimg = int(self.draw_decal_spin.get_value())
            if (self.draw_wall_checkbox.get_active()):
                tile.wallimg = int(self.draw_wall_spin.get_value())
            if (self.draw_walldecal_checkbox.get_active()):
                tile.walldecalimg = int(self.draw_walldecal_spin.get_value())

            # Check to see if we should change the "wall" flag
            if (self.draw_barrier.get_active()):
                if (self.draw_barrier_seethrough.get_active()):
                    tile.wall = 5
                else:
                    tile.wall = 1
            elif (self.smartdraw_check.get_active() and self.draw_smart_barrier.get_active()):
                # TODO: it would be nice to check to see if we really should be updating
                # barriers here...  as it is, if you leave all the "drawing" checkboxes off
                # but draw around, this function will update barrier information as it goes.
                # Ah well.  For now I'm just going to let it do that.
                #if (self.draw_wall_checkbox.get_active() or self.draw_floor_checkbox.get_active() or
                #        self.draw_decal_checkbox.get_active()):
                if (tile.walldecalimg in self.smartdraw.wall_list['walldecal_seethrough']):
                    tile.wall = 5
                elif (c.book > 1 and tile.wallimg in self.smartdraw.wall_list['wall_restrict']):
                    tile.wall = 2
                elif (tile.wallimg in self.smartdraw.wall_list['wall_blocked']):
                    tile.wall = 1
                elif (tile.wallimg in self.smartdraw.wall_list['wall_seethrough']):
                    tile.wall = 5
                elif (tile.decalimg in self.smartdraw.wall_list['decal_blocked']):
                    tile.wall = 1
                elif (tile.decalimg in self.smartdraw.wall_list['decal_seethrough']):
                    tile.wall = 5
                elif (tile.floorimg in self.smartdraw.wall_list['floor_seethrough']):
                    tile.wall = 5
                else:
                    tile.wall = 0

            # Handle "smart" walls if requested
            if (self.draw_wall_checkbox.get_active() and self.smartdraw_check.get_active() and self.draw_smart_wall.get_active()):
                for dir in [Map.DIR_NE, Map.DIR_SE, Map.DIR_SW, Map.DIR_NW]:
                    self.undo.add_additional(self.map.tile_relative(x, y, dir))
                affected_tiles = self.smartdraw.draw_wall(tile)
                if (affected_tiles is not None):
                    self.undo.set_text('Smart Wall Draw')
                    for adjtile in affected_tiles:
                        self.redraw_tile(adjtile.x, adjtile.y)
            if (self.draw_wall_checkbox.get_active() and self.smartdraw_check.get_active() and self.smart_complex_objects.get_active()):
                (text, affected_tiles) = self.smartdraw.draw_smart_complex_wall(tile, self.undo)
                if (text is not None):
                    self.undo.set_text('Smart Wall Draw (%s)' % (text))
                    for adjtile in affected_tiles:
                        self.redraw_tile(adjtile.x, adjtile.y)

            # Handle "smart" floors if needed
            if (self.draw_floor_checkbox.get_active() and
                    not self.draw_decal_checkbox.get_active() and
                    self.smartdraw_check.get_active() and
                    self.draw_smart_floor.get_active()):
                for dir in [Map.DIR_NE, Map.DIR_E, Map.DIR_SE, Map.DIR_S, Map.DIR_SW, Map.DIR_W, Map.DIR_NW, Map.DIR_N]:
                    self.undo.add_additional(self.map.tile_relative(x, y, dir))
                affected_tiles = self.smartdraw.draw_floor(tile, self.draw_straight_paths.get_active())
                if (affected_tiles is not None):
                    self.undo.set_text('Smart Draw')
                    for adjtile in affected_tiles:
                        self.redraw_tile(adjtile.x, adjtile.y)
            if (self.draw_floor_checkbox.get_active() and self.smartdraw_check.get_active() and self.smart_complex_objects.get_active()):
                (text, affected_tiles) = self.smartdraw.draw_smart_complex_floor(tile, self.undo)
                if (text is not None):
                    self.undo.set_text('Smart Draw (%s)' % (text))
                    for adjtile in affected_tiles:
                        self.redraw_tile(adjtile.x, adjtile.y)

            # Handles "smart" decals if needed
            if (self.draw_decal_checkbox.get_active() and self.smartdraw_check.get_active() and self.draw_smart_floor.get_active()):
                self.smartdraw.draw_decal(tile)
            if (self.draw_walldecal_checkbox.get_active() and self.smartdraw_check.get_active() and self.draw_smart_walldecal.get_active()):
                self.smartdraw.draw_walldecal(tile)

            # Smart decals (triggered by the floor checkbox for now)
            if (self.draw_decal_checkbox.get_active() and self.smartdraw_check.get_active() and self.smart_complex_objects.get_active()):
                (text, affected_tiles) = self.smartdraw.draw_smart_complex_decal(tile, self.undo)
                if (text is not None):
                    self.undo.set_text('Smart Draw (%s)' % (text))
                    for adjtile in affected_tiles:
                        self.redraw_tile(adjtile.x, adjtile.y)

            # And then close off our undo and redraw if needed
            if (self.undo.finish()):
                self.redraw_tile(x, y)
                self.update_undo_gui()

            # Check for hugegfx changes
            if c.book > 1:
                if self.check_hugegfx_state(tile):
                    self.draw_map()

        except Exception:

            self.handle_editing_exception(x, y, sys.exc_info())

    def action_erase_tile(self, x, y):
        """ What to do when we're erasing on a tile on the map."""

        # TODO: Figure out if we really should do any of the smartdraw
        # stuff here.  I'm not so sure.  And anyway, I suspect that
        # it may be not processing that stuff anyway right now.

        # First store our undo state
        self.undo.store(x, y)
        self.undo.set_text('Erase')

        try:
            
            # Grab our tile object
            tile = self.map.tiles[y][x]
            if c.book > 1:
                self.store_hugegfx_state(tile)

            # Now erase anything that the user's requesed
            if (self.erase_barrier.get_active()):
                tile.wall = 0
            if (self.erase_floor_checkbox.get_active()):
                if (self.smartdraw_check.get_active() and self.draw_smart_barrier.get_active()):
                    if (tile.floorimg in self.smartdraw.wall_list['floor_seethrough']):
                        tile.wall = 0
                tile.floorimg = 0
            if (self.erase_decal_checkbox.get_active()):
                if (self.smartdraw_check.get_active() and self.draw_smart_barrier.get_active()):
                    if (tile.decalimg in self.smartdraw.wall_list['decal_blocked']+self.smartdraw.wall_list['decal_seethrough']):
                        tile.wall = 0
                tile.decalimg = 0
            if (self.erase_wall_checkbox.get_active()):
                if (self.smartdraw_check.get_active() and self.draw_smart_barrier.get_active()):
                    if (tile.wallimg in self.smartdraw.wall_list['wall_blocked']+self.smartdraw.wall_list['wall_seethrough']):
                        tile.wall = 0
                tile.wallimg = 0
            if (self.erase_walldecal_checkbox.get_active()):
                tile.walldecalimg = 0
            if (self.erase_entity_checkbox.get_active()):
                self.map.delentity(x, y)
            if (self.erase_object_checkbox.get_active()):
                num = len(tile.tilecontents)
                for i in range(num):
                    self.map.deltilecontent(x, y, 0)
                tile.tilecontentid = 0

            # Handle "smart" walls if requested
            if (self.draw_wall_checkbox.get_active() and self.smartdraw_check.get_active() and self.draw_smart_wall.get_active()):
                for dir in [Map.DIR_NE, Map.DIR_SE, Map.DIR_SW, Map.DIR_NW]:
                    self.undo.add_additional(self.map.tile_relative(x, y, dir))
                affected_tiles = self.smartdraw.draw_wall(tile)
                if (affected_tiles is not None):
                    self.undo.set_text('Smart Wall Erase')
                    for adjtile in affected_tiles:
                        self.redraw_tile(adjtile.x, adjtile.y)

            # Handle "smart" floors if needed
            if (self.erase_floor_checkbox.get_active() and
                    not self.erase_decal_checkbox.get_active() and
                    self.smartdraw_check.get_active() and
                    self.draw_smart_floor.get_active()):
                for dir in [Map.DIR_NE, Map.DIR_E, Map.DIR_SE, Map.DIR_S, Map.DIR_SW, Map.DIR_W, Map.DIR_NW, Map.DIR_N]:
                    self.undo.add_additional(self.map.tile_relative(x, y, dir))
                affected_tiles = self.smartdraw.draw_floor(tile, self.draw_straight_paths.get_active())
                if (affected_tiles is not None):
                    self.undo.set_text('Smart Erase')
                    for adjtile in affected_tiles:
                        self.redraw_tile(adjtile.x, adjtile.y)

            # Handles "smart" wall decals if needed
            # This just randomizes, so don't bother here.
            #if (self.erase_walldecal_checkbox.get_active() and self.smartdraw_check.get_active() and self.draw_smart_walldecal.get_active()):
            #    self.smartdraw.draw_walldecal(tile)

            # And then close off our undo and redraw if needed
            if (self.undo.finish()):
                self.redraw_tile(x, y)
                self.update_undo_gui()

            # Check for hugegfx changes
            if c.book > 1:
                if self.check_hugegfx_state(tile):
                    self.draw_map()

        except Exception:

            self.handle_editing_exception(x, y, sys.exc_info())

    def get_cur_object_placement(self):
        """
        Looks up our currently-selected premade object
        """
        iter = self.get_widget('objectplace_combo').get_active_iter()
        model = self.get_widget('objectplace_combo').get_model()
        objidx = model.get_value(iter, 1)
        objcat = model.get_value(iter, 2)
        return self.smartdraw.premade_objects.get(objcat, objidx)

    def action_place_object_tile(self, x, y):
        """ What to do when we're told to place an object on a tile on the map."""

        # Make sure we know what we're drawing
        obj = self.get_cur_object_placement()

        # Store our undo state
        self.undo.store(x, y)
        self.undo.set_text('Place Object "%s"' % (obj.name))

        try:

            # It's possible that our object placement may touch adjacent tiles, as well.
            # Load those in now.
            for dir in [Map.DIR_NE, Map.DIR_E, Map.DIR_SE, Map.DIR_S, Map.DIR_SW, Map.DIR_W, Map.DIR_NW, Map.DIR_N]:
                self.undo.add_additional(self.map.tile_relative(x, y, dir))
            
            # Grab our tile object
            tile = self.map.tiles[y][x]
            if c.book > 1:
                self.store_hugegfx_state(tile)

            # Let's just implement this in SmartDraw
            additionals = self.smartdraw.place_object(tile, obj)

            # Redraw any additional tiles here
            for add_tile in additionals:
                self.redraw_tile(add_tile.x, add_tile.y)

            # And then close off our undo and redraw if needed
            if (self.undo.finish()):
                self.redraw_tile(x, y)
                self.update_undo_gui()

            # Check our hugegfx state and redraw if need be
            if c.book > 1:
                if self.check_hugegfx_state(tile):
                    self.draw_map()

        except Exception:

            self.handle_editing_exception(x, y, sys.exc_info())

    def action_script_edit(self, x, y):
        """
        What to do when we've been clicked from the script editing window.
        This is kind of a hack; the MapSelector class from scripteditor will
        override this function definition when it's running and do its stuff
        from there.
        """
        pass

    def map_toggle(self, widget):
        if not self.updating_map_checkboxes:
            self.draw_map()

    def mass_update_checkboxes(self, status, checkboxes):
        self.updating_map_checkboxes = True
        changed = False
        for elem in checkboxes:
            if (elem.get_active() != status):
                changed = True
                elem.set_active(status)
        self.updating_map_checkboxes = False
        if changed:
            self.draw_map()

    def draw_check_set_to(self, status):
        return self.mass_update_checkboxes(status, [self.floor_toggle, self.decal_toggle, self.object_toggle,
            self.wall_toggle, self.tree_toggle, self.objectdecal_toggle, self.entity_toggle, self.huge_gfx_toggle])

    def draw_check_all(self, widget):
        self.draw_check_set_to(True)

    def draw_uncheck_all(self, widget):
        self.draw_check_set_to(False)

    def highlight_check_set_to(self, status):
        return self.mass_update_checkboxes(status, [self.barrier_hi_toggle, self.tilecontent_hi_toggle, self.entity_hi_toggle])

    def highlight_check_all(self, widget):
        self.highlight_check_set_to(True)

    def highlight_uncheck_all(self, widget):
        self.highlight_check_set_to(False)

    # Assumes that the context is tilebuf_ctx, hence the hardcoded width/height
    # We're passing it in so we're not constantly referencing self.tilebuf_ctx
    def composite_simple(self, context, surface, color):
        context.save()
        context.set_operator(cairo.OPERATOR_ATOP)
        context.set_source_rgba(*color)
        context.rectangle(0, 0, surface.get_width(), surface.get_height())
        context.fill()
        context.restore()

    def draw_tile(self, x, y, usecache=False, do_main_paint=True):
        """ Draw a single tile of the map. """

        # TODO: Layers are pretty inefficient and slow here, IMO
        barrier = False
        tilecontent = False
        pointer = False
        entity = False

        # Use local vars instead of continually calling out
        tile = self.map.tiles[y][x]
        tile_ctx = self.tilebuf_ctx
        main_ctx = self.ctx

        if (do_main_paint and x == self.tile_x and y == self.tile_y):
            pointer = (1, 1, 1, 0.5)

        if (tile.entity is not None):
            if self.map.is_savegame():
                if (tile.entity.friendly == 1):
                    entity = (0, 1, 0, 0.5)
                else:
                    entity = (1, 0, 0, 0.5)
            else:
                if tile.entity.entid in c.entitytable:
                    if c.entitytable[tile.entity.entid].friendly == 1:
                        entity = (0, 1, 0, 0.5)
                    else:
                        entity = (1, 0, 0, 0.5)
                else:
                    entity = (1, 0, 0, 0.5)

        if c.book == 1:
            if (tile.tilecontentid != 0 and len(tile.tilecontents) > 0):
                tilecontent = (1, 1, 0, 0.5)
            elif (tile.tilecontentid != 0 and len(tile.tilecontents) == 0):
                tilecontent = (0, .784, .784, 0.5)
            elif (tile.tilecontentid == 0 and len(tile.tilecontents) > 0):
                # afaik, this doesn't happen.  should use something other than red here, though
                tilecontent = (1, 0, 0, 0.5)
        else:
            if (tile.tilecontentid == 0 and len(tile.tilecontents) > 0):
                # afaik, this doesn't happen.  should use something other than red here, though
                tilecontent = (1, 0, 0, 0.5)
            elif (tile.tilecontentid >= 25 and tile.tilecontentid < 50):
                tilecontent = (0, .784, .784, 0.5)
            elif (tile.tilecontentid > 0 and len(tile.tilecontents) == 0):
                # This shouldn't happen either
                tilecontent = (1, 0, 0, 0.5)
            elif tile.tilecontentid > 0:
                tilecontent = (1, 1, 0, 0.5)

        if (tile.wall == 1):
            barrier = (.784, .784, .784, 0.5)
        elif (tile.wall == 2):
            barrier = (.41, .75, .83, 0.5)
        elif (tile.wall == 5):
            barrier = (.684, .684, .950, 0.5)
        elif (tile.floorimg == 126 and not self.floor_toggle.get_active()):
            barrier = (0, 0, .784, 0.5)

        # TODO: xpad processing should be abstracted somehow when we're drawing whole rows
        # (for instance, when initially loading the map)
        if (y % 2 == 1):
            xpad = self.z_halfwidth
        else:
            xpad = 0

        # Coordinates
        #      2
        #   1     3
        #      4
        xstart = (x*self.z_width)+xpad
        x1 = xstart+1
        x3 = xstart+self.z_width-1

        ystart = y*self.z_halfheight
        y2 = ystart+1
        y4 = ystart+self.z_height-1
        #if (y4-y2<3):
        #    # This is for our two most-zoomed-out levels
        #    y4 = y4 + 1
        #    y2 = y2 - 1

        # Area we're actually drawing
        top = y2-(self.z_4xheight)
        height = self.z_5xheight
        buftop = 0
        if (top<0):
            height = height+top
            buftop = -top
            top = 0

        # Simply redraw the area from our cache, if we should
        if (do_main_paint and usecache and not pointer):
            main_ctx.save()
            main_ctx.set_operator(cairo.OPERATOR_SOURCE)
            main_ctx.rectangle(x1-self.z_tilebuf_offset, top, self.z_tilebuf_w, height)
            main_ctx.set_source_surface(self.guicache, 0, 0)
            main_ctx.fill()
            main_ctx.restore()
            return

        # Prepare our pixbuf
        tile_ctx.save()
        tile_ctx.set_operator(cairo.OPERATOR_SOURCE)
        if (do_main_paint and usecache):
            # If we're the pointer, always overlay our black tile
            tile_ctx.set_source_surface(self.basictile)
        else:
            tile_ctx.set_source_surface(self.blanktile)
        tile_ctx.paint()
        tile_ctx.restore()

        # Keep track of whether we've drawn anything or not
        drawn = False

        # Draw the floor tile
        if (tile.floorimg > 0 and self.floor_toggle.get_active()):
            pixbuf = self.gfx.get_floor(tile.floorimg, self.curzoom)
            if (pixbuf is not None):
                tile_ctx.set_source_surface(pixbuf, self.z_tilebuf_offset, self.z_4xheight)
                tile_ctx.paint()
                drawn = True

        # Draw the floor decal
        if (tile.decalimg > 0 and self.decal_toggle.get_active()):
            pixbuf = self.gfx.get_decal(tile.decalimg, self.curzoom)
            if (pixbuf is not None):
                tile_ctx.set_source_surface(pixbuf, self.z_tilebuf_offset, self.z_4xheight)
                tile_ctx.paint()
                drawn = True
                # Check to see if we should draw a flame
                if ((self.req_book == 1 and tile.decalimg == 52) or
                    (self.req_book == 2 and tile.decalimg == 101)):
                    pixbuf = self.gfx.get_flame(self.curzoom)
                    if (pixbuf is not None):
                        # TODO: in book 2, campfire wall objects will overwrite some of our campfire flame
                        # (note that the campfire wall object will NOT provide an in-game flame on its own)
                        xoffset = self.z_halfwidth-int(pixbuf.get_width()/2)+self.z_tilebuf_offset
                        yoffset = int(self.z_height*0.4)
                        tile_ctx.set_source_surface(pixbuf, xoffset, self.z_3xheight+yoffset)
                        tile_ctx.paint()

        # Draw "walls," though only if we should
        wallid = tile.wallimg
        if wallid > 0:
            try:
                walltype = self.gfx.wall_types[wallid]
            except KeyError:
                # This should only happen for Book 2 maps, and should only
                # denote that it's one of the gigantic graphic maps.
                walltype = self.gfx.TYPE_NONE

            # Draw the object
            if (walltype == self.gfx.TYPE_OBJ and self.object_toggle.get_active()):
                (pixbuf, pixheight, offset) = self.gfx.get_object(wallid, self.curzoom)
                if (pixbuf is not None):
                    tile_ctx.set_source_surface(pixbuf, offset+self.z_tilebuf_offset, self.z_height*(4-pixheight))
                    tile_ctx.paint()
                    drawn = True
                    if (self.req_book == 2 and (tile.wallimg == 349 or tile.wallimg == 350)):
                        pixbuf = self.gfx.get_flame(self.curzoom)
                        if (pixbuf is not None):
                            xoffset = self.z_halfwidth-int(pixbuf.get_width()/2)+self.z_tilebuf_offset
                            yoffset = int(self.z_height*0.3)
                            tile_ctx.set_source_surface(pixbuf, xoffset, self.z_height+yoffset)
                            tile_ctx.paint()

            # Draw walls
            elif (walltype == self.gfx.TYPE_WALL and self.wall_toggle.get_active()):
                (pixbuf, pixheight, offset) = self.gfx.get_object(wallid, self.curzoom)
                if (pixbuf is not None):
                    tile_ctx.set_source_surface(pixbuf, offset+self.z_tilebuf_offset, self.z_height*(4-pixheight))
                    tile_ctx.paint()
                    drawn = True

            # Draw trees
            elif (walltype == self.gfx.TYPE_TREE and self.tree_toggle.get_active()):
                (pixbuf, pixheight, offset) = self.gfx.get_object(wallid, self.curzoom, False, self.map.tree_set)
                if (pixbuf is not None):
                    tile_ctx.set_source_surface(pixbuf, offset+self.z_tilebuf_offset, self.z_height*(4-pixheight))
                    tile_ctx.paint()
                    drawn = True

        # Draw a zapper
        if (self.req_book > 1 and tile.tilecontentid == 19 and self.object_toggle.get_active()):
            pixbuf = self.gfx.get_zapper(self.curzoom)
            if pixbuf is not None:
                xoffset = self.z_tilebuf_offset
                yoffset = 0
                tile_ctx.set_source_surface(pixbuf, xoffset, self.z_3xheight+yoffset)
                tile_ctx.paint()

        # Draw the object decal
        if (tile.walldecalimg > 0 and self.objectdecal_toggle.get_active()):
            pixbuf = self.gfx.get_object_decal(tile.walldecalimg, self.curzoom)
            if (pixbuf is not None):
                tile_ctx.set_source_surface(pixbuf, self.z_tilebuf_offset, self.z_2xheight)
                tile_ctx.paint()
                drawn = True
                # Check to see if we should draw a flame
                if ((self.req_book == 1 and (tile.walldecalimg == 17 or tile.walldecalimg == 18)) or
                    (self.req_book == 2 and (tile.walldecalimg == 2 or tile.walldecalimg == 4))):
                    pixbuf = self.gfx.get_flame(self.curzoom)
                    if (pixbuf is not None):
                        xoffset = int(pixbuf.get_width()*0.3)
                        yoffset = int(self.z_height/4)
                        if (self.req_book == 2):
                            yoffset -= 1
                        if (tile.walldecalimg == 17 or tile.walldecalimg == 2):
                            tile_ctx.set_source_surface(pixbuf, self.curzoom-pixbuf.get_width()-xoffset+self.z_tilebuf_offset, self.z_2xheight+yoffset)
                        else:
                            tile_ctx.set_source_surface(pixbuf, xoffset+self.z_tilebuf_offset, self.z_2xheight+yoffset)
                        tile_ctx.paint()

        # Draw the entity if needed
        # We switch to using op_ctx and op_surf because we may not be drawing on tile_ctx
        # from this point on, depending on entity width
        op_surf = self.tilebuf
        op_ctx = tile_ctx
        op_xoffset = 0
        if (tile.entity is not None and self.entity_toggle.get_active()):
            ent_img = self.gfx.get_entity(tile.entity.entid, tile.entity.direction, self.curzoom)
            if (ent_img is not None):
                if (ent_img.get_width() > self.z_tilebuf_w):
                    # This whole bit here will copy our tilebuf into a larger surface, centered
                    # (so, transparent on the side)
                    self.ent_surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, ent_img.get_width(), self.z_5xheight)
                    self.ent_ctx = cairo.Context(self.ent_surf)
                    op_xoffset = int((ent_img.get_width()-self.z_tilebuf_w)/2)
                    self.ent_ctx.set_source_surface(op_surf, op_xoffset, 0)
                    self.ent_ctx.paint()
                    op_surf = self.ent_surf
                    op_ctx = self.ent_ctx
                if (op_surf.get_width() > ent_img.get_width()):
                    offset = int((op_surf.get_width() - ent_img.get_width())/2)
                else:
                    offset = 0
                op_ctx.set_source_surface(ent_img, offset, self.z_5xheight-ent_img.get_height())
                op_ctx.paint()
                drawn = True

        # Now, before we do highlights, see if we've drawn anything.  If not, 
        # overlay our basic black tile, so that highlighting shows up if it
        # needs to.  If we *have* drawn something, just let it be.  (We do this
        # primarily to avoid graphical glitches on cliff-face graphics, where
        # having the black tile overlay makes things look bad.)  Additionally
        # only do it if we would have done some highlighting.
        drawbarrier = (barrier and self.barrier_hi_toggle.get_active())
        drawtilecontent = (tilecontent and self.tilecontent_hi_toggle.get_active())
        drawentity = (entity and self.entity_hi_toggle.get_active())
        if (not drawn and (drawbarrier or drawtilecontent or drawentity)):
            tile_ctx.set_source_surface(self.basictile)
            tile_ctx.paint()

        # Draw Barrier Highlights
        if (drawbarrier):
            self.composite_simple(op_ctx, op_surf, barrier)

        # Draw Tilecontent Highlights
        if (drawtilecontent):
            self.composite_simple(op_ctx, op_surf, tilecontent)

        # Draw Entity Highlights
        if (drawentity):
            self.composite_simple(op_ctx, op_surf, entity)

        # Now draw the pixbuf onto our pixmap
        if (do_main_paint):
            if (usecache):
                # We only get here when we're the pointer
                self.composite_simple(op_ctx, op_surf, pointer)
                main_ctx.set_source_surface(op_surf, x1-op_xoffset-self.z_tilebuf_offset, top-buftop)
                main_ctx.paint()
            else:
                # This is only for the initial map population
                self.guicache_ctx.set_source_surface(op_surf, x1-op_xoffset-self.z_tilebuf_offset, top-buftop)
                self.guicache_ctx.paint()

        return (op_surf, op_xoffset+self.z_tilebuf_offset)

    def draw_huge_gfx(self, tile, ctx=None, xoff=None, yoff=None):
        """
        Draws a "huge" graphic image on our map (like Hammerlorne, etc).
        Only used in Book 2.
        """
        if tile.tilecontentid == 21 and len(tile.tilecontents) > 0:
            img = self.gfx.get_huge_gfx(tile.tilecontents[0].extratext, self.curzoom)
            if img:
                x = tile.x
                y = tile.y
                # TODO: xpad processing should be abstracted somehow when we're drawing whole rows
                # (for instance, when initially loading the map)
                if (y % 2 == 1):
                    xpad = self.z_halfwidth
                else:
                    xpad = 0

                xstart = (x*self.z_width)+xpad - int(img.get_width()/2) + self.z_height
                ystart = y*self.z_halfheight + self.z_height

                if ctx is None:
                    ctx = self.guicache_ctx
                else:
                    xstart -= xoff
                    ystart -= yoff

                ctx.set_source_surface(img, xstart, ystart-img.get_height())
                ctx.paint()

    def update_composite(self):
        """
        Updates the composite image in the individual tile-editing window.
        This duplicates some code from draw_tile() but there are some differences
        I'd rather not have to deal with in there (ie: we're always fully-zoomed-in
        here, we don't want to do any highlighting, entities won't actually get
        drawn, etc, etc).
        """

        # Grab our variables and clear out the pixbuf
        tile = self.map.tiles[self.tile_y][self.tile_x]
        comp_pixbuf = self.comp_pixbuf
        comp_pixbuf.fill(0)

        # Sizing vars
        width = self.gfx.tile_width
        width_x2 = width*2
        height_x4 = width_x2
        height = self.gfx.tile_height
        height_x2 = width
        height_x3 = height*3

        # These torch numbers are rather Magic.  They come from
        # when we still had everything hardcoded (from Book 1, since it
        # wasn't a problem then) and would just nudge things pixel-by-pixel.
        # Here we're just computing the ratio based on if height_x4 was 104,
        # and then scaling to the *actual* height_x4.  It's dumb, yeah.
        torchbuf = self.gfx.get_flame(width, True)
        torchwidth = torchbuf.get_property('width')
        torchheight = torchbuf.get_property('height')
        torchdecalyoff = int((88/104.0)*height_x4)
        torchwallyoff = int((35/104.0)*height_x4)
        torchwallyoff2 = int((30/104.0)*height_x4)
        torchsconceyoff = int((58/104.0)*height_x4)
        torchsconceyoff2 = int((30/104.0)*height_x4)
        torchsconcexoff = int((29/52.0)*width)
        torchsconcexoff2 = int((5/52.0)*width)

        # Now do all the actual compositing
        if (tile.floorimg > 0):
            pixbuf = self.gfx.get_floor(tile.floorimg, width, True)
            if (pixbuf is not None):
                pixbuf.composite(comp_pixbuf,
                        0, height_x4,
                        width, height,
                        0, height_x4,
                        1, 1, gtk.gdk.INTERP_NEAREST, 255)
        if (tile.decalimg > 0):
            pixbuf = self.gfx.get_decal(tile.decalimg, width, True)
            if (pixbuf is not None):
                pixbuf.composite(comp_pixbuf,
                        0, height_x4,
                        width, height,
                        0, height_x4,
                        1, 1, gtk.gdk.INTERP_NEAREST, 255)
            if ((self.req_book == 1 and tile.decalimg == 52) or
                (self.req_book == 2 and tile.decalimg == 101) or
                (self.req_book == 3 and tile.decalimg == 101)):
                if (torchbuf is not None):
                    torchbuf.composite(comp_pixbuf,
                            torchwidth-1, torchdecalyoff,
                            torchwidth, torchheight,
                            torchwidth-1, torchdecalyoff,
                            1, 1, gtk.gdk.INTERP_NEAREST, 255)
        if (tile.wallimg > 0):
            (pixbuf, pixheight, offset) = self.gfx.get_object(tile.wallimg, width, True, self.map.tree_set)
            if (pixbuf is not None):
                pixbuf.composite(comp_pixbuf,
                        0, height*(4-pixheight),
                        width, height*(pixheight+1),
                        offset, height*(4-pixheight),
                        1, 1, gtk.gdk.INTERP_NEAREST, 255)
            if (self.req_book == 2 and (tile.wallimg == 349 or tile.wallimg == 350)):
                if (torchbuf is not None):
                    torchbuf.composite(comp_pixbuf,
                            torchwidth-1, torchwallyoff,
                            torchwidth, torchwallyoff2,
                            torchwidth-1, torchwallyoff,
                            1, 1, gtk.gdk.INTERP_NEAREST, 255)
        if (tile.walldecalimg > 0):
            pixbuf = self.gfx.get_object_decal(tile.walldecalimg, width, True)
            if (pixbuf is not None):
                pixbuf.composite(comp_pixbuf,
                        0, height_x2,
                        width, height_x3,
                        0, height_x2,
                        1, 1, gtk.gdk.INTERP_NEAREST, 255)
            if ((self.req_book == 1 and (tile.walldecalimg == 17 or tile.walldecalimg == 18)) or
                (self.req_book == 2 and (tile.walldecalimg == 2 or tile.walldecalimg == 4))):
                if (torchbuf is not None):
                    if (tile.walldecalimg == 17 or tile.walldecalimg == 2):
                        torchbuf.composite(comp_pixbuf,
                                torchsconcexoff, torchsconceyoff,
                                torchwidth, torchsconceyoff2,
                                torchsconcexoff, torchsconceyoff,
                                1, 1, gtk.gdk.INTERP_NEAREST, 255)
                    elif (tile.walldecalimg == 18 or tile.walldecalimg == 4):
                        torchbuf.composite(comp_pixbuf,
                                torchsconcexoff2, torchsconceyoff,
                                torchwidth, torchsconceyoff2,
                                torchsconcexoff2, torchsconceyoff,
                                1, 1, gtk.gdk.INTERP_NEAREST, 255)

        # ... and update the main image
        self.get_widget('composite_area').set_from_pixbuf(comp_pixbuf)

    def export_map_pngs(self):
        """
        A little sub to loop through and write out a PNG of each mapname.
        This is never called in the actual code, though it's trivial to hook it
        in so that it'll write out PNGs for every single map specified on
        the commandline.
        """
        self.mapinit = True
        self.set_zoom_vars(1)
        print self.options
        for file in self.options['filenames']:
            self.load_from_file(file)
            #self.draw_map()
            (pngfile, junk) = file.split('.')
            pngfile = '%s.png' % (pngfile)
            self.guicache.write_to_png(pngfile)
        import sys
        sys.exit(0)
        return False

    def store_hugegfx_state(self, tile):
        """
        Stores whether or not there's a current hugegfx on the given tile
        (and stores the graphic name).  Used before a tile is edited.
        """
        if (tile.wallimg == 1000 and tile.tilecontentid == 21 and len(tile.tilecontents) != 0):
            self.cur_hugegfx_state = tile.tilecontents[0].extratext
        else:
            self.cur_hugegfx_state = None

    def check_hugegfx_state(self, tile):
        """
        Compares the current state of the given tile versus our stored
        hugegfx state (see store_hugegfx_state()).  Will return True if
        a redraw of the map is needed.

        Will also upkeep our self.huge_gfx_rows list
        """
        if (tile.wallimg == 1000 and tile.tilecontentid == 21 and len(tile.tilecontents) != 0):
            new_hugegfx_state = tile.tilecontents[0].extratext
        else:
            new_hugegfx_state = None
        if (new_hugegfx_state != self.cur_hugegfx_state):
            if new_hugegfx_state is None:
                self.huge_gfx_rows[tile.y].remove(tile.x)
            elif self.cur_hugegfx_state is None:
                if tile.x not in self.huge_gfx_rows[tile.y]:
                    self.huge_gfx_rows[tile.y].append(tile.x)
                    self.huge_gfx_rows[tile.y].sort()
            return True
        else:
            return False

    def draw_map(self, widget=None):
        """
        This is the routine which sets up our initial map.  This used to be
        a part of expose_map, but this way we can throw up a progress dialog
        so the user's not wondering what's going on.

        Note that we're drawing to the main window HERE instead of in the
        setup areas of expose_map, so that the old map image stays onscreen
        for as long as possible.

        One further note: this is kicked off from maparea's 'realize' signal
        """

        # Timing, and statusbar
        time_a = time.time()
        self.drawstatusbar.set_fraction(0)
        self.drawstatuswindow.show()

        self.maparea.set_size_request(self.z_mapsize_x, self.z_mapsize_y)
        self.pixmap = gtk.gdk.Pixmap(self.maparea.window, self.z_mapsize_x, self.z_mapsize_y)

        self.ctx = self.pixmap.cairo_create()
        # Comment the next two lines out if you're exporting map PNGs
        # (so that the images have a tarnsparent background).  Also
        # another two lines below
        self.ctx.set_source_rgba(0, 0, 0, 1)
        self.ctx.paint()

        self.tilebuf = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.z_tilebuf_w, self.z_5xheight)
        self.tilebuf_ctx = cairo.Context(self.tilebuf)
        self.guicache = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.z_mapsize_x, self.z_mapsize_y)
        self.guicache_ctx = cairo.Context(self.guicache)
        # Here, for PNG exports
        self.guicache_ctx.set_source_rgba(0, 0, 0, 1)
        self.guicache_ctx.paint()

        self.ent_surf = None
        self.ent_ctx = None

        # Activate (or deactivate) our "draw barrier" checkboxes depending on if we're highlighting
        # barriers or not
        if (self.barrier_hi_toggle.get_active()):
            self.draw_barrier.set_sensitive(True)
            self.draw_barrier_seethrough.set_sensitive(True)
            self.erase_barrier.set_sensitive(True)
        else:
            self.draw_barrier.set_sensitive(False)
            self.draw_barrier.set_active(False)
            self.draw_barrier_seethrough.set_sensitive(False)
            self.draw_barrier_seethrough.set_active(False)
            self.erase_barrier.set_sensitive(False)
            self.erase_barrier.set_active(False)

        # ... and also for objects
        if (self.tilecontent_hi_toggle.get_active()):
            self.erase_object_checkbox.set_sensitive(True)
        else:
            self.erase_object_checkbox.set_sensitive(False)
            self.erase_object_checkbox.set_active(False)

        # Set up a "blank" tile to draw everything else on top of
        self.blanktile = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.z_tilebuf_w, self.z_5xheight)
        tile_ctx = cairo.Context(self.blanktile)
        tile_ctx.save()
        tile_ctx.set_operator(cairo.OPERATOR_CLEAR)
        tile_ctx.paint()
        tile_ctx.restore()

        # Set up a default tile with just a black tile, for otherwise-empty tiles
        self.basictile = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.z_tilebuf_w, self.z_5xheight)
        basic_ctx = cairo.Context(self.basictile)
        basic_ctx.set_source_rgba(0, 0, 0, 1)
        basic_ctx.move_to(self.z_tilebuf_offset+0, self.z_4xheight+self.z_halfheight)
        basic_ctx.line_to(self.z_tilebuf_offset+self.z_halfwidth, self.z_4xheight)
        basic_ctx.line_to(self.z_tilebuf_offset+self.z_width, self.z_4xheight+self.z_halfheight)
        basic_ctx.line_to(self.z_tilebuf_offset+self.z_halfwidth, self.z_5xheight)
        basic_ctx.close_path()
        basic_ctx.fill()

        # Draw the tiles
        self.huge_gfx_rows = []
        # TODO: for editing's sake, we may want to abstract this huge_gfx_rows maintenance
        # to a helper func (with an _add and _remove or whatever)
        #time_c = time.time()
        for i in range(200):
            self.huge_gfx_rows.append([])
        for y in range(len(self.map.tiles)):
            huge_gfxes = []
            for x in range(len(self.map.tiles[y])):
                self.draw_tile(x, y)
                if self.map.tiles[y][x].tilecontentid == 21:
                    huge_gfxes.append(self.map.tiles[y][x])
            if self.req_book > 1 and self.huge_gfx_toggle.get_active():
                for tile in huge_gfxes:
                    self.draw_huge_gfx(tile)
                    self.huge_gfx_rows[y].append(tile.x)
            if (y % 10 == 0):
                self.drawstatusbar.set_fraction(y/float(len(self.map.tiles)))
                while gtk.events_pending():
                    gtk.main_iteration()
        #time_d = time.time()
        #print 'Inner loop: %0.2f' % (time_d-time_c)

        # Finish drawing
        self.ctx.set_source_surface(self.guicache, 0, 0)
        self.ctx.paint()
        
        # ... and draw onto our main area (this is duplicated below, in expose_map)
        self.maparea.window.draw_drawable(self.maparea.get_style().fg_gc[gtk.STATE_NORMAL],
                self.pixmap,
                0, 0,
                0, 0,
                self.z_mapsize_x, self.z_mapsize_y)

        # Clean up our statusbar
        self.drawstatuswindow.hide()

        # Report timing
        time_b = time.time()
        print "Map rendered in %0.2f seconds" % (time_b-time_a)

        # From now on, our map's considered initialized
        self.mapinit = True

        # Make sure we only do this once, when called from idle_add initially
        return False


    def expose_map(self, widget, event):

        # Don't bother to do anything unless we've been initialized
        if (self.mapinit):

            # Redraw what tiles need to be redrawn
            for (x, y) in self.cleantiles:
                self.draw_tile(x, y, True)

            # Render to the window (this is duplicated above, in draw_map)
            self.maparea.window.draw_drawable(
                    self.maparea.get_style().fg_gc[gtk.STATE_NORMAL],
                    self.pixmap,
                    0, 0,
                    0, 0,
                    self.z_mapsize_x, self.z_mapsize_y)

            # Make sure our to-clean list is empty
            self.cleantiles = []
