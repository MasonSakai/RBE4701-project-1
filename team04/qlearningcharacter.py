# This is necessary to find the main code
from io import TextIOWrapper
import random
import sys
sys.path.insert(0, '../bomberman')
# Import necessary stuff
from entity import BombEntity, CharacterEntity, ExplosionEntity, MonsterEntity
from colorama import Fore, Back
from math import inf
from sensed_world import SensedWorld
from world import World
from events import Event
import math
from queue import PriorityQueue

class QLearningCharacter(CharacterEntity):
    w_goal: float = 0
    w_monster: float = 0
    w_bomb_danger: float = 0
    w_bomb_potential: float = 0
    w_explosion_danger: float = 0
    saved_weights = False

    def __init__(self, name, avatar, x, y, log_file: TextIOWrapper):
        super().__init__(name, avatar, x, y)
        
        try: # Load weights from file
            with open("QLearningWeights.txt", 'r') as wfile:
                self.w_goal = float(wfile.readline())
                self.w_monster = float(wfile.readline())
                self.w_bomb_danger = float(wfile.readline())
                self.w_bomb_potential = float(wfile.readline())
                self.w_explosion_danger = float(wfile.readline())
            print("Loaded weights: ", self.w_goal, ", ", self.w_monster, ", ", self.w_bomb_danger, ", ", self.w_bomb_potential, ", ", self.w_explosion_danger, sep='', file=log_file)
        except Exception as e:
            print("Failed to read weights:", e)
    
    def __del__(self):
        self.save_weights()

    def save_weights(self):
        if self.saved_weights:
            return
        
        try: # Save weights to file
            with open("QLearningWeights.txt", 'w') as wfile:
                wfile.writelines([
                    str(self.w_goal), '\n',
                    str(self.w_monster), '\n',
                    str(self.w_bomb_danger), '\n', 
                    str(self.w_bomb_potential), '\n',
                    str(self.w_explosion_danger),
                ])
            print("Successfully saved weights")
            self.saved_weights = True
        except Exception as e:
            print("Failed to write weights:", e)

    def dist(self, a: tuple[int, int], b: tuple[int, int]) -> float:
        dx = b[0] - a[0]
        dy = b[1] - a[1]
        return math.sqrt(dx * dx + dy * dy)
    
    def calculate_bomb_danger(self, wrld: SensedWorld, me: CharacterEntity) -> float:
        feat_bomb_danger = 0.0
        all_bombs = wrld.bombs.values()
        if all_bombs:
            min_dist_to_bomb = float('inf')
            for bomb in all_bombs:
                dist_b = self.dist((me.x, me.y), (bomb.x, bomb.y))
                if dist_b < min_dist_to_bomb:
                    min_dist_to_bomb = dist_b
            feat_bomb_danger = 1.0 / (min_dist_to_bomb + 1.0)
        return feat_bomb_danger

    def out_of_bomb_danger(self, wrld: SensedWorld) -> float:
        me = wrld.me(self)
        if not me:
            me = self

        bomb_position = None
        current_pos = (me.x, me.y)
        for b_x in range(wrld.width()):
            for b_y in range(wrld.height()):
                bomb = wrld.bomb_at(b_x,b_y)
                if bomb:
                    bomb_position = (bomb.x,bomb.y)

        if not bomb_position:
            return 0
        
        danger_value = 0
        directions = [(0, 1),  (0, -1),  (-1, 0),  (1, 0)]
        for dx, dy in directions:
            for step in range(1, 5):  
                new_x = bomb_position[0] + dx * step
                new_y = bomb_position[1] + dy * step
            if current_pos==(new_x,new_y):
                danger_value = 1

        return danger_value

    def calculate_bomb_potential(self, wrld: World, me: CharacterEntity, first_step: tuple[int, int]) -> float:
        
        if first_step is None:
            return 0.0

        if self.find_bomb(wrld, me) is not None:
            return 0.0

        next_step_x, next_step_y = first_step
        if wrld.wall_at(next_step_x, next_step_y):
            return 1
        
        return 0.0
    
    def calculate_goal_feature(self, wrld: SensedWorld, me: CharacterEntity) -> tuple[float, tuple[int, int]]:
        dist_goal, first_step = self.find_path(wrld)
        
        if dist_goal == float("inf"):
            goal_x, goal_y = wrld.exitcell
            me_x, me_y = me.x, me.y
            dist_goal = max(abs(goal_x - me_x), abs(goal_y - me_y))
            
        goal_feat = 1 / (1 + dist_goal)
        return goal_feat, first_step

    def calculate_monster_component(self, wrld: SensedWorld, me: CharacterEntity) -> float:
        closest = float('inf')

        for monsters in wrld.monsters.values():
            for monster in monsters:
                dist_m = self.dist((me.x, me.y), (monster.x, monster.y))
                if dist_m < closest:
                    closest = dist_m
        
        return 1 / (1 + closest)

    def evaluate_state(self, wrld: World) -> float:
        me = wrld.me(self)
        if not me:
            me = self

        goal_feat, first_step = self.calculate_goal_feature(wrld, me)
        feature_monster = self.calculate_monster_component(wrld, me)
        feat_bomb_danger = self.calculate_bomb_danger(wrld, me)
        feat_expl_danger = self.out_of_bomb_danger(wrld)
        feat_bomb_potential = self.calculate_bomb_potential(wrld, me, first_step)
        if feat_expl_danger == None:
            feat_expl_danger = 0
        q_value = self.w_goal * goal_feat + self.w_monster * feature_monster + self.w_bomb_danger * feat_bomb_danger + self.w_bomb_potential * feat_bomb_potential + self.w_explosion_danger * feat_expl_danger
        
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
        return bombs
    
    def find_path(self, wrld: SensedWorld):
        me = wrld.me(self)
        if not me:
            me = self
        start_pos = (me.x, me.y)

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
                elif (expl := wrld.explosion_at(neighbor[0], neighbor[1])):
                    new_cost += expl.timer

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

    def find_bomb(self, wrld: World, char: CharacterEntity) -> BombEntity:
            """
            Will attempt to find a bomb owned by a player
            """
            me = char if char else self
            for bomb in wrld.bombs.values():
                if not bomb.expired() and bomb.owner.name == me.name:
                    return bomb
            return None
        
    def get_actions(self, wrld: World) -> list[tuple[SensedWorld, tuple[int, int] | bool]]:
        def get_safe_neighbors() -> list[tuple[int, int]]:
            """
            Gets the safe movements around the position x, y\n
            Returns a list of movements (dx, dy) that pass is_safe_pathable
            """
            neighbors = []
            for dx in [-1, 0, 1]:
                if (self.x + dx) >= 0 and (self.x + dx) < wrld.width():
                    for dy in [-1, 0, 1]:
                        if (self.y + dy) >= 0 and (self.y + dy) < wrld.height():
                            if not wrld.wall_at(self.x + dx, self.y + dy) and not wrld.explosion_at(self.x + dx, self.y + dy) and not wrld.monsters_at(self.x + dx, self.y + dy):
                                neighbors.append((dx, dy))
            return neighbors
        
        if not SensedWorld.from_world(wrld).me(self):
            return []

        child_states = []

        neighbors = get_safe_neighbors()
        for (dx, dy) in neighbors:
            n_world = SensedWorld.from_world(wrld)
            n_world.me(self).move(dx, dy)
            (n_world, _) = n_world.next()
            child_states.append((n_world, (dx, dy)))

        if not self.find_bomb(wrld, None):
            n_world = SensedWorld.from_world(wrld)
            n_world.me(self).place_bomb()
            (n_world, _) = n_world.next()
            child_states.append((n_world, True))
            
        return child_states

    def get_action(self, wrld: World) -> tuple[float, tuple[int, int] | bool]:
        
        best_action = None
        best_value = float('-inf')
        actions = self.get_actions(wrld)
        random.shuffle(actions)
        for (n_world, action) in actions:
            val = self.evaluate_state(n_world)
            if val > best_value:
                best_action = action
                best_value = val
        return best_value, best_action

    def q_learning_update(self, wrld: World, reward: float, alpha=0.5, gamma=0.9):
        me = wrld.me(self)
        if not me:
            me = self

        print("Qlearning update", reward)

        goal_feat, first_step = self.calculate_goal_feature(wrld, me)
        feature_monster = self.calculate_monster_component(wrld, me)
        feat_bomb_danger = self.calculate_bomb_danger(wrld, me)
        feat_bomb_potential = self.calculate_bomb_potential(wrld, me, first_step)
        feat_expl_danger = self.out_of_bomb_danger(wrld)
        if feat_expl_danger == None:
            feat_expl_danger = 0

        q_value = self.evaluate_state(wrld)
        delta = 0

        next_nodes = self.get_actions(wrld)
        if len(next_nodes) > 0:
            best_future_q = -float("inf")
            for (child, _) in next_nodes:
                q_next = self.evaluate_state(child)
                if q_next > best_future_q:
                    best_future_q = q_next
            delta = (reward + gamma * best_future_q) - q_value
        else:
            delta = reward

        new_w_goal = self.w_goal + alpha * delta * goal_feat
        new_w_monster = self.w_monster + alpha * delta * feature_monster
        new_w_bomb_danger = self.w_bomb_danger + alpha * delta * feat_bomb_danger
        new_w_bomb_potential = self.w_bomb_potential + alpha * delta * feat_bomb_potential
        new_w_explosion_danger = self.w_bomb_potential + alpha * delta * feat_expl_danger

        return new_w_goal, new_w_monster, new_w_bomb_danger, new_w_bomb_potential, new_w_explosion_danger

    def calc_reward(self, wrld: World, v_exmax: float, a_exmax: tuple[int, int] | bool, d_goal: float, p_path: tuple[int, int]) -> float:
        dx = p_path[0] - self.x
        dy = p_path[1] - self.y

        if wrld.wall_at(*p_path):
            return 0.5 if a_exmax == True else -0.2
        elif a_exmax == True:
            return 0
        elif isinstance(a_exmax, tuple):
            return (a_exmax[0] * dx + a_exmax[1] * dy) * 0.3
        else:
            print("Error, a_exmax is", a_exmax, v_exmax)
    
    def do(self, wrld: World):
        value, best_action = self.get_action(wrld)
        (dist, next) = self.find_path(wrld)
        reward = self.calc_reward(wrld, value, best_action, dist, next)
        print(value, best_action, dist, next, reward)

        candidate_weights = self.q_learning_update(wrld, reward)
        # print(candidate_weights)

        self.w_goal, self.w_monster, self.w_bomb_danger, self.w_bomb_potential, self.w_explosion_danger = candidate_weights
        if isinstance(best_action, tuple):
            self.move(best_action[0], best_action[1])
        elif best_action == True:
            self.place_bomb()
        else:
            return
        
    def done(self, wrld: SensedWorld):
        reward = 0
        event: Event
        for event in wrld.events:
            if event.tpe == Event.CHARACTER_FOUND_EXIT and event.character == self:
                reward += 10
            elif event.tpe == Event.CHARACTER_KILLED_BY_MONSTER and event.character == self:
                reward -= 10
            elif event.tpe == Event.BOMB_HIT_CHARACTER and event.other == self:
                reward -= 10
        if wrld.time <= 0:
            reward = -5
        
        self.w_goal, self.w_monster, self.w_bomb_danger, self.w_bomb_potential, self.w_explosion_danger = self.q_learning_update(wrld, reward)

        self.save_weights()
        