# This is necessary to find the main code
import sys

from sensed_world import SensedWorld
sys.path.insert(0, '../bomberman')
# Import necessary stuff
from entity import CharacterEntity
from world import World
from worldstate import WorldStateTree

class DLDFSCharacter(CharacterEntity):
        
    tree: WorldStateTree = None

    def calculate_tree(self, wrld: World):
        self.tree = WorldStateTree.CreateTree(self, wrld)
        self.tree.fill_single_step()
        sim_world = SensedWorld.from_world(wrld)
        sim_world.me(self).place_bomb()
        (sim_world, _) = sim_world.next()
        
        new_tree = self.tree.get_progressed_state(sim_world)
        print(new_tree)
        print(new_tree.get_next()[0][0].get_next())
        
        if new_tree:
            print(new_tree.is_repeat_state())
        

        


    def do(self, wrld):
        if self.tree:
            self.tree = self.tree.get_progressed_state(wrld)
        if not self.tree:
            print("Tree Init")
            self.tree = WorldStateTree.CreateTree(self, wrld)

        self.tree.fill_single_step()

        wrld.me(self).move(1, 0)
