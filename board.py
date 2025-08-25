from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from constants import GRID_SIZE, STANDARD_SHIPS


EMPTY = 0
SHIP = 1
HIT = 2
MISS = 3


@dataclass
class Ship:
    length: int
    cells: List[Tuple[int, int]] = field(default_factory=list)
    hits: int = 0

    @property
    def sunk(self) -> bool:
        return self.hits >= self.length


class Board:
    def __init__(self, size: int = GRID_SIZE):
        self.size = size
        self.grid: List[List[int]] = [[EMPTY for _ in range(size)] for _ in range(size)]
        self.ships: List[Ship] = []
        self.total_ship_cells = 0

    def in_bounds(self, r: int, c: int) -> bool:
        return 0 <= r < self.size and 0 <= c < self.size

    def can_place(self, r: int, c: int, length: int, horizontal: bool) -> bool:
        for i in range(length):
            rr = r + (0 if horizontal else i)
            cc = c + (i if horizontal else 0)
            if not self.in_bounds(rr, cc):
                return False
            if self.grid[rr][cc] != EMPTY:
                return False
        return True

    def place_ship(self, r: int, c: int, length: int, horizontal: bool) -> bool:
        if not self.can_place(r, c, length, horizontal):
            return False
        cells = []
        for i in range(length):
            rr = r + (0 if horizontal else i)
            cc = c + (i if horizontal else 0)
            self.grid[rr][cc] = SHIP
            cells.append((rr, cc))
        self.ships.append(Ship(length=length, cells=cells))
        self.total_ship_cells += length
        return True

    def random_place_all(self, ships: List[int] = None, seed: Optional[int] = None) -> None:
        if ships is None:
            ships = STANDARD_SHIPS
        if seed is not None:
            random.seed(seed)
        self.grid = [[EMPTY for _ in range(self.size)] for _ in range(self.size)]
        self.ships = []
        self.total_ship_cells = 0
        for length in ships:
            placed = False
            tries = 0
            while not placed and tries < 1000:
                tries += 1
                horizontal = bool(random.getrandbits(1))
                if horizontal:
                    r = random.randrange(self.size)
                    c = random.randrange(self.size - length + 1)
                else:
                    r = random.randrange(self.size - length + 1)
                    c = random.randrange(self.size)
                placed = self.place_ship(r, c, length, horizontal)
            if not placed:
                # Fallback simple deterministic scan (very unlikely needed)
                for r in range(self.size):
                    for c in range(self.size - length + 1):
                        if self.place_ship(r, c, length, True):
                            placed = True
                            break
                    if placed:
                        break
            if not placed:
                raise RuntimeError("Failed to place all ships")

    def receive_shot(self, r: int, c: int) -> Tuple[bool, Optional[int], bool]:
        """
        Returns (hit, sunk_length, game_over)
        """
        if not self.in_bounds(r, c):
            return False, None, self.all_ships_sunk()
        cell = self.grid[r][c]
        if cell == HIT or cell == MISS:
            # Already shot; treat as miss to avoid double counting
            return False, None, self.all_ships_sunk()
        if cell == SHIP:
            self.grid[r][c] = HIT
            # Update ship hits
            sunk_length = None
            for ship in self.ships:
                if (r, c) in ship.cells:
                    ship.hits += 1
                    if ship.sunk:
                        sunk_length = ship.length
                    break
            return True, sunk_length, self.all_ships_sunk()
        else:
            self.grid[r][c] = MISS
            return False, None, self.all_ships_sunk()

    def is_valid_shot(self, r: int, c: int) -> bool:
        return self.in_bounds(r, c) and self.grid[r][c] not in (HIT, MISS)

    def all_ships_sunk(self) -> bool:
        return all(s.sunk for s in self.ships) and len(self.ships) > 0

    def get_public_view(self) -> List[List[int]]:
        """
        Returns a grid where own ships are hidden (ships appear as EMPTY unless hit).
        Useful to render the enemy board to the player.
        """
        view = [[EMPTY for _ in range(self.size)] for _ in range(self.size)]
        for r in range(self.size):
            for c in range(self.size):
                if self.grid[r][c] == HIT:
                    view[r][c] = HIT
                elif self.grid[r][c] == MISS:
                    view[r][c] = MISS
                else:
                    view[r][c] = EMPTY
        return view

    def get_ai_knowledge(self) -> List[List[int]]:
        """
        Returns a grid from the perspective of the attacker: UNKNOWN (-1), MISS (3), HIT (2)
        """
        view = [[-1 for _ in range(self.size)] for _ in range(self.size)]
        for r in range(self.size):
            for c in range(self.size):
                if self.grid[r][c] == HIT:
                    view[r][c] = HIT
                elif self.grid[r][c] == MISS:
                    view[r][c] = MISS
                else:
                    view[r][c] = -1
        return view

