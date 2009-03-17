#!/usr/bin/python
# vim: set expandtab tabstop=4 shiftwidth=4:
# $Id$
#
# Eschalon Book 1 Character Editor
# Copyright (C) 2008, 2009 CJ Kucera
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

import getopt, sys
from eschalonb1.map import Map
from eschalonb1.mapcli import MapCLI
from eschalonb1.preferences import Prefs

def usage(full=False):
    #progname = sys.argv[0]
    progname = 'eschalon_b1_char.py'
    print
    print "To launch the GUI:"
    print "\t%s [<charfile>]" % (progname)
    print
    print "To list character attributes on the console:"
    print "\t%s -l [-s <all|stats|avatar|magic|equip|inv>] [-u] <charfile>" % (progname)
    print "\t%s --list [--show=<all|stats|...>] [--unknowns] <charfile>" % (progname)
    print
    print "To manipulate character data from the console:"
    print "\t%s [--set-gold=<num>] [--rm-disease]" % (progname)
    print "\t\t[--set-mana-max=<num>] [--set-mana-cur=<num>]"
    print "\t\t[--set-hp-max=<num>] [--set-hp-cur=<num>] <charfile>"
    print
    if (full):
        print "Wherever <charfile> appears in the above, you should specify the"
        print "location of the file named 'char' inside your savegame folder."
        print
        print "By default, the application will launch the GUI.  Note that"
        print "specifying a character file is optional when you're launching"
        print "the GUI, but required when using any of the other commandline"
        print "options."
        print
        print "For a textual representation of the charfile instead, use -l or"
        print "--list."
        print
        print "To only show a listing of specific character information, use"
        print "the -s or --show option, which can be specified more than once."
        print "For instance, to show both the basic character stats and the"
        print "character's magic information, you would use:"
        print
        print "\t%s -l -s stats -s magic <charfile>" % (progname)
        print "\tor"
        print "\t%s --list --show=stats --show=magic <charfile>" % (progname)
        print
        print "Currently, the following arguments are valid for --show:"
        print
        print "\tall - Show all information (this is the default)"
        print "\tstats - Base Character Statistics"
        print "\tavatar - Avatar information"
        print "\tmagic - Magic information"
        print "\tequip - Equipment information (armor, weapons, etc)"
        print "\tinv - Inventory listings (including \"ready\" slots)"
        print
        print "When being shown the listing, specify -u or --unknowns to"
        print "also show unknown data from the charfile."
        print
        print "There are a few options to set your character's gold level, hitpoints,"
        print "mana, and remove any diseases.  These should be fairly self-explanatory."
        print "Note that equipped items on your character may increase your effective"
        print "HP or MP, so even if this util reports that you're at your maximum HP,"
        print "you may find that you're slightly off when you enter the game.  Using the"
        print "--set-hp-max or --set-mana-max options will also bring your current HP or"
        print "MP up to the new Max level."
        print
        print "Additionally, you may use -h or --help to view this message"
    else:
        print "To get a full help listing, with text descriptions of all the options:"
        print "\t%s -h" % (progname)
        print "\t%s --help" % (progname)
    print
    sys.exit(2)

def main(argv=None):

    # Argument var defaults
    options = {
            'gui': True,
            'list': False,
            'listoptions' : {
                'all': False,
                'squares': False,
                'scripts': False,
                'txtmap': False
                },
            'unknowns': False,
            'filename' : None
            }

    # Parse the args
    if argv is None:
        argv = sys.argv
    try:
        opts, args = getopt.getopt(argv[1:],
                'hls:u',
                ['help',
                 'list',
                 'show=',
                 'unknowns'])
    except getopt.GetoptError, err:
        print str(err)
        usage()

    # now check to see if they're proper
    for o, a in opts:
        if (o in ('-h', '--help')):
            usage(True)
        elif (o in ('-l', '--list')):
            options['gui'] = False
            options['list'] = True
        elif (o in ('-s', '--show')):
            if (a == 'all' or a == ''):
                options['listoptions']['all'] = True
            elif (a == 'squares'):
                options['listoptions']['squares'] = True
            elif (a == 'scripts'):
                options['listoptions']['scripts'] = True
            elif (a == 'txtmap'):
                options['listoptions']['txtmap'] = True
            else:
                usage()
        elif (o in ('-u', '--unknowns')):
            options['unknowns'] = True
        else:
            assert False, 'unhandled option'

    # Set our filename, if we have it
    if (len(args) > 0):
        options['filename'] = args[0]

    # Make sure we have a filename still
    if (not options['gui'] and options['filename'] == None):
        print "A filename is required"
        usage()
    
    # Now load up the appropriate class
    if (options['gui']):
        # We're waiting until now to import, so people just using CLI don't need
        # PyGTK installed, etc).  Not that this program follows PEP8-recommended
        # practices anyway, but I *am* aware that doing this is discouraged.
        from eschalonb1.mapgui import MapGUI
        prog = MapGUI(options, Prefs())
    else:
        prog = MapCLI(options, Prefs())

    # ... and run it
    return prog.run()

if __name__ == '__main__':
    sys.exit(main())
