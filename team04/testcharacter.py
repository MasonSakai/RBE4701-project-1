# This is necessary to find the main code
import sys
sys.path.insert(0, '../bomberman')
# Import necessary stuff
from entity import CharacterEntity
from colorama import Fore, Back
from worldstate import WorldStateTree
from math import inf
from sensed_world import SensedWorld

def get_goals(self, wrld: SensedWorld) -> set[tuple[int, int]]:
        """
        Return a set of all goal positions (x, y) in the world.
        """
        goals = set()
        for x in range(wrld.width()):
            for y in range(wrld.height()):
                if wrld.exit_at(x, y):   # check if this cell is a goal/exit
                    goals.add((x, y))
        return goals

def evaluate_state(self, node: WorldStateTree) -> float:

    goals = self.get_goals(node.world)
    goal_pos = next(iter(goals))  
    goal_x, goal_y = goal_pos

    player_pos = (node.world.me(node.actor).x, node.world.me(node.actor).y)
    player_x, player_y = player_pos 

    distance = abs(player_x - goal_x) + abs(player_y - goal_y)

    return -distance

class TestCharacter(CharacterEntity):
    # def __init__(self, name, avatar, x, y, actors: list[CharacterEntity | str | tuple[str, int]]):
    #     CharacterEntity.__init__(self, name, avatar, x, y)
    #     for i, actor in enumerate(actors):
    #         if actor is None:
    #             actors[i] = self
    #     self.actors = actors
        
    # tree: WorldStateTree = None
# Function needs to stop at a certain depth on the tree. We pass in the tree and the required depth
    def Expectimax(self, generatedNode: WorldStateTree, depth=3):
        if generatedNode is None:
            return -inf
        if depth == 0:
            return evaluate_state(generatedNode)
        if generatedNode.actor_turn == 0:
            best_value = float('-inf')
            for child in generatedNode.get_next():
                value = self.Expectimax(child[0], depth - 1)
                if value > best_value:
                    best_value = value
                    best_action = child[1]
            return best_value, best_action
        else:
            v = 0
            for child in generatedNode.get_next():
                p = child[1]
                value, _ = self.Expectimax(child[0], depth - 1)
                v = v + p * value
            return v, None
    
    def do(self, wrld):
        if self.tree:
            self.tree = self.tree.get_progressed_state(wrld)
        if not self.tree:
            print("Tree Init")
            self.tree = WorldStateTree.CreateTree(self, wrld)
        depth_limit = 3
        value, best_action = self.Expectimax(self.tree, depth=depth_limit)

        if isinstance(best_action, tuple):
            wrld.me(self).move(best_action[0], best_action[1])
            return best_action
        elif best_action == True:
            wrld.me(self).place_bomb()
        else:
            return None

        
# function Expectimax(self, generatedTree, depth)
#     if generatedTree = []
#         return -inf (i.e player is dead)
#     if depth == 0 then
#         return generatedTree.utility (scores will be evaluated in a separate function)
#     else if generatedTree.actor_turn == 0 then
#         best_value = −inf
#         best_action = nothing
#         for each child in generatedTree.children do
#             value = self.Expectimax(child, depth - 1)
#             if value > best_value then
#                 best_value = value
#                 best_action = child.action
#         return best_action  
#     else if generatedTree.actor_turn > 0 then
#         v = 0
#         for each child in generatedTree.children do
#             p = child.probability
#             v = v + p * Expectimax(child, depth - 1)
#         return v
# end function

    



# The first time do is called, generate the tree and save it to the character's variables and then use get_progressed_state to update the tree
# Move Character -> Progress State -> Expectimax -> Move Character -> Progress State -> Expectimax



# ------------------------------------------------------------------------------------------------------------------------
# ------------------------------------------------------------------------------------------------------------------------
# ------------------------------------------------------------------------------------------------------------------------
# ------------------------------------------------------------------------------------------------------------------------
# ------------------------------------------------------------------------------------------------------------------------

# def evaluate_state(state: WorldStateTree, my_actor: CharacterEntity) -> float:
#     me = state.world.me(my_actor)
#     if me is None:
#         return -9999 
    
#     visited_penalty = 0
#     bomb_penalty = 0
    
#     monsters = []
#     for a in state.actors:
#         if isinstance(a, str): 
#             m = state.find_monster(a)
#             if m:
#                 monsters.append(m)
#         elif isinstance(a, (tuple, list)) and len(a) == 3: 
#             m = state.find_monster(a[0])
#             if m:
#                 monsters.append(m)

#     score = 1000

#     if state.parent_state:
#         parent_me = state.parent_state.world.me(my_actor)
#         if parent_me and (me.x, me.y) == (parent_me.x, parent_me.y):
#             score -= 1000
#             visited_penalty -= 1000

