import sys
from typing import Any
sys.path.insert(0, '../bomberman')
from world import World
from sensed_world import SensedWorld
from entity import CharacterEntity, MonsterEntity, AIEntity, MovableEntity, PositionalEntity, TimedEntity, OwnedEntity, __sign__
from events import Event

class WorldStateTree:
    world: SensedWorld
    actor_turn: int
    actors: list[CharacterEntity | tuple[str, float, float]]
    parent_state: 'WorldStateTree'
    child_states: list[tuple['WorldStateTree', float | tuple[int, int] | bool]]
    state_value = None

    def CreateTree(character: CharacterEntity, world: World):
        """
        Initilization of the search tree\n
        Requries the current world and the character
        """
        actors = [ ]
        for _, monsters in world.monsters.items():
            for monster in monsters:
                actors.append([monster.name, 0.5, 0.5])
        actors.append(character)
        tree = WorldStateTree(None, world, actors)
        return tree

    def __init__(self, parent_state: 'WorldStateTree', world: World, actors: list[CharacterEntity | tuple[str, float, float]]):
        """
        Creates a sub-node to a parent state and increments the actor turn\n
        Will automatically tick the world state, be sure to check the world's events when actor_turn == 0
        """
        self.parent_state = parent_state
        self.child_states = None
        self.actors = actors

        if parent_state == None:
            self.actor_turn = 0
            self.world = SensedWorld.from_world(world)
        else:
            self.world = world
            self.actor_turn = parent_state.actor_turn + 1
            if self.actor_turn >= len(self.actors):
                self.actor_turn = 0
                (self.world, events) = self.world.next()
                for event in events:
                    if isinstance(event, Event):
                        if (event.tpe == Event.BOMB_HIT_CHARACTER and event.other.name == actors[-1].name) or (event.tpe == Event.CHARACTER_KILLED_BY_MONSTER and event.character.name == actors[-1].name):
                            self.child_states = []
                            self.actors.pop(0)
                        elif event.tpe == Event.BOMB_HIT_MONSTER:
                            for i in range(1, len(self.actors)):
                                if self.actors[i][0] == event.other.name:
                                    self.actors.pop(i)
                                    break

    def get_safe_neighbors(self, x: int, y: int) -> list[tuple[int, int]]:
        """
        Gets the safe movements around the position x, y\n
        Returns a list of movements (dx, dy) that pass is_safe_pathable
        """
        neighbors = []
        for dx in [-1, 0, 1]:
            if (x + dx) >= 0 and (x + dx) < self.world.width():
                for dy in [-1, 0, 1]:
                    if (y + dy) >= 0 and (y + dy) < self.world.height():
                        if not self.world.wall_at(x + dx, y + dy) and not self.world.explosion_at(x + dx, y + dy) and not self.world.monsters_at(x + dx, y + dy):
                            neighbors.append((dx, dy))
        return neighbors
    
    def must_change_direction(self, ent: MovableEntity) -> bool:
        # Get next desired position
        (nx, ny) = ent.nextpos()
        # If next pos is out of bounds, must change direction
        if ((nx < 0) or (nx >= self.world.width()) or
            (ny < 0) or (ny >= self.world.height())):
            return True
        # If these cells are an explosion, a wall, or a monster, go away
        return (self.world.explosion_at(nx, ny) or
                self.world.wall_at(nx, ny) or
                self.world.monsters_at(nx, ny) or
                self.world.exit_at(nx, ny))
    def random_monster_neighbors(self, x: int, y: int):
        neighbors = []
        for dx in [-1, 0, 1]:
            if (x + dx) >= 0 and (x + dx) < self.world.width():
                for dy in [-1, 0, 1]:
                    if (y + dy) >= 0 and (y + dy) < self.world.height():
                        if not self.world.wall_at(x + dx, y + dy):
                            neighbors.append((dx, dy))
        return neighbors
    def safe_monster_neighbors(self, x: int, y: int):
        neighbors = []
        for dx in [-1, 0, 1]:
            if (x + dx) >= 0 and (x + dx) < self.world.width():
                for dy in [-1, 0, 1]:
                    if (y + dy) >= 0 and (y + dy) < self.world.height():
                        if self.world.exit_at(x + dx, y + dy) or self.world.empty_at(x + dx, y + dy):
                            neighbors.append((dx, dy))
        return neighbors
    
    def look_for_character(self, x: int, y: int, rad: int) -> tuple[bool, int, int]:
        for dx in range(-rad, rad+1):
            # Avoid out-of-bounds access
            if ((x + dx >= 0) and (x + dx < self.world.width())):
                for dy in range(-rad, rad+1):
                    # Avoid out-of-bounds access
                    if ((y + dy >= 0) and (y + dy < self.world.height())):
                        # Is a character at this position?
                        if (self.world.characters_at(x + dx, y + dy)):
                            return (True, dx, dy)
        # Nothing found
        return (False, 0, 0)
    def find_bomb(self, player: CharacterEntity) -> bool:
        """
        Will attempt to find a bomb owned by a player
        """
        for bomb in self.world.bombs.values():
            if not bomb.expired() and (player is None or bomb.owner.name == player.name):
                return True
        return False

    def get_monster_with_name(world: World, name: str) -> MonsterEntity:
        for _, monsters in world.monsters.items():
            for monster in monsters:
                if monster.name == name:
                    return monster
        return None

    def get_next(self) -> list[tuple['WorldStateTree', float | tuple[int, int] | bool]]:
        """
        Gets the child nodes to this world state\n
        Will calculate only when first called, set child_states to None to recalculate 
        """
        if self.has_children():
            return self.child_states
        
        self.child_states = []

        actor = self.actors[self.actor_turn]
        if isinstance(actor, CharacterEntity): # actor is the player (random + bomb)
            player: CharacterEntity = self.world.me(actor)
            neighbors = self.get_safe_neighbors(player.x, player.y)
            for (dx, dy) in neighbors:
                n_world = SensedWorld.from_world(self.world)
                n_world.me(actor).move(dx, dy)
                self.child_states.append((WorldStateTree(self, n_world, self.actors.copy()), (dx, dy)))

            if not self.find_bomb(player):
                n_world = SensedWorld.from_world(self.world)
                n_world.me(actor).place_bomb()
                self.child_states.append((WorldStateTree(self, n_world, self.actors.copy()), True))
                
            return self.child_states

        else:
            (mname, p_smart, p_r2) = actor
            monster: MonsterEntity = WorldStateTree.get_monster_with_name(self.world, mname)
            neighbors = self.random_monster_neighbors(monster.x, monster.y)
            safe_neighbors = self.safe_monster_neighbors(monster.x, monster.y)
            (has_t2, dx_t2, dy_t2) = self.look_for_character(monster.x, monster.y, 2)
            (has_t1, dx_t1, dy_t1) = self.look_for_character(monster.x, monster.y, 1)
            smart_change = self.must_change_direction(monster)

            for (dx, dy) in neighbors:
                actors_data = self.actors.copy()

                p = 0
                p_r = 1 / len(neighbors)
                
                if p_smart == 0: # Purely random
                    p = p_r
                else: # mix of smart and random
                    is_natural = dx == monster.dx and dy == monster.dy
                    p_s = 0
                    p_sr = 1 / len(safe_neighbors)

                    np_smart = p_smart
                    np_r2 = p_r2

                    if not smart_change and (has_t1 or has_t2): # Not random and has target
                        if (has_t2 and __sign__(dx_t2) == dx and __sign__(dy_t2) == dy) or (not has_t2 and is_natural):
                            p_s += p_r2
                            if has_t2: # increase probability of range 2
                                np_r2 = min(1, np_r2 * 1.1)

                        if (has_t1 and dx_t1 == dx and dy_t1 == dy) or (not has_t1 and is_natural):
                            p_s += (1 - p_r2)
                            if has_t1: # decrease probability of range 2
                                np_r2 = np_r2 / 1.1
                    
                    elif smart_change or (dx == 0 and dy == 0): # random safe
                        if any(map(lambda p: p[0] == dx and p[1] == dy, safe_neighbors)): # is a safe neighbor
                            p_s = p_sr
                        else: # stuck
                            p_s = 1 if (dx == 0 and dy == 0) else 0

                    else: # natural movement
                        if is_natural:
                            p_s = 1
                        np_smart = 0 if not is_natural else min(1, p_smart * 1.1) # increase if natural, zero if random
                    

                    p = p_r * (1 - p_smart) + p_s * p_smart
                    actors_data[self.actor_turn] = (mname, np_smart, np_r2)
                
                if p == 0:
                    continue
                n_world = SensedWorld.from_world(self.world)
                WorldStateTree.get_monster_with_name(n_world, mname).move(dx, dy)
                self.child_states.append((WorldStateTree(self, n_world, actors_data), p))
        
            self.child_states = list(sorted(self.child_states, key=lambda s: s[1]))
            return self.child_states
    


    def fill_single_step(self):
        """
        Fills the world state tree via DFS until the next run state
        """
        stack = self.get_next().copy()
        while len(stack) > 0:
            state = stack.pop()[0]
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
            return False
        
        for keyB, valB in listB.items():
            if valB.expired():
                continue
            if keyB in matched_inds:
                continue
            return False
        
        return True

    def check_ai_entities(listA: dict[Any, list[AIEntity | MovableEntity]], listB: dict[Any, list[AIEntity | MovableEntity]]) -> bool:
        def check_entity(valA):
            for valsB in listB.values():
                for valB in valsB:
                    if valA.name == valB.name and valA.x == valB.x and valA.y == valB.y: #  and valA.dx == valB.dx and valA.dy == valB.dy:
                        return True
            return False

        matched_names = set()
        for valsA in listA.values():
            for valA in valsA:
                if check_entity(valA):
                    matched_names.add(valA.name)
                else:
                    return False
        
        for valsB in listB.values():
            for valB in valsB:
                if valB.name not in matched_names:
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
    def is_player_turn(self) -> bool:
        return isinstance(self.actors[self.actor_turn], CharacterEntity)

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
            state = stack.pop()[0]
            if state.is_run_state():
                if WorldStateTree.are_equal(state.world, world):
                    return state
            elif state.has_children():
                stack.extend(state.child_states)
        
        return None

        



