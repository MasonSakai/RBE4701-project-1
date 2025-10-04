# This is necessary to find the main code
from io import TextIOWrapper
import sys
sys.path.insert(0, '../bomberman')
# Import necessary stuff
from entity import BombEntity, CharacterEntity, ExplosionEntity, MonsterEntity
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
    w_bomb_danger: float = 0
    w_bomb_potential: float = 0
    weight_file: TextIOWrapper = None

    def __init__(self, name, avatar, x, y): #, recording_file_idents: list[str]
        super().__init__(name, avatar, x, y)
        
        try: # Load weights from file
            with open("QLearningWeights.txt", 'r') as wfile:
                self.w_goal = float(wfile.readline())
                self.w_stupid = float(wfile.readline())
                self.w_smart = float(wfile.readline())
                self.w_bomb_danger = float(wfile.readline())
                self.w_bomb_potential = float(wfile.readline())
            print("Loaded weights: ", self.w_goal, ", ", self.w_stupid, ", ", self.w_smart, ", ", self.w_bomb_danger, ", ", self.w_bomb_potential, sep='')
        except Exception as e:
            print("Failed to read weights:", e)
            
        self.weight_file = open("QLearningWeights.txt", 'w') # opened here due to garbage collection, no try-except because we don't want to proceed if this fails
        # This does clear the file for the lifetime of the character. It should be written to at the end no matter what, but I'm still a bit worried about that
    
    def __del__(self):
        try: # Save weights to file
            self.weight_file.writelines([
                str(self.w_goal), '\n',
                str(self.w_stupid), '\n',
                str(self.w_smart), '\n',
                str(self.w_bomb_danger), '\n', 
                str(self.w_bomb_potential)   
            ])
            self.weight_file.close()
            print("Successfully saved weights")
        except Exception as e:
            print("Failed to write weights:", e)

    

    def dist(self, a: tuple[int, int], b: tuple[int, int]) -> float:
        dx = b[0] - a[0]
        dy = b[1] - a[1]
        return math.sqrt(dx * dx + dy * dy)
    
    def calculate_bomb_danger(self, wrld: SensedWorld, me: CharacterEntity) -> float:
        """
        Calculates the danger feature based on the agent's proximity to active bombs.
        The feature is more negative the closer the agent is to a bomb.
        """
        feat_bomb_danger = 0.0
        all_bombs = wrld.bombs.values()
        if all_bombs:
            min_dist_to_bomb = float('inf')
            for bomb in all_bombs:
                dist_b = self.dist((me.x, me.y), (bomb.x, bomb.y))
                if dist_b < min_dist_to_bomb:
                    min_dist_to_bomb = dist_b
            # Use inverse distance as a penalty. The +1 prevents division by zero.
            feat_bomb_danger = -1.0 / (min_dist_to_bomb + 1.0)
        return feat_bomb_danger

    def calculate_bomb_potential(self, node: WorldStateTree, me: CharacterEntity, dist_goal: float) -> float:
        wrld = node.world
        goal_pos = wrld.exitcell

        if dist_goal != float("inf"):
            return 0.0

        # If no bombs are on the field and if a goal exists
        if node.find_bomb(me) is None and goal_pos:
            wall_to_check_x, wall_to_check_y = me.x, me.y + 1
            if 0 <= wall_to_check_x < wrld.width() and 0 <= wall_to_check_y < wrld.height() and wrld.wall_at(wall_to_check_x, wall_to_check_y):
                dist_me_to_goal = self.dist((me.x, me.y), goal_pos)
                dist_wall_to_goal = self.dist((wall_to_check_x, wall_to_check_y), goal_pos)
                if dist_wall_to_goal < dist_me_to_goal:
                    return 10
        return 0.0

    def evaluate_state(self, node: WorldStateTree) -> float:

        wrld = node.world
        me = wrld.me(self)

        dist_goal, _ = self.find_path(wrld)          
        goal_x, goal_y = wrld.exitcell 
        me_x, me_y = me.x, me.y
        if dist_goal == float("inf"):
            dist_goal = max(abs(goal_x - me_x), abs(goal_y - me_y))
        goal_feat = -dist_goal

        max_range = max(wrld.width(), wrld.height(), 1)

        monster_component = 0.0
        feature_m_stupid = 0.0 
        feature_m_smart = 0.0 

        
        for actor in node.actors:
            if isinstance(actor, CharacterEntity):
                continue
            
            (mname, p_smart, _) = actor
            monster = node.get_monster_with_name(wrld, mname)
            
            dx = monster.x - me.x
            dy = monster.y - me.y
            dist_m = math.sqrt(dx * dx + dy * dy)
            neg_dist_m = 1 / (1 + dist_m)
            
            feature_m_stupid += (1.0 - p_smart) * neg_dist_m
            feature_m_smart += p_smart * neg_dist_m

        monster_component = self.w_stupid * feature_m_stupid + self.w_smart * feature_m_smart

        feat_bomb_danger = self.calculate_bomb_danger(wrld, me)
        feat_bomb_potential = self.calculate_bomb_potential(node, me, dist_goal)

        q_value = (self.w_goal * goal_feat) + monster_component + self.w_bomb_danger * feat_bomb_danger + self.w_bomb_potential * feat_bomb_potential 
        
        return q_value

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
                if wrld.empty_at(pos[0] + x, pos[1] + y) or wrld.exit_at(pos[0] + x, pos[1] + y) or wrld.explosion_at(pos[0] + x, pos[1] + y):
                    neighbors.append((pos[0] + x, pos[1] + y))
                elif (x == 0 or y == 0) and wrld.wall_at(pos[0] + x, pos[1] + y):
                    neighbors.append((pos[0] + x, pos[1] + y))
        return neighbors
    
    def find_bombs_for_wall(self, wrld: SensedWorld, x: int, y: int) -> list[BombEntity]:
        bombs = []
        bomb: BombEntity
        for bomb in wrld.bombs.values():
            dx = abs(bomb.x - x)
            dy = abs(bomb.y - y)
            if (dx == 0 or dy == 0) and (dx <= wrld.expl_range or dy <= wrld.expl_range):
                bombs.append(bomb)
        return bomb
                
    
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

                if wrld.wall_at(neighbor[0], neighbor[1]):
                    m = -1
                    for bomb in self.find_bombs_for_wall(wrld, neighbor[0], neighbor[1]):
                        m = max(m, bomb.timer)
                    if m < 0:
                        m = wrld.bomb_time
                    new_cost += m + wrld.expl_duration
                elif (expls := wrld.explosion_at(neighbor[0], neighbor[1])):
                    m = 0
                    expl: ExplosionEntity
                    for expl in expls:
                        m = max(m, expl.timer)
                    new_cost += m

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


