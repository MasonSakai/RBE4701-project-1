# This is necessary to find the main code
import sys
sys.path.insert(0, '../bomberman')
# Import necessary stuff
from entity import CharacterEntity
from colorama import Fore, Back
from worldstate import WorldStateTree
from math import inf
from sensed_world import SensedWorld
import math
from queue import PriorityQueue

class QLearningCharacter(CharacterEntity):
    tree: WorldStateTree = None
    w_goal: float = 0
    w_stupid: float = 0
    w_smart: float = 0

    

# Function needs to stop at a certain depth on the tree. We pass in the tree and the required depth
    def dist(self, a: tuple[int, int], b: tuple[int, int]) -> float:
        dx = b[0] - a[0]
        dy = b[1] - a[1]
        return math.sqrt(dx * dx + dy * dy)

    def find_monster(self, wrld: SensedWorld):
       monster_positions = []

    # Loop over the whole board
       for m_x in range(wrld.width()):
        for m_y in range(wrld.height()):
            monsters = wrld.monsters_at(m_x,m_y)
            if monsters:
                monster_positions.append((m_x, m_y))

       return monster_positions

    def evaluate_state(self, node: WorldStateTree) -> float:

        wrld = node.world
        me = wrld.me(self)
        monsters=self.find_monster(wrld)
        distance, _ = self.find_path(wrld)

        for m_x, m_y in monsters:
          if max(abs(me.x - m_x), abs(me.y - m_y)) <= 1:
              return -1000     
          
        if distance == float("inf"):
              return -1000
        # print(-distance)
        return -distance

    def get_goals(self, wrld: SensedWorld) -> set[tuple[int, int]]:
            """
            Return a set of all goal positions (x, y) in the world.
            """
            goals = set()
            for x in range(wrld.width()):
                for y in range(wrld.height()):
                    if wrld.exit_at(x, y): 
                        goals.add((x, y))
            return goals
    
    def get_neighbors(self, wrld: SensedWorld, pos: tuple[int, int]) -> list[tuple[int, int]]:
        neighbors = list()
        for x in range(-1, 2, 1):
            if pos[0] + x < 0 or pos[0] + x >= wrld.width():
                continue
            for y in range(-1, 2, 1):
                if pos[1] + y < 0 or pos[1] + y >= wrld.height():
                    continue
                if wrld.empty_at(pos[0] + x, pos[1] + y) or wrld.exit_at(pos[0] + x, pos[1] + y):
                    neighbors.append((pos[0] + x, pos[1] + y))
        return neighbors
    
    def find_path(self, wrld: SensedWorld):
        start_pos = (wrld.me(self).x, wrld.me(self).y)

        queue = PriorityQueue()
        came_from = {start_pos: None}
        cost_so_far = {start_pos: 0}

        goals = self.get_goals(wrld)
        found_goal = None

        queue.put((0, start_pos))

        while not queue.empty():
            _, pos = queue.get(False)

            if pos in goals:
                found_goal = pos
                break

            for neighbor in self.get_neighbors(wrld, pos):
                new_cost = cost_so_far[pos] + 1
                if neighbor not in cost_so_far or new_cost < cost_so_far[neighbor]:
                    cost_so_far[neighbor] = new_cost
                    priority = new_cost + min(self.dist(g, neighbor) for g in goals)
                    queue.put((priority, neighbor))
                    came_from[neighbor] = pos

        if not found_goal:
            return float("inf"), None

        path = []
        pos = found_goal
        while pos is not None:
            path.append(pos)
            pos = came_from[pos]
        path.reverse() 

        if len(path) > 1:
            first_step = path[1]  
        else:
            first_step = None

        return cost_so_far[found_goal], first_step


    def Expectimax(self, generatedNode: WorldStateTree, depth=3, alpha=-1000, beta=100):
        # Handle character events first
        if generatedNode.character_event == True:
            # print("I'm giving a high cost", depth)
            return 100, None
        elif generatedNode.character_event == False:
            return -1000, None

        if depth == 0:
            return self.evaluate_state(generatedNode), None

        if generatedNode.is_player_turn():
            best_value = float('-inf')
            best_action = None
            for (child, action) in generatedNode.get_next():
                value, _ = self.Expectimax(child, depth - 1, alpha, beta)
                value -= 1 
                if value > best_value:
                    best_value = value
                    best_action = action
                if best_value >= beta:
                    #print("Playr branch pruned", alpha, beta, best_value)
                    return best_value, best_action
                alpha = max(alpha, best_value)
            return best_value, best_action

        else:
            v = 0
            p_i = 1
            v_i = 0
            for (child, p) in generatedNode.get_next():
                value, _ = self.Expectimax(child, depth-1, alpha, beta)
                v += p * value
                p_i -= p
                v_i = v + p_i * beta
                if (p_i < -1e-5):
                    print(p_i)
                    print(generatedNode.get_next(True))
                    print(sum(map(lambda p: p[1], generatedNode.get_next())))
                    raise Exception("probability sum error")
                if v_i < alpha:
                    return v_i, None
                beta = min(beta, v_i)
            return v, None


    
    def do(self, wrld):
        if self.tree:
            self.tree.fill_single_step()
            self.tree = self.tree.get_progressed_state(wrld)
            if self.tree:
                self.tree.prune_parents()
        if not self.tree:
            print("Tree Init")
            self.tree = WorldStateTree.CreateTree(self, wrld)
        depth_limit = 4
        value, best_action = self.Expectimax(self.tree, depth=depth_limit)
        print(value, best_action)
        if isinstance(best_action, tuple):
            self.move(best_action[0], best_action[1])
        elif best_action == True:
            self.place_bomb()
        else:
            return None
