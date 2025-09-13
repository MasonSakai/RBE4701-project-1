import sys
from typing import Any
sys.path.insert(0, '../bomberman')
from world import World
from sensed_world import SensedWorld
from entity import CharacterEntity, MonsterEntity, BombEntity, AIEntity, MovableEntity, PositionalEntity, TimedEntity, OwnedEntity

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
        if x < 0 or x >= self.world.width() or y < 0 or y >= self.world.height():
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
    
    def is_in_range(self, x: int, y: int, rad: int) -> CharacterEntity | None:
        closest = None
        distance = rad + 1

        for dx in range(-rad, rad + 1, 1):
            if (x + dx) >= 0 and (x + dx) < self.world.width():
                for dy in range(-rad, rad + 1, 1):
                    if max(dx, dy) < distance and (y + dy) >= 0 and (y + dy) < self.world.height():
                        chars = self.world.characters_at(x + dx, y + dy)
                        if chars:
                            closest = chars[0]
                            distance = max(dx, dy)
            
        return closest

    def find_bomb(self, player: CharacterEntity) -> bool:
        """
        Will attempt to find a bomb owned by a player
        """
        for x in range(self.world.width()):
            for y in range(self.world.height()):
                bomb: BombEntity = self.world.bomb_at(x, y)
                if bomb is not None and not bomb.expired() and (player is None or bomb.owner.name == player.name):
                    return True
        return False


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

            if not self.find_bomb(player):
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
                    dx = in_range.x - monster.x
                    dy = in_range.y - monster.y
                    world = SensedWorld.from_world(self.world)
                    WorldStateTree.get_monster_at(world, monster.name, monster.x, monster.y).move(dx, dy)
                    self.child_states.append(WorldStateTree(self, world))

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
    


    def fill_single_step(self):
        """
        Fills the world state tree via DFS until the next run state
        """
        stack = self.get_next().copy()
        while len(stack) > 0:
            state = stack.pop()
            if not state.is_run_state():
                stack.extend(state.get_next())

    
    def check_timed_entities(listA: dict[Any, PositionalEntity | TimedEntity | OwnedEntity], listB: dict[Any, PositionalEntity | TimedEntity | OwnedEntity]) -> bool:
        matched_inds = set()
        for keyA, valA in listA.items():
            if valA.expired():
                continue

            if keyA in listB:
                valB = listB[keyA]
                if valA.timer != valB.timer:
                    return False
                if valA.owner.name != valB.owner.name:
                    return False
                if valA.x != valB.x:
                    return False
                if valA.y != valB.y:
                    return False
                matched_inds.add(keyA)
        
        for keyB, valB in listB.items():
            if valB.expired():
                continue
            if keyB in matched_inds:
                continue
            return False
        
        return True

    def check_ai_entities(listA: dict[Any, list[AIEntity | MovableEntity]], listB: dict[Any, list[AIEntity | MovableEntity]]) -> bool:
        matched_inds = set()
        for keyA, valA in listA.items():
            valA = valA[0]
            if keyA in listB:
                valB = listB[keyA][0]
                if valA.name != valB.name:
                    return False
                if valA.x != valB.x:
                    return False
                if valA.y != valB.y:
                    return False
                if valA.dx != valB.dx:
                    return False
                if valA.dy != valB.dy:
                    return False
                matched_inds.add(keyA)
        
        for keyB, valB in listB.items():
            if keyB in matched_inds:
                continue
            return False
        
        return True

    def are_equal(wrldA: World, wrldB: World) -> bool:
        """
        Checks if two worlds are equal
        """
        
        if wrldA.width() != wrldB.width(): # check size
            return False
        if wrldA.height() != wrldB.height(): # check size
            return False
        
        for x in range(wrldA.width()):
            for y in range(wrldA.height()):
                if wrldA.wall_at(x, y) != wrldB.wall_at(x, y): # check walls
                    return False
                if wrldA.exit_at(x, y) != wrldB.exit_at(x, y): # check exits
                    return False
                
        if not WorldStateTree.check_timed_entities(wrldA.bombs, wrldB.bombs):
            return False
        if not WorldStateTree.check_timed_entities(wrldA.explosions, wrldB.explosions):
            return False
        
        if not WorldStateTree.check_ai_entities(wrldA.characters, wrldB.characters):
            return False
        if not WorldStateTree.check_ai_entities(wrldA.monsters, wrldB.monsters):
            return False


        return True

    def is_run_state(self) -> bool:
        """
        Is this a state where the world was ticked?
        """
        return self.actor_turn == 0
    def has_children(self) -> bool:
        return self.child_states != None

    def is_repeat_state(self, other: 'WorldStateTree' = None) -> bool:
        """
        Checks if the current state is a repeat to an earlier state\n
        If given another WorldStateTree, will check up their state tree 
        """
        if not self.is_run_state:
            raise Exception('Cannot run is_repeat_state on non-run state!')

        if other is None:
            other = self.parent_state
        
        while other is not None:
            if other.is_run_state() and WorldStateTree.are_equal(self.world, other.world):
                return True
            other = other.parent_state

        return False

    def get_progressed_state(self, world: World) -> 'WorldStateTree':
        """
        Returns the immediate (is_run_state) child matching our new world state
        """
        if not self.is_run_state:
            raise Exception('Cannot run is_repeat_state on non-run state!')
        
        if self.child_states is None:
            return None

        stack = self.child_states.copy()
        while len(stack) > 0:
            state = stack.pop()
            if state.is_run_state():
                if WorldStateTree.are_equal(state.world, world):
                    return state
            elif state.child_states is not None:
                stack.extend(state.child_states)
        
        return None

        