#     if hasattr(my_actor, 'last_positions'):
#         if (me.x, me.y) in my_actor.last_positions[-5:]: 
#             score -= 2000  

#     exit_positions = [(x, y) for x in range(state.world.width())
#                       for y in range(state.world.height()) if state.world.exit_at(x, y)]
#     if exit_positions:
#         min_dist = min(abs(me.x - x) + abs(me.y - y) for x, y in exit_positions)
#         score += max(0, 500 - 10*min_dist)  
#         if min_dist == 0:
#             score += 5000

#     for monster in monsters:
#         m_dist = abs(me.x - monster.x) + abs(me.y - monster.y)
#         if m_dist == 0: 
#             score -= 5000
#         elif m_dist == 1:
#             score -= 2000
#         elif m_dist == 2:
#             score -= 1000

#     bomb = state.world.bomb_at(me.x, me.y)
#     if bomb:
#         score -= 5000
#         bomb_penalty -= 5000
#     for nx, ny in state.get_safe_neighbors(me.x, me.y):
#         bomb = state.world.bomb_at(nx, ny)
#         if bomb:
#             score -= 3000
#             bomb_penalty -= 3000

#     print(f"x={me.x},y={me.y}, min_dist={min_dist}, score={score} "
#       f"visited_penalty={visited_penalty}, bomb_penalty={bomb_penalty}")
    
#     return score




#     def do(self, wrld):
#         if not hasattr(self, 'last_positions'):
#             self.last_positions = []

#         actors = [self, 'selfpreserving'] 
#         root = WorldStateTree.CreateTree(wrld, actors)

#         children = [child for child, _ in root.get_next()]

#         best_score = -inf
#         best_state = None

#         for child in children:
#             score, chosen_child = self.minimax(child, depth=3, alpha=-inf, beta=inf, maximizing=True, original_depth = None)
#             if score > best_score:
#                 best_score = score
#                 best_state = chosen_child

#         if best_state is None:
#             return

#         me_now = wrld.me(self)
#         me_next = best_state.world.me(self)
#         dx = me_next.x - me_now.x
#         dy = me_next.y - me_now.y

#         print(f"Recommended move: dx={dx}, dy={dy}, score={best_score}")

#         self.last_positions.append((me_now.x, me_now.y))
#         self.last_positions = self.last_positions[-4:] 

#         if dx != 0 or dy != 0:
#             self.move(dx, dy)
#         # elif not root.find_bomb(me_now):
#         #     self.place_bomb()

#     def minimax(self, node: WorldStateTree, depth=3, alpha=-inf, beta=inf, maximizing=True, original_depth=None):
#         if original_depth is None:
#             original_depth = depth

#         me = node.world.me(self)
#         immediate_score = evaluate_state(node, self)
#         if depth == 0 or me is None:
#             print(f"{'Max' if maximizing else 'Min'} leaf at depth {original_depth-depth} ({me.x if me else 'x'},{me.y if me else 'y'}): "
#               f"immediate={immediate_score}, propagated={immediate_score}")
#             return evaluate_state(node, self), node

#         children = [child for child in node.get_next()]

#         if maximizing:
#             max_eval = -inf
#             best_child = None
#             best_dist_for_this_level = inf  

#             for child in children:
#                 eval_score, chosen_leaf = self.minimax(child, depth-1, alpha, beta, False, original_depth)
                
#                 me_child = child.world.me(self)
#                 exit_positions = [(x, y) for x in range(child.world.width())
#                                 for y in range(child.world.height()) if child.world.exit_at(x, y)]
#                 dist_to_exit = min(abs(me_child.x - x) + abs(me_child.y - y) for x, y in exit_positions) if exit_positions else 0

#                 if eval_score > max_eval or (eval_score == max_eval and dist_to_exit < best_dist_for_this_level):
#                     max_eval = eval_score
#                     best_dist_for_this_level = dist_to_exit
#                     best_child = child if depth == original_depth else chosen_leaf

#                 alpha = max(alpha, eval_score)
#                 if beta <= alpha:
#                     break
            
#             print(f"Max node at depth {original_depth-depth} ({me.x},{me.y}): immediate={immediate_score}, propagated={max_eval}")
#             return max_eval, best_child

#         else:  # minimizing
#             min_eval = inf
#             best_child = None

#             for child in children:
#                 eval_score, chosen_leaf = self.minimax(child, depth-1, alpha, beta, True, original_depth)

#                 if eval_score < min_eval:
#                     min_eval = eval_score
#                     best_child = child if depth == original_depth else chosen_leaf

#                 beta = min(beta, eval_score)
#                 if beta <= alpha:
#                     break
            
#             print(f"Min node at depth {original_depth-depth} ({me.x},{me.y}): immediate={immediate_score}, propagated={min_eval}")
#             return min_eval, best_child
