#!/usr/bin/python
# vim: set expandtab tabstop=4 shiftwidth=4:
# $Id$
#
# Eschalon Book 1 Character Editor
# Copyright (C) 2008 CJ Kucera
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

app_name = 'Eschalon Book 1 Savefile Editor'
version = '0.3.0'
url = 'http://apocalyptech.com/eschalon/'
authors = ['Main Code - CJ Kucera', 'Additional Code / Ideas - WR Goerlich']

__all__ = [ 'app_name', 'version', 'url', 'authors'
        'Savefile', 'Item', 'Unknowns', 'Character', 'MainGUI', 'LoadException',
        'Square', 'Mapscript',
        'attrtable', 'skilltable', 'typetable', 'itemincrtable', 'flagstable', 'spelltable', 'dirtable', 'statustable', 'diseasetable', 'entitytable' ]

# Lookup tables
attrtable = {
        0x01: 'Strength',
        0x02: 'Dexterity',
        0x03: 'Endurance',
        0x04: 'Speed',
        0x05: 'Intelligence',
        0x06: 'Wisdom',
        0x07: 'Perception',
        0x08: 'Concentration'
    }
skilltable = {
        0x01: 'Alchemy',
        0x02: 'Divination',
        0x03: 'Elemental',
        0x04: 'Light Armor',
        0x05: 'Heavy Armor',
        0x06: 'Shields',
        0x07: 'Cartography',
        0x08: 'Dodge',
        0x09: 'Hide in Shadows',
        0x0A: 'Lore',
        0x0B: 'Meditation',
        0x0C: 'Mercantile',
        0x0D: 'Move Silently',
        0x0E: 'Pick Locks',
        0x0F: 'SkullDuggery',
        0x10: 'Spot Hidden',
        0x11: 'Survival',
        0x12: 'Unarmed Combat',
        0x13: 'Bludgeoning Weapons',
        0x14: 'Bows',
        0x15: 'Cleaving Weapons',
        0x16: 'Short Bladed Weapons',
        0x17: 'Swords',
        0x18: 'Thrown Weapons'
    }
typetable = {
        0x00: '(nothing)',
        0x01: 'Weapon',
        0x02: 'Arrow',
        0x03: 'Armor (Helm)',
        0x04: 'Armor (Cloak)',
        0x05: 'Armor (Torso)',
        0x06: 'Armor (Belt)',
        0x07: 'Armor (Gauntlet)',
        0x08: 'Armor (Legs)',
        0x09: 'Armor (Shield)',
        0x0A: 'Armor (Feet)',
        0x0B: 'Amulet',
        0x0C: 'Ring',
        0x0D: 'Magic',
        # 0x0E: Duration field displayed as "Charges" - dynamite of some sort
        0x0F: 'Potion',
        0x10: 'Reagent',
        0x11: 'Reactant',
        0x12: 'Miscellaneous',
        0x13: 'Lock Pick',
        0x14: 'Gem',
        # 0x15: No idea, just comes up n/a
        0x16: 'Consumable',
        0x17: 'Gold',
        0x18: 'n/a',
        0x19: 'Special',
        0x1A: 'Key'
        # Not sure if there's anything beyond here...
    }
itemincrtable = {
        0x01: 'Resist Elements',
        0x02: 'Resist Toxins',
        0x03: 'Resist Magick',
        0x04: 'Resist Disease'
    }
flagstable = {
        0x03: 'Poisoned'
    }
spelltable = {
        0: 'Bless',
        1: 'Cat\'s Eyes',
        2: 'Detox',
        3: 'Divine Heal',
        4: 'Entangle',
        5: 'Fleshboil',
        6: 'Leatherskin',
        7: 'Lore',
        8: 'Poison Spray',
        9: 'Nimbleness',
        10: 'Ogre Strength',
        11: 'Charm',
        12: 'Cure Disease',
        13: 'Enchanted Weapon',
        14: 'Haste',
        15: 'Sunder Flesh',
        16: 'Stoneskin',
        17: 'Turn Undead',
        18: 'Mass Boil',
        19: 'Smite',
        20: 'Dehex',
        21: 'Dancing Lights',
        22: 'Air Shield',
        23: 'Fire Dart',
        24: 'Gravedigger\'s Flame',
        25: 'Element Armor',
        26: 'Reveal Map',
        27: 'Predator Sight',
        28: 'Sonic Blast',
        29: 'Compress Atmosphere',
        30: 'Enkindled Weapon',
        31: 'Deep Freeze',
        32: 'Fireball',
        33: 'Chameleon',
        34: 'Lock Melt',
        35: 'Trapkill',
        36: 'Portal',
        37: 'Invisibility',
        38: 'Supernova'
    }
