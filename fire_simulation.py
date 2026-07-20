# fire_simulation.py
from collections import deque
import random
import copy
import json

# choose grid sizes
GRID_OPTIONS = [25, 28, 30, 32]

DIRS = [(-1,0),(1,0),(0,-1),(0,1)]  # up,down,left,right

class SimulationEngine:
    def __init__(self):
        # parameters
        self.rows = 30
        self.cols = 30
        self.grid = []
        self.walls = set()
        self.exits = []        # list of (r,c)
        self.fires = set()     # set of (r,c)
        self.humans = []       # list of dicts {id, r, c, block}
        self.max_ticks = 60    # fire spread duration (seconds)
        self.tick_ms = 500     # client should use this (ms per tick)
        self.frames = []       # will hold frames after simulate_full()
        self.fire_spread_interval = 1  # fire spreads every  ticks
        self.human_speed = 2    # humans move  steps per tick

    #This function is for the grid of fire means building 
    def create_random_scenario(self):
        # choose random grid size
        self.rows = random.choice(GRID_OPTIONS)
        self.cols = self.rows
        self.grid = [["empty" for _ in range(self.cols)] for __ in range(self.rows)]
        self.walls = set()
        self.exits = []
        self.fires = set()
        self.humans = []
        self.frames = []

        # place walls randomly (~20-26% cells) but leave border free
        prob = 0.22
        for r in range(self.rows):
            for c in range(self.cols):
                if r in (0, self.rows-1) or c in (0, self.cols-1):
                    continue
                if random.random() < prob:
                    self.grid[r][c] = "wall"
                    self.walls.add((r,c))

        # place two exits on edges (2-3 cells each) - ensure different sides typically left/right or top/bottom
        sides = ["left","right","top","bottom"]
        side1 = random.choice(sides)
        possible = [s for s in sides if s != side1]
        side2 = random.choice(possible)
        self._place_exit_on_side(side1)
        self._place_exit_on_side(side2)

        # carve some corridors to ensure reachability (random walks from center toward each exit)
        self._carve_paths_to_exits()

        # place 2-3 fire sources on different sides/areas (not on wall/exit)
        fire_count = random.choice([2,3])
        attempts = 0
        while len(self.fires) < fire_count and attempts < 1000:
            attempts += 1
            # pick random area near edges or random
            r = random.randint(1, self.rows-2)
            c = random.randint(1, self.cols-2)
            if self.grid[r][c] == "empty":
                self.grid[r][c] = "fire"
                self.fires.add((r,c))

        # place human clusters (A block = left half area, B block = right half area)
        self._place_human_cluster(block="A", count=random.randint(6,12), area="left")
        self._place_human_cluster(block="B", count=random.randint(6,12), area="right")

    def _place_exit_on_side(self, side):
        width = random.choice([2,3])
        if side == "left":
            r0 = random.randint(2, max(2, self.rows - width - 3))
            for i in range(width):
                rr = r0 + i
                self.grid[rr][0] = "exit"
                self.exits.append((rr,0))
        elif side == "right":
            r0 = random.randint(2, max(2, self.rows - width - 3))
            for i in range(width):
                rr = r0 + i
                self.grid[rr][self.cols-1] = "exit"
                self.exits.append((rr,self.cols-1))
        elif side == "top":
            c0 = random.randint(2, max(2, self.cols - width - 3))
            for i in range(width):
                cc = c0 + i
                self.grid[0][cc] = "exit"
                self.exits.append((0,cc))
        else:
            c0 = random.randint(2, max(2, self.cols - width - 3))
            for i in range(width):
                cc = c0 + i
                self.grid[self.rows-1][cc] = "exit"
                self.exits.append((self.rows-1,cc))

    def _carve_paths_to_exits(self):
        # simple carve from center to exits so there is at least one route
        center = (self.rows//2, self.cols//2)
        for ex in self.exits:
            r,c = center
            tr,tc = ex
            steps = 0
            while (r,c) != (tr,tc) and steps < self.rows*self.cols:
                if r < tr: r += 1
                elif r > tr: r -= 1
                if c < tc: c += 1
                elif c > tc: c -= 1
                if self.grid[r][c] == "wall":
                    self.grid[r][c] = "empty"
                steps += 1

    def _place_human_cluster(self, block="A", count=8, area="left"):
        attempts = 0
        placed = 0
        while placed < count and attempts < 5000:
            attempts += 1
            if area == "left":
                r = random.randint(2, self.rows-3)
                c = random.randint(2, max(2, self.cols//2 - 3))
            else:
                r = random.randint(2, self.rows-3)
                c = random.randint(min(self.cols-3, self.cols//2 + 3), self.cols-3)
            if self.grid[r][c] == "empty":
                hid = len(self.humans) + 1
                self.humans.append({"id": hid, "r": r, "c": c, "block": block, "escaped": False, "trapped": False})
                placed += 1

    def get_initial_state(self):
        # provide initial map for frontend rendering
        return {
            "rows": self.rows,
            "cols": self.cols,
            "walls": list(self.walls),
            "exits": self.exits,
            "fires": list(self.fires),
            "humans": [{"id":h["id"], "r":h["r"], "c":h["c"], "block":h["block"]} for h in self.humans],
            "tick_ms": self.tick_ms,
            "max_ticks": self.max_ticks
        }

    # BFS shortest path avoiding walls and fire (returns list of coords)
    def bfs_shortest_path(self, start, avoid_fire_set):
        sr, sc = start
        q = deque()
        q.append((sr,sc))
        parent = { (sr,sc): None }
        visited = set([(sr,sc)])
        while q:
            r,c = q.popleft()
            if (r,c) in self.exits:
                # reconstruct
                path = []
                cur = (r,c)
                while cur:
                    path.append(cur)
                    cur = parent[cur]
                path.reverse()
                return path
            for dr,dc in DIRS:
                nr, nc = r+dr, c+dc
                if 0 <= nr < self.rows and 0 <= nc < self.cols:
                    if (nr,nc) in visited: continue
                    if self.grid[nr][nc] == "wall": continue
                    if (nr,nc) in avoid_fire_set: continue
                    visited.add((nr,nc))
                    parent[(nr,nc)] = (r,c)
                    q.append((nr,nc))
        return []

    def simulate_full(self):
        """
        Simulate for max_ticks. At each tick:
         - spread fire (BFS wave using current fire set)
         - for each human compute shortest path avoiding walls and current fires
         - if path exists, move human one step along path
         - update status escaped/trapped
        We'll produce frames list: each frame is dict with fires, humans (positions + path), exits, walls.
        """
        # deep copy starting baseline grid + sets
        fires = set(self.fires)
        walls = set(self.walls)
        humans = [h.copy() for h in self.humans]
        frames = []

        for tick in range(self.max_ticks):
            # compute paths for humans with current fire positions
            human_states = []
            for h in humans:
                if h["escaped"] or h["trapped"]:
                    human_states.append({"id":h["id"], "r":h["r"], "c":h["c"], "block":h["block"], "escaped":h["escaped"], "trapped":h["trapped"], "path": []})
                    continue
                path = self.bfs_shortest_path((h["r"],h["c"]), fires)
                # if no path -> trapped
                if not path or len(path) == 0:
                    h["trapped"] = True
                    human_states.append({"id":h["id"], "r":h["r"], "c":h["c"], "block":h["block"], "escaped":True if h["escaped"] else False, "trapped":True, "path": []})
                    continue
                # if next step is exit, mark escaped
                if len(path) >= 2 and path[1] in self.exits:
                    # move into exit
                    nr,nc = path[1]
                    h["r"], h["c"] = nr, nc
                    h["escaped"] = True
                    human_states.append({"id":h["id"], "r":h["r"], "c":h["c"], "block":h["block"], "escaped":True, "trapped":False, "path": path})
                else:
                    # move one step along path (index 1)
                    if len(path) >= 2:
                        # move human up to 'human_speed' steps along path if available
                        steps = min(self.human_speed, len(path) - 1)
                        nr, nc = path[steps]

                        # if stepping into fire now -> trapped
                        if (nr,nc) in fires:
                            h["trapped"] = True
                            human_states.append({"id":h["id"], "r":h["r"], "c":h["c"], "block":h["block"], "escaped":False, "trapped":True, "path": path})
                        else:
                            h["r"], h["c"] = nr, nc
                            human_states.append({"id":h["id"], "r":h["r"], "c":h["c"], "block":h["block"], "escaped":False, "trapped":False, "path": path})
                    else:
                        human_states.append({"id":h["id"], "r":h["r"], "c":h["c"], "block":h["block"], "escaped":False, "trapped":False, "path": path})

            # record frame
            frames.append({
                "tick": tick,
                "fires": list(fires),
                "humans": human_states,
                "exits": list(self.exits),
                "walls": list(walls),
            })

            # spread fire to neighbors (wave): collect new fires
            if tick % self.fire_spread_interval == 0:
                newfires = set()
                for (fr, fc) in list(fires):
                    for dr, dc in DIRS:
                        nr, nc = fr + dr, fc + dc
                        if 0 <= nr < self.rows and 0 <= nc < self.cols:
                            if (nr, nc) in walls or (nr, nc) in self.exits or (nr, nc) in fires:
                                continue
                            newfires.add((nr, nc))
                fires.update(newfires)
            # add newfires to fires
            for nf in newfires:
                fires.add(nf)

            # update humans list status propagate to next tick (humans list is mutated above)

        # After loop, return frames and tick_ms to client
        # Convert tuples to lists for JSON
        def serialize(fr):
            fr2 = copy.deepcopy(fr)
            fr2["fires"] = [[a,b] for (a,b) in fr2["fires"]]
            fr2["exits"] = [[a,b] for (a,b) in fr2["exits"]]
            fr2["walls"] = [[a,b] for (a,b) in fr2["walls"]]
            for h in fr2["humans"]:
                h["path"] = [[r,c] for (r,c) in h.get("path",[])]
            return fr2

        self.frames = [serialize(f) for f in frames]
        return self.frames, self.tick_ms
