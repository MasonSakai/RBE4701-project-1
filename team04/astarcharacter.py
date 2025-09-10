# This is necessary to find the main code
import sys
sys.path.insert(0, '../bomberman')
# Import necessary stuff
from entity import CharacterEntity
from sensed_world import SensedWorld
from colorama import Fore, Back
from queue import PriorityQueue
import math

class AStarCharacter(CharacterEntity):

    path: list[tuple[int, int]] = None

    def get_goals(self, wrld: SensedWorld) -> set[tuple[int, int]]:
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


    def dist(self, a: tuple[int, int], b: tuple[int, int]) -> float:
        dx = b[0] - a[0]
        dy = b[1] - a[1]
        return math.sqrt(dx * dx + dy * dy)

    def find_path(self, wrld: SensedWorld) -> bool:
        start_pos = (wrld.me(self).x, wrld.me(self).y)
        print(start_pos, wrld.width(), wrld.height())

        queue = PriorityQueue()
        came_from = dict()
        cost_so_far = { start_pos: 0 }

        goals = self.get_goals(wrld)
        found_goal = None

        queue.put((0, start_pos))

        while not queue.empty():
            (_, pos) = queue.get(False)
            if pos in goals:
                print("goal:", pos)
                found_goal = pos
                break
            neighbors = self.get_neighbors(wrld, pos)
            for neighbor in neighbors:
                new_cost = cost_so_far[pos] + 1
                if neighbor not in cost_so_far or new_cost < cost_so_far[neighbor]:
                    cost_so_far[neighbor] = new_cost
                    priority = new_cost + min(map(lambda p: self.dist(p, neighbor), goals))
                    queue.put((priority, neighbor))
                    came_from[neighbor] = pos

        if not found_goal:
            return False

        pos = found_goal
        path = []
        while pos in came_from:
            path.append(pos)
            pos = came_from[pos]

        print(path)
        self.path = path
        return True


    def traverse(self, wrld: SensedWorld):
        me = wrld.me(self)
        next = self.path.pop()
        dx = next[0] - me.x
        dy = next[1] - me.y
        self.move(dx, dy)

    def do(self, wrld):
        if not self.path and not self.find_path(wrld):
            raise Exception("Failed to find path")

        self.traverse(wrld)
