import sys
sys.path.insert(0, '../bomberman')
from world import World
from sensed_world import SensedWorld
from events import Event
from entity import CharacterEntity, MonsterEntity

class WorldStateTree:
    world: SensedWorld
    actor_turn: int
    actors: list[CharacterEntity | str | tuple[str, tuple[int, int], int]]
    parent_state: 'WorldStateTree'
    child_states: list['WorldStateTree']
    state_value = None

    def CreateTree(world: World, actors: list[CharacterEntity | str | tuple[str, int]]):
        """
        Initilization of the search tree\n
        Requries the current world, and the actors to search through
        """
        tree = WorldStateTree(None, world)
        tree.actors = actors
        return tree

    def __init__(self, parent_state: 'WorldStateTree', world: World):
        """
        Creates a sub-node to a parent state and increments the actor turn\n
        Will automatically tick the world state, be sure to check the world's events when actor_turn == 0
        """
        self.parent_state = parent_state
        self.child_states = None

        if parent_state == None:
            self.actor_turn = 0
            self.world = SensedWorld.from_world(world)
        else:
            self.actors = parent_state.actors
            self.world = world
            self.actor_turn = parent_state.actor_turn + 1
            if self.actor_turn >= len(self.actors):
                self.actor_turn = 0
                (self.world, _) = self.world.next()


    def is_safe_pathable(self, x: int, y: int) -> bool:
        """
        Returns true if the position x, y is safe to navigate\n
        This only checks for walls, explosions, and the edge of the map
        """
        if x < 0 or x >= self.world.width() or y < 0 or y > self.world.height():
            return False
        return not self.world.wall_at(x, y) and not self.world.explosion_at(x, y)
    def get_safe_neighbors(self, x: int, y: int) -> list[tuple[int, int]]:
        """
        Gets the safe movements around the position x, y\n
        Returns a list of movements (dx, dy) that pass is_safe_pathable
        """
        neighbors = []
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if self.is_safe_pathable(x + dx, y + dy):
                    neighbors.append((dx, dy))
        return neighbors
    
    def find_monster(self, name: str) -> MonsterEntity | None:
        """
        Will attempt to find a monster based on name
        """
        for x in range(self.world.width()):
            for y in range(self.world.height()):
                monsters = self.world.monsters_at(x, y)
                if monsters is not None:
                    for monster in monsters:
                        if monster.name == name:
                            return monster
        return None
    
    def get_monster_at(world: SensedWorld, name: str, x: int, y: int) -> MonsterEntity:
        """
        Gets the monster at a position from a world. For world state copies
        """
        for monster in world.monsters_at(x, y):
            if monster.name == name:
                return monster
    
    def get_next(self) -> list['WorldStateTree']:
        """
        Gets the child nodes to this world state\n
        Will calculate only when first called, set child_states to None to recalculate 
        """
        if self.child_states:
            return self.child_states
        
        self.child_states = []
        print('Getting Next')

        actor = self.actors[self.actor_turn]
        if isinstance(actor, CharacterEntity): # actor is the player (random + bomb)
            print("Node is player")
            player: CharacterEntity = self.world.me(actor)
            neighbors = self.get_safe_neighbors(player.x, player.y)
            for (dx, dy) in neighbors:
                world = SensedWorld.from_world(self.world)
                world.me(actor).move(dx, dy)
                self.child_states.append(WorldStateTree(self, world))

            world = SensedWorld.from_world(self.world)
            world.me(actor).place_bomb()
            self.child_states.append(WorldStateTree(self, world))

        elif isinstance(actor, str): # actor is random
            print("Node is monster", actor)
            monster: MonsterEntity = self.find_monster(actor)
            if monster == None: # Could not find monster (dead)
                self.child_states.append(WorldStateTree(self, world))
            else:
                neighbors = self.get_safe_neighbors(monster.x, monster.y)
                for (dx, dy) in neighbors: # do random walk
                    if dx == 0 and dy == 0:
                        continue
                    world = SensedWorld.from_world(self.world)
                    WorldStateTree.get_monster_at(world, monster.name, monster.x, monster.y).move(dx, dy)
                    self.child_states.append(WorldStateTree(self, world))

        elif len(actor) == 3: # actor is not purely random
            print("Node is monster", actor[0])
            monster: MonsterEntity = self.find_monster(actor[0])
            if monster == None: # Could not find monster (dead)
                self.child_states.append(WorldStateTree(self, world))
            else:
                in_range = self.is_in_range(monster.x, monster.y, actor[2])
                if in_range: # player to kill
                    pass

                elif monster.dx != 0 and monster.dy != 0 and self.is_safe_pathable(monster.x + monster.dx, monster.y + monster.dy): # can continue walking
                    self.child_states.append(WorldStateTree(self, SensedWorld.from_world(self.world)))
                else: # random direction
                    neighbors = self.get_safe_neighbors(monster.x, monster.y)
                    for (dx, dy) in neighbors: # do random walk
                        if dx == 0 and dy == 0:
                            continue
                        world = SensedWorld.from_world(self.world)
                        WorldStateTree.get_monster_at(world, monster.name, monster.x, monster.y).move(dx, dy)
                        self.child_states.append(WorldStateTree(self, world))

        print('Got {} children states'.format(len(self.child_states)))
        return self.child_states
    
    # Add a method to find which child a particular world state matches?
    # For no recalculating