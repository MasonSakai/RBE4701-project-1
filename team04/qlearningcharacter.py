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
import time

class QLearningCharacter(CharacterEntity):
    w_goal: float = 10
    w_monster: float = -5
    w_bomb_danger: float = 1
    w_explosion_danger: float = -10
    saved_weights = False
    weight_file: str
    saved_dist: float = None
    results_data: dict[str, int]
    
    monster_engage_distance = 5
    is_monster = False
    flee_target: tuple[int, int] = None

    def __init__(self, name, avatar, x, y, weight_file_name, results_data = {}):
        super().__init__(name, avatar, x, y)
        self.weight_file = "training/{}.txt".format(weight_file_name)
        self.results_data = results_data
        
        try: # Load weights from file
            with open(self.weight_file, 'r') as wfile:
                self.w_goal = float(wfile.readline())
                self.w_monster = float(wfile.readline())
                self.w_bomb_danger = float(wfile.readline())
                self.w_explosion_danger = float(wfile.readline())
            print("Loaded weights: ", self.w_goal, ", ", self.w_monster, ", ", self.w_bomb_danger, ", ", self.w_explosion_danger, sep='')
        except Exception as e:
            print("Failed to read weights:", e)
    
    def __del__(self):
        self.save_weights()

    def save_weights(self):
        if self.saved_weights:
            return
        
        try: # Save weights to file
            with open(self.weight_file, 'w') as wfile:
                wfile.writelines([
                    str(self.w_goal), '\n',
                    str(self.w_monster), '\n',
                    str(self.w_bomb_danger), '\n',
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
            feat_bomb_danger = max(0, 1 - (min_dist_to_bomb / wrld.expl_range))
        return feat_bomb_danger

    def out_of_bomb_danger(self, wrld: SensedWorld) -> bool:
        me = wrld.me(self)
        if not me:
            me = self

        bombs = self.find_bombs_for_wall(wrld, me.x, me.y)
        bombs = list(filter(lambda b: b.timer < 2, bombs))

        return len(bombs) == 0

    def calculate_goal_feature(self, wrld: SensedWorld, me: CharacterEntity) -> tuple[float, tuple[int, int]]:
        dist_goal, first_step = self.find_path(wrld)
        
        if dist_goal == float("inf"):
            goal_x, goal_y = wrld.exitcell
            me_x, me_y = me.x, me.y
            dist_goal = max(abs(goal_x - me_x), abs(goal_y - me_y))
            
        goal_feat = 1 - (dist_goal / self.saved_dist)
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

        goal_feat, _ = self.calculate_goal_feature(wrld, me)
        feature_monster = self.calculate_monster_component(wrld, me)
        feat_bomb_danger = self.calculate_bomb_danger(wrld, me)
        feat_expl_danger = self.out_of_bomb_danger(wrld)
        if feat_expl_danger == None:
            feat_expl_danger = 0
        q_value = self.w_goal * goal_feat + self.w_monster * feature_monster + self.w_bomb_danger * feat_bomb_danger + self.w_explosion_danger * feat_expl_danger
        
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
    
    def get_neighbors(self, wrld: SensedWorld, pos: tuple[int, int], strictly_pathable = False, monster_check = False) -> list[tuple[int, int]]:
        neighbors = list()
        for x in range(-1, 2, 1):
            if pos[0] + x < 0 or pos[0] + x >= wrld.width():
                continue
            for y in range(-1, 2, 1):
                if pos[1] + y < 0 or pos[1] + y >= wrld.height():
                    continue
                if wrld.empty_at(pos[0] + x, pos[1] + y) or wrld.exit_at(pos[0] + x, pos[1] + y) or (not strictly_pathable and wrld.explosion_at(pos[0] + x, pos[1] + y)) or (monster_check and wrld.monsters_at(pos[0] + x, pos[1] + y)):
                    neighbors.append((pos[0] + x, pos[1] + y))
                elif not strictly_pathable and (x == 0 or y == 0) and wrld.wall_at(pos[0] + x, pos[1] + y):
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
        def monster_score(m: MonsterEntity, p: tuple[int, int]) -> float:
            s_dist = self.monster_engage_distance - self.dist((m.x, m.y), p)

            if s_dist <= 0:
                return 0
            
            l_dp = self.dist(p, (m.x, m.y))
            l_dd = math.sqrt(m.dx * m.dx + m.dy * m.dy)
            if l_dd == 0 or l_dp == 0:
                return s_dist

            s_dot = m.dx * (p[0] - m.x) + m.dy * (p[1] - m.y)
            s_dot /= l_dp
            s_dot /= l_dd

            return max(0, s_dist * 2 + s_dot * 0.25)

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

                if wrld.wall_at(*neighbor):
                    m = -1
                    for bomb in self.find_bombs_for_wall(wrld, *neighbor):
                        m = max(m, bomb.timer)
                    if m < 0:
                        m = wrld.bomb_time
                    new_cost += m + wrld.expl_duration
                elif (expl := wrld.explosion_at(*neighbor)):
                    new_cost += expl.timer

                for m_list in wrld.monsters.values():
                    for m in m_list:
                        new_cost += monster_score(m, neighbor)

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
    
    def in_monster_range(self, wrld: SensedWorld, start_pos = None) -> bool:
        me = wrld.me(self)
        if not me:
            me = self
        if not start_pos:
            start_pos = (me.x, me.y)

        monsters = set()
        for m_list in wrld.monsters.values():
            for m in m_list:
                monsters.add((m.x, m.y))

        if not len(monsters):
            return False
        
        if not any(map(lambda mp: self.dist(mp, start_pos) < self.monster_engage_distance, monsters)):
            return False

        queue = PriorityQueue()
        cost_so_far = {start_pos: 0}

        queue.put((0, start_pos))

        while not queue.empty():
            _, pos = queue.get(False)

            if pos in monsters:
                return True

            for neighbor in self.get_neighbors(wrld, pos, True, True):
                new_cost = cost_so_far[pos] + 1
                if new_cost >= self.monster_engage_distance:
                    continue

                if neighbor not in cost_so_far or new_cost < cost_so_far[neighbor]:
                    cost_so_far[neighbor] = new_cost
                    priority = new_cost + min(self.dist(g, neighbor) for g in monsters)
                    queue.put((priority, neighbor))
        
        return False

    def q_learning_update(self, wrld: World, reward: float, alpha=0.2, gamma=0.9):
        me = wrld.me(self)
        if not me:
            me = self

        #print("Qlearning update", reward)

        goal_feat, _ = self.calculate_goal_feature(wrld, me)
        feature_monster = self.calculate_monster_component(wrld, me)
        feat_bomb_danger = self.calculate_bomb_danger(wrld, me)
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
        new_w_explosion_danger = self.w_explosion_danger + alpha * delta * feat_expl_danger

        return new_w_goal, new_w_monster, new_w_bomb_danger, new_w_explosion_danger

    def calc_reward(self, wrld: World, v_exmax: float, a_exmax: tuple[int, int] | bool) -> float:
        reward = 0

        if not self.out_of_bomb_danger(wrld):
            reward -= 5
        
        (d_goal, p_path) = self.find_path(wrld)

        dx = p_path[0] - self.x
        dy = p_path[1] - self.y

        if wrld.wall_at(*p_path):
            reward += 2 if a_exmax == True else 0
        elif a_exmax == True:
            reward += 1
        
        if isinstance(a_exmax, tuple):
            reward += (a_exmax[0] * dx + a_exmax[1] * dy) * 0.25

        for m_list in wrld.monsters.values():
            m: MonsterEntity
            for m in m_list:
                d_m = self.dist((m.x, m.y), (self.x, self.y))
                nd_m = 1 - d_m / self.monster_engage_distance
                if nd_m <= 0:
                    continue
                reward -= nd_m - 0.75
        
        return reward


    def find_safe_flee_spot(self, wrld: World) -> tuple[int, int] | None:
        me_x, me_y = self.x, self.y
        all_neighbors = self.get_neighbors(wrld, (me_x, me_y), strictly_pathable=True)

        for pos in all_neighbors:
            if not len(self.find_bombs_for_wall(wrld, *pos)):
                return pos
        
        return None
        

    def do(self, wrld: World):
        if not self.saved_dist:
            (self.saved_dist, _) = self.find_path(wrld)

        self.is_monster = self.in_monster_range(wrld)
        if self.is_monster:
            self.flee_target = None
            value, best_action = self.get_action(wrld)
            #print("Qlearning", best_action)

            reward = self.calc_reward(wrld, value, best_action)
            self.w_goal, self.w_monster, self.w_bomb_danger, self.w_explosion_danger = self.q_learning_update(wrld, reward)

            if isinstance(best_action, tuple):
                self.move(*best_action)
            elif best_action == True:
                self.place_bomb()
            return
        
        bomb = self.find_bomb(wrld, self)

        if not bomb and self.flee_target:
            self.flee_target = None
            #print("Cleared bomb")
        elif bomb and not self.flee_target:
            self.flee_target = self.find_safe_flee_spot(wrld)
            #print("found bomb", bomb.timer, self.flee_target)

        if self.flee_target:
            dx = self.flee_target[0] - self.x
            dy = self.flee_target[1] - self.y
            self.move(dx, dy)
            #print("Fleeing", dx, dy, bomb.timer)
            return

        _, next_step = self.find_path(wrld)
        if next_step:
            if expl := wrld.explosion_at(*next_step):
                self.move(0, 0)
                #print("pathing waiting", expl.timer)
            elif wrld.wall_at(*next_step):
                self.place_bomb()
                #print("pathing bomb")
            else:
                dx = next_step[0] - self.x
                dy = next_step[1] - self.y
                self.move(dx, dy)
                #print("pathing", dx, dy)
            
        
    def done(self, wrld: SensedWorld):
        agent_state = "PATHING"
        if self.is_monster:
            agent_state = "Q_LEARNING"
        elif self.flee_target:
            agent_state = "FLEEING"

        reward = 0
        event: Event
        for event in wrld.events:
            if event.tpe == Event.CHARACTER_FOUND_EXIT and event.character == self:
                reward += 20
            elif event.tpe == Event.CHARACTER_KILLED_BY_MONSTER and event.character == self:
                reward -= 10
            elif event.tpe == Event.BOMB_HIT_CHARACTER and event.other == self:
                if self.is_monster:
                    reward -= 15
                else:
                    print("Killed self:", (self.x, self.y), self.flee_target, self.is_monster)
                    #raise Exception("Why?")

            name = str(event)
            if agent_state not in self.results_data:
                self.results_data[agent_state] = { }
            if name not in self.results_data[agent_state]:
                self.results_data[agent_state][name] = 0
            self.results_data[agent_state][name] += 1

        if wrld.time <= 0:
            reward = -5

            name = "out of time"
            if agent_state not in self.results_data:
                self.results_data[agent_state] = { }
            if name not in self.results_data[agent_state]:
                self.results_data[agent_state][name] = 0
            self.results_data[agent_state][name] += 1
        
        self.w_goal, self.w_monster, self.w_bomb_danger, self.w_explosion_danger = self.q_learning_update(wrld, reward)

        self.save_weights()
        