dirtable = {
        1: 'N',
        2: 'NE',
        3: 'E',
        4: 'SE',
        5: 'S',
        6: 'SW',
        7: 'W',
        8: 'NW'
    }
statustable = {
        0: 'Stunned',
        1: 'Air Shielded',
        2: 'Poisoned',
        3: 'Enchanted Weapon',
        4: 'Entangled',
        5: 'Cat\'s Eyes',
        6: 'Gravedigger\'s Flame',
        7: 'Bless',
        8: 'Haste',
        9: 'Ogre Strength',
        10: 'Invisible',
        11: 'Leatherskin',
        12: 'Nimbleness',
        13: 'Charmed',
        14: 'Reveal Map',
        15: 'Stoneskin',
        16: 'Keensight',
        17: 'Paralyzed',
        18: 'Scared',
        19: 'Enkindled Weapon',
        20: 'Elemental Armor',
        21: 'Chameleon',
        22: 'Predator Sight',
        23: 'Off-Balance',
        24: 'Mana Fortified',
        25: 'Greater Protection'
    }
# Note that diseases are stored as bit flags
diseasetable = {
        0x0200: 'Dungeon Fever',
        0x0400: 'Rusty Knuckles',
        0x0800: 'Eye Fungus',
        0x1000: 'Blister Pox',
        0x2000: 'Insanity Fever',
        0x4000: 'Fleshrot',
        0x8000: 'Cursed'
    }

# Entities
entitytable = {
        0x01: 'Fanged Salamander',
        0x02: 'Bloodsipper',
        0x03: 'Raptor',
        0x04: 'Noximander',
        0x05: 'Fungal Slime',
        0x06: 'Walking Corpse',
        0x07: 'Acid Grubb',
        0x08: 'Timberland Giant',
        0x09: 'Goblin Hacker',
        0x0A: 'Goblin Archer',
        0x0B: 'Goblin Warlord',
        0x0C: 'Hive Drone',
        0x0D: 'Hive Queen',
        0x0E: 'Thug',
        0x0F: 'Dimensional Eye',
        0x10: 'Giant Arachnid',
        0x11: 'Dirachnid',
        0x12: 'Skeleton',
        0x13: 'Goblin Bombthug',
        0x14: 'Poltergeist',
        0x15: 'Barrea Mercenary',
        0x16: 'Taurax',
        0x17: 'Spire Guard',
        0x33: 'Maddock',
        0x34: 'Michael',
        0x35: 'Farwick',
        0x36: 'Abygale',
        0x37: 'Eleanor (crash)',
        0x38: 'Garrett (crash)',
        0x39: 'Porter',
        0x3A: '(crash 3)',
        0x3B: 'Lilith',
        0x3C: 'Town Guard',
        0x3D: 'Gruzz',
        0x3E: 'Gatekeeper',
        0x3F: 'Eeru',
        0x40: 'Erik',
        0x41: 'Darkford Guard',
        0x42: 'Gunther',
        0x43: 'Leurik',
        0x44: 'Vault Master',
        0x45: 'Paul',
        0x46: 'Krista',
        0x47: 'Gamfari',
        0x48: '(your brother) (crash 4)',
        0x49: 'Mary',
        0x4A: 'Vekkar (crash)',
        0x4B: 'Jonathon',
        0x4C: 'Shady Character',
        0x4D: '(crash 6)',
        0x4E: 'Vault Guard',
        0x4F: 'Vidar the Knife',
        0x50: 'Walter',
        0x51: 'Azure Guard',
        0x52: 'Captain Morgan',
        0x53: 'Erubor',
        0x54: 'Shadowmirk Acolyte',
        0x55: 'Phillip',
        0x56: 'Omar',
        0x57: 'Gramuk',
        0x58: 'Shady Character (2)',
        0x5A: '(crash 7)',
        0x5B: 'Sonya',
        0x5C: 'Aaron',
        0x5D: 'Penelope',
        0x5E: 'Siam',
        0x5F: 'William',
        0x60: 'Hesham'
    }
