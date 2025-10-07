# This is necessary to find the main code
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
import atexit

sys.path.insert(1, '../team04')
from qlearningcharacter import QLearningCharacter as Character

with open('training/maps.json', 'r') as f:
    maps = json.load(f)

results = { }

def addMonsters(g: Game, data: None | str | list[list[dict]]):
    if not data:
        return

    if isinstance(data, str):
        data = maps["monsters"][data]
    
    if not data or len(data) == 0:
        return

    for d in data:
        monster = None
        v = d["variant"]
        if v == 0:
            monster = StupidMonster(d["name"], d["avatar"], d["x"], d["y"])
        elif v == 1:
            monster = SelfPreservingMonster(d["name"], d["avatar"], d["x"], d["y"], d["range"])
        
        if monster:
            g.add_monster(monster)
def generateGame(index) -> Game:
    data = maps[index]
    
    if data["train"] == False:
        results[data['name']] = "Not Played"
        return None

    if data['name'] not in results:
        results[data['name']] = { }

    g = Game.fromfile('map.txt')
    
    addMonsters(g, data["monsters"])
    
    g.add_character(Character("me", 'C', 0, 0, data['name'], results[data['name']]))

    return g

g = None
random.seed()

iterations = 50

def on_close():
    print(iterations, *results.items(), sep='\n')

atexit.register(on_close)

while iterations > 0:
    iterations -= 1
    for index in range(len(maps)):
        # Create the game
        g = generateGame(index)

        # Run!
        if g:
            g.go(True)
            if g.world.time <= 0:
                wrld = SensedWorld.from_world(g.world)
                cl: list[Character]
                for cl in g.world.characters.values():
                    for c in cl:
                        c.done(wrld)