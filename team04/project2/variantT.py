# This is necessary to find the main code
from io import TextIOWrapper
import sys

sys.path.insert(0, '../../bomberman')
sys.path.insert(1, '..')

# Import necessary stuff
import random
from game import Game
from monsters.stupid_monster import StupidMonster
from monsters.selfpreserving_monster import SelfPreservingMonster
from sensed_world import SensedWorld
import json
import os
import atexit

sys.path.insert(1, '../team04')
from qlearningcharacter import QLearningCharacter as Character

with open('training/maps.json', 'r') as f:
    maps = json.load(f)

log_file: TextIOWrapper = None

def extract_weights(data: list[dict]) -> list[float]:
    def extract_weight(d: dict) -> float:
        if 'weight' in d:
            return d['weight']
        return 1

    return list(map(extract_weight, data))

def addMonsters(g: Game, data: None | str | list[list[dict]]):
    if not data:
        return

    if isinstance(data, str):
        data = maps["monsters"][data]
    
    if not data or len(data) == 0:
        return

    data = random.choices(data, weights=extract_weights(data), k=1)[0]

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

    d = random.choices(data, weights=extract_weights(data), k=1)[0]

    g.add_character(Character(d["name"], d["avatar"], d["x"], d["y"], log_file))
def generateGame() -> Game:
    data = maps["maps"]
    mapData = random.choices(data, weights=extract_weights(data), k=1)[0]

    g = Game.fromfile('training/maps/' + mapData["file"])
    
    addMonsters(g, mapData["monsters"])
    addCharacter(g, mapData["characters"])

    return g

g = None
random.seed()
while True:
    name = "training/logs/{}.txt".format(hex(random.getrandbits(32)))
    if not os.path.exists(name):
        log_file = open(name, 'w')
        break

def on_close():
    log_file.close()

atexit.register(on_close)

i = 50
log_file.write('Starting iterations: {}\n'.format(i))

while i > 0:
    log_file.writelines([ str(random.getstate()), '\n' ])

    # Create the game
    g = generateGame()

    # Run!
    g.go(True)
    if g.world.time <= 0:
        wrld = SensedWorld.from_world(g.world)
        cl: list[Character]
        for cl in g.world.characters.values():
            for c in cl:
                c.done(wrld)


    print(*g.events, sep=', ')
    log_file.write('events: ')
    log_file.writelines(map(lambda e: '{}, '.format(str(e)), g.world.events))
    log_file.write('\n  ----\n')

    i -= 1