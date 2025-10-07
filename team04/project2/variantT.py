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

"""
A self-sufficient training variant for training and scoring all other variants
Will cycle through the enemies of all other variants (defined in training/maps.json) automatically for specified number of iterations
Important details are commented
"""

with open('training/maps.json', 'r') as f:
    maps = json.load(f)

results: dict[str, str | dict[str, dict[str, int]]] = { }

# Do we do training?
# If false, will run all variant
do_training = False

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
    
    if do_training and data["train"] == False:
        results[data['name']] = "Not Played"
        return None

    if data['name'] not in results:
        results[data['name']] = { }

    g = Game.fromfile('map.txt')
    
    addMonsters(g, data["monsters"])
    
    g.add_character(Character("me", 'C', 0, 0, data['name'], do_training=do_training, results_data=results[data['name']]))

    return g

g = None
random.seed()

# Number of times to run each variant, set negative to run until ctrl+c
max_iterations = 50
iterations = 0

# Print results on any kind of exit
def on_close():
    print('Iterations Ran', iterations)
    if not do_training: print('Not Training!')
    for name, data in results.items():
        if isinstance(data, str):
            print("{}: {}".format(name, data))
        else:
            successes = 0
            fails = 0
            runs = 0
            for d_list in data.values():
                for k, d in d_list.items():
                    if k == 'me found the exit':
                        successes += d
                        runs += d
                    elif k == 'me killed itself' or 'me was killed by ' in k:
                        fails += d
                        runs += d
                    elif k == 'out of time':
                        runs += d

            print('{}: {} | {} | {} of {}'.format(name, successes, fails, runs - successes - fails, runs))
            if runs > 0:
                print('\t{} | {} | {}'.format(successes / runs, fails / runs, (runs - successes - fails) / runs))
            print(*map(lambda s: '\t' + str(s), data.items()), sep='\n')
atexit.register(on_close)

while iterations != max_iterations:
    iterations += 1
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