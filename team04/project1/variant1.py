# This is necessary to find the main code
import sys
sys.path.insert(0, '../../bomberman')
sys.path.insert(1, '..')

# Import necessary stuff
from game import Game

# TODO This is your code!
sys.path.insert(1, '../team04')

# Uncomment this if you want the empty test character
from dlbfscharacter import DLDFSCharacter

# Create the game
g = Game.fromfile('map.txt')

# Uncomment this if you want the test character
g.add_character(DLDFSCharacter("me", # name
                              "C",   # avatar
                              0, 0   # position
))

g.go(1)
