# This is necessary to find the main code
import sys

from sensed_world import SensedWorld
sys.path.insert(0, '../bomberman')
# Import necessary stuff
from entity import CharacterEntity
from world import World
from worldstate import WorldStateTree

class DLDFSCharacter(CharacterEntity):

    def __init__(self, name, avatar, x, y, actors: list[CharacterEntity | str | tuple[str, int]]):
        CharacterEntity.__init__(self, name, avatar, x, y)
        for i, actor in enumerate(actors):
            if actor is None:
                actors[i] = self
        self.actors = actors
        
    tree: WorldStateTree = None

    def calculate_tree(self, wrld: World):
        self.tree = WorldStateTree.CreateTree(wrld, self.actors)
        self.tree.fill_single_step()
        sim_world = SensedWorld.from_world(wrld)
        sim_world.me(self).place_bomb()
        monster_keys = set()
        for key, monsters in sim_world.monsters.items():
            for i, monster in enumerate(monsters):
                if any(map(lambda a: (a == monster.name) if isinstance(a, str) else ((a[0] == monster.name) if not isinstance(a, CharacterEntity) else False), self.actors)):
                    monster.move(1, 0)
                    monster_keys.add((key, i))
        (sim_world, _) = sim_world.next()
        
        new_tree = self.tree.get_progressed_state(sim_world)
        print(new_tree)
        
        if new_tree:
            print(new_tree.is_repeat_state())
        

        


    def traverse(self, wrld: World):
        raise Exception("Completed search")
        pass

    def do(self, wrld):
        if not self.tree:
            self.calculate_tree(wrld)

        self.traverse(wrld)
