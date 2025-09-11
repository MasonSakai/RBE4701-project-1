# This is necessary to find the main code
import sys
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
        


    def traverse(self, wrld: World):
        raise Exception("Completed search")
        pass

    def do(self, wrld):
        if not self.tree:
            self.calculate_tree(wrld)

        self.traverse(wrld)
