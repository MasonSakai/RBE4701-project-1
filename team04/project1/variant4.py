# This is necessary to find the main code
import sys
sys.path.insert(0, '../../bomberman')
sys.path.insert(1, '..')

# Import necessary stuff
import random
from game import Game
from monsters.selfpreserving_monster import SelfPreservingMonster
from frankenstein_part5 import frankenstein5

# TODO This is your code!
sys.path.insert(1, '../team04')
from testcharacter import TestCharacter
from astarcharacter import AStarCharacter
# Create the game
random.seed(330) # TODO Change this if you want different random choices
g = Game.fromfile('map.txt')
g.add_monster(SelfPreservingMonster("aggressive", # name
                                    "A",          # avatar
                                    7, 13,        # position
                                    2             # detection range
))

# TODO Add your character
g.add_character(frankenstein5("me", # name
                              "C",  # avatar
                              0, 0  # position
))

# Run!
g.go()
