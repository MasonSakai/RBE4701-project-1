# This is necessary to find the main code
import sys
sys.path.insert(0, '../../bomberman')
sys.path.insert(1, '..')

# Import necessary stuff
import random
from game import Game
from monsters.stupid_monster import StupidMonster
from monsters.selfpreserving_monster import SelfPreservingMonster
import json
import os
import atexit

sys.path.insert(1, '../team04')
from testcharacter import TestCharacter as Character

with open('training/maps.json', 'r') as f:
    maps = json.load(f)

def addMonsters(g: Game, data: None | str | list[list[dict]]):
    if not data:
        return

    if isinstance(data, str):
        data = maps["monsters"][data]
    
    if not data or len(data) == 0:
        return

    data = random.choice(data)

    for d in data:
        monster = None
        v = d["variant"]
        if v == 0:
            monster = StupidMonster(d["name"], d["avatar"], d["x"], d["y"])
        elif v == 1:
            monster = SelfPreservingMonster(d["name"], d["avatar"], d["x"], d["y"], d["range"])
        
        if monster:
            g.add_monster(monster)
def addCharacter(g: Game, data: str | list[dict]):
    if isinstance(data, str):
        data = maps["characters"][data]

    d = random.choice(data)

    g.add_character(Character(d["name"], d["avatar"], d["x"], d["y"]))
def generateGame() -> Game:
    mapData = random.choice(maps["maps"])

    g = Game.fromfile('training/maps/' + mapData["file"])
    
    addMonsters(g, mapData["monsters"])
    addCharacter(g, mapData["characters"])

    return g


random.seed()
log_file = None
while True:
    name = "training/logs/{}.txt".format(hex(random.getrandbits(32)))
    if not os.path.exists(name):
        log_file = open(name, 'w')
        break

def on_close():
    log_file.close()

atexit.register(on_close)

i = 10
log_file.write('Starting iterations: {}\n'.format(i))

while i > 0:
    log_file.writelines([
        str(random.getstate()), '\n',
        'write weights?', '\n'
    ])

    # Create the game
    g = generateGame()

    # Run!
    g.go(True)

    print(*g.events, sep=', ')
    log_file.write('events: ')
    log_file.writelines(map(lambda e: '{}, '.format(str(e)), g.world.events))
    log_file.write('\n  ----\n')

    i -= 1