# Function needs to stop at a certain depth on the tree. We pass in the tree and the required depth
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

    def q_learning_update(self, node: WorldStateTree, reward: float, alpha=0.5, gamma=0.9):
        wrld = node.world
        me = wrld.me(self)

        q_value = self.evaluate_state(node)

        best_future_q = -float("inf")
        next_nodes = node.fill_single_step()
        if len(next_nodes) == 0:
            best_future_q = 0.0
        else:
            for child in next_nodes:
                q_next = self.evaluate_state(child)
                if q_next > best_future_q:
                    best_future_q = q_next

        if best_future_q == -float("inf"):
            best_future_q = 0.0

        delta = (reward + gamma * best_future_q) - q_value
        new_w_goal, new_w_stupid, new_w_smart, new_w_bomb_danger, new_w_bomb_potential = 0

        new_w_goal += self.w_goal + alpha * delta * goal_feat
        new_w_stupid += self.w_stupid + alpha * delta * feature_m_stupid
        new_w_smart += self.w_smart + alpha * delta * feature_m_smart
        new_w_bomb_danger += self.w_bomb_danger + alpha * delta * feat_bomb_danger
        new_w_bomb_potential += self.w_bomb_potential + alpha * delta * feat_bomb_potential

        return new_w_goal, new_w_stupid, new_w_smart

    
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
        # print(value, best_action)
        reward = 0
        me = wrld.me(self)
        if wrld.exit_at(me.x, me.y): 
            reward = 100
        else:
            reward = value 

        candidate_weights = self.q_learning_update(self.tree, reward)
        # print(candidate_weights)

        self.w_goal, self.w_stupid, self.w_smart = candidate_weights
        if isinstance(best_action, tuple):
            self.move(best_action[0], best_action[1])
        elif best_action == True:
            self.place_bomb()
        else:
            return None
