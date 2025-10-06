# This is necessary to find the main code
from io import TextIOWrapper
import random
import sys
sys.path.insert(0, '../bomberman')
# Import necessary stuff
from entity import BombEntity, CharacterEntity, ExplosionEntity, MonsterEntity
from colorama import Fore, Back
from worldstate import WorldStateTree
from math import inf
from sensed_world import SensedWorld
from world import World
from events import Event
import math
from queue import PriorityQueue
import pygame

class QLearningCharacter(CharacterEntity):
    tree: WorldStateTree = None
    w_goal: float = 0
    w_stupid: float = 0
    w_smart: float = 0
    w_bomb_danger: float = 0
    w_bomb_potential: float = 0
    w_explosion_danger: float = 0
    saved_weights = False

    def __init__(self, name, avatar, x, y): #, recording_file_idents: list[str]
        super().__init__(name, avatar, x, y)
        
        try: # Load weights from file
            with open("QLearningWeights.txt", 'r') as wfile:
                self.w_goal = float(wfile.readline())
                self.w_stupid = float(wfile.readline())
                self.w_smart = float(wfile.readline())
                self.w_bomb_danger = float(wfile.readline())
                self.w_bomb_potential = float(wfile.readline())
                self.w_explosion_danger = float(wfile.readline())
            print("Loaded weights: ", self.w_goal, ", ", self.w_stupid, ", ", self.w_smart, ", ", self.w_bomb_danger, ", ", self.w_bomb_potential, ", ", self.w_explosion_danger, sep='')
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
                    str(self.w_stupid), '\n',
                    str(self.w_smart), '\n',
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


    def out_of_bomb_danger(self, wrld: World, coordinates:tuple) -> float:

        bomb_position = None
        current_pos = (coordinates)
        for b_x in range(wrld.width()):
            for b_y in range(wrld.height()):
                bomb = wrld.bomb_at(coordinates)
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

    def calculate_bomb_potential(self, wrld:World, coordinates: tuple[int, int]) -> float:
        x,y=coordinates
        if wrld.wall_at(x,y+1):
            return 1
        
        else:
            return 0
    
    def calculate_goal_feature(self, wrld: World, coordinates: tuple) -> tuple[float, tuple[int, int]]:
      for g_x in range(wrld.width()): 
        for g_y in range(wrld.height()):
            if wrld.exit_at(g_x,g_y):
                goal=(g_x,g_y)
           
      dist_goal = self.dist(coordinates,goal)
      
      return dist_goal
    

    def find_monster_stupid(self, wrld: World, position: tuple):
       monster_position_stupid = None

    # Loop over the whole board
       for m_x in range(wrld.width()): 
        for m_y in range(wrld.height()):
           if (wrld.monsters_at(m_x,m_y).x,wrld.monsters_at(m_x,m_y).y) and "stupid" == wrld.monsters_at(m_x,m_y).name:
               monster_position_stupid=(wrld.monsters_at(m_x,m_y).x,wrld.monsters_at(m_x,m_y).y)

       if monster_position_stupid:
           return self.dist(position,monster_position_stupid)
       else:
           return 0
       

    def find_monster_agressive(self, wrld: World, position: tuple):
       monster_position_aggresive = None

    # Loop over the whole board
       for m_x in range(wrld.width()): 
        for m_y in range(wrld.height()):
           if (wrld.monsters_at(m_x,m_y).x,wrld.monsters_at(m_x,m_y).y) and "aggressive" == wrld.monsters_at(m_x,m_y).name:
               monster_position_aggresive=(wrld.monsters_at(m_x,m_y).x,wrld.monsters_at(m_x,m_y).y)

       if monster_position_aggresive:
           return self.dist(position,monster_position_aggresive)
       else:
           return 0
       
    def find_monster_self_preserving(self, wrld: World, position: tuple):
       monster_position_selfpreserving = None

    # Loop over the whole board
       for m_x in range(wrld.width()): 
        for m_y in range(wrld.height()):
           if (wrld.monsters_at(m_x,m_y).x,wrld.monsters_at(m_x,m_y).y) and "selfpreserving" == wrld.monsters_at(m_x,m_y).name:
               monster_position_selfpreserving=(wrld.monsters_at(m_x,m_y).x,wrld.monsters_at(m_x,m_y).y)

       if monster_position_selfpreserving:
           return self.dist(position,monster_position_selfpreserving)
       else:
           return 0



    def evaluate_state(self, wrld: World,coordinates: tuple) -> float:
        goal_feat = self.calculate_goal_feature(wrld, coordinates)
        feat_expl_danger = self.out_of_bomb_danger(wrld,coordinates)
        feat_bomb_potential = self.calculate_bomb_potential(wrld, coordinates)

        q_value = self.w_goal * goal_feat + self.w_bomb_potential * feat_bomb_potential + self.w_explosion_danger * feat_expl_danger
        return q_value

    
    def get_neighbors(self, wrld: World, pos: tuple[int, int]) -> list[tuple[int, int]]:
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
    


    def q_learning_update(self, reward, best_future_q:float, q_value:float, coordinates:tuple, wrld:World, alpha=0.5, gamma=0.9):


        print("Qlearning update", reward)

        goal_feat, first_step = self.calculate_goal_feature(wrld, coordinates)
        feat_bomb_potential = self.calculate_bomb_potential(wrld,coordinates)
        feat_expl_danger = self.out_of_bomb_danger(wrld,coordinates=)

        delta = (reward + gamma * best_future_q) - q_value

        new_w_goal = self.w_goal + alpha * delta * goal_feat
        new_w_bomb_potential = self.w_bomb_potential + alpha * delta * feat_bomb_potential
        new_w_explosion_danger = self.w_bomb_potential + alpha * delta * feat_expl_danger

        return new_w_goal,new_w_bomb_potential, new_w_explosion_danger

    
    def do(self, wrld: World):
        
        
        reward = 1 / (1 + dist)
        print(value, best_action, dist, reward)

        candidate_weights = self.q_learning_update(self.tree, 0)
        # print(candidate_weights)

        self.w_goal, self.w_stupid, self.w_smart, self.w_bomb_danger, self.w_bomb_potential, self.w_explosion_danger = candidate_weights
        if isinstance(best_action, tuple):
            self.move(best_action[0], best_action[1])
        elif best_action == True:
            self.place_bomb()
        else:
            return None
        
    def done(self, wrld: SensedWorld):
        if self.tree:
            self.tree.fill_single_step()
            self.tree = self.tree.get_progressed_state(wrld)
            if self.tree:
                self.tree.prune_parents()
        if not self.tree:
            print("Tree Init")
            self.tree = WorldStateTree.CreateTree(self, wrld)

        reward = 0
        event: Event
        for event in wrld.events:
            if event.tpe == Event.CHARACTER_FOUND_EXIT and event.character == self:
                reward += 10
            elif event.tpe == Event.CHARACTER_KILLED_BY_MONSTER and event.character == self:
                reward -= 5
            elif event.tpe == Event.BOMB_HIT_CHARACTER and event.other == self:
                reward -= 5
        if wrld.time <= 0:
            reward = -5
        
        self.w_goal, self.w_stupid, self.w_smart, self.w_bomb_danger, self.w_bomb_potential, self.w_explosion_danger = self.q_learning_update(self.tree, reward)

        self.save_weights()
        