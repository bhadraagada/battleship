from __future__ import annotations

from typing import List, Tuple, Optional, Set

from constants import GRID_SIZE, STANDARD_SHIPS
from board import HIT, MISS


class BattleshipAI:
    """
    Alpha-beta inspired Battleship AI.

    Uses a heatmap of all valid placements of remaining ships consistent with known hits/misses.
    Scores shots by expected gain minus opponent's best immediate counter-gain on the AI's board.
    This is a pragmatic, depth-1 minimax approximation suitable for real-time play.
    """

    def __init__(self, size: int = GRID_SIZE, ships: Optional[List[int]] = None):
        self.size = size
        self.remaining_ships: List[int] = list(ships or STANDARD_SHIPS)
        self._target_cache: List[Tuple[int, int]] = []

    def notify_sunk(self, length: int):
        # Remove one ship of matching length if tracked
        if length in self.remaining_ships:
            self.remaining_ships.remove(length)

    # --- Heatmap logic ---
    def _valid_placement_on_knowledge(self, knowledge: List[List[int]], r: int, c: int, length: int, horizontal: bool) -> bool:
        for i in range(length):
            rr = r + (0 if horizontal else i)
            cc = c + (i if horizontal else 0)
            if rr < 0 or rr >= self.size or cc < 0 or cc >= self.size:
                return False
            cell = knowledge[rr][cc]
            if cell == MISS:
                return False
            # HIT is allowed; UNKNOWN (-1) is allowed
        return True

    def _hit_clusters(self, knowledge: List[List[int]]) -> List[Tuple[Set[Tuple[int, int]], Optional[str]]]:
        """
        Return list of (cells_set, orientation) where orientation in {'h','v',None}
        Cells are 4-connected components of HIT cells. Orientation is inferred if >=2 colinear.
        """
        visited = [[False for _ in range(self.size)] for _ in range(self.size)]
        clusters: List[Tuple[Set[Tuple[int, int]], Optional[str]]] = []
        for r in range(self.size):
            for c in range(self.size):
                if knowledge[r][c] == HIT and not visited[r][c]:
                    stack = [(r, c)]
                    comp: Set[Tuple[int, int]] = set()
                    visited[r][c] = True
                    while stack:
                        rr, cc = stack.pop()
                        comp.add((rr, cc))
                        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                            nr, nc = rr + dr, cc + dc
                            if 0 <= nr < self.size and 0 <= nc < self.size and not visited[nr][nc] and knowledge[nr][nc] == HIT:
                                visited[nr][nc] = True
                                stack.append((nr, nc))
                    # infer orientation
                    if len(comp) >= 2:
                        rows = {rr for rr, _ in comp}
                        cols = {cc for _, cc in comp}
                        orient: Optional[str] = None
                        if len(rows) == 1:
                            orient = 'h'
                        elif len(cols) == 1:
                            orient = 'v'
                        clusters.append((comp, orient))
                    else:
                        clusters.append((comp, None))
        return clusters

    def _placement_cells(self, r: int, c: int, length: int, horizontal: bool) -> List[Tuple[int, int]]:
        return [(r + (0 if horizontal else i), c + (i if horizontal else 0)) for i in range(length)]

    def _placement_consistent_with_clusters(
        self,
        cells: List[Tuple[int, int]],
        clusters: List[Tuple[Set[Tuple[int, int]], Optional[str]]],
        length: int,
        horizontal: bool,
    ) -> bool:
        # A ship placement can intersect at most one cluster, must fully cover it if it intersects,
        # and must align with the cluster's orientation if known. It cannot intersect a cluster larger than itself.
        intersected = 0
        cells_set = set(cells)
        for comp, orient in clusters:
            inter = cells_set.intersection(comp)
            if not inter:
                continue
            # intersected something
            if len(comp) > length:
                return False
            intersected += 1
            # Must include all cells of the cluster
            if not comp.issubset(cells_set):
                return False
            # Must align with cluster orientation if known
            if orient == 'h' and not horizontal:
                return False
            if orient == 'v' and horizontal:
                return False
            if intersected > 1:
                return False
        return True

    def heatmap(self, knowledge: List[List[int]], remaining_ships: Optional[List[int]] = None) -> List[List[int]]:
        ships = remaining_ships or self.remaining_ships
        heat = [[0 for _ in range(self.size)] for _ in range(self.size)]
        clusters = self._hit_clusters(knowledge)

        for length in ships:
            # Horizontal
            for r in range(self.size):
                for c in range(self.size - length + 1):
                    if self._valid_placement_on_knowledge(knowledge, r, c, length, True):
                        cells = self._placement_cells(r, c, length, True)
                        if self._placement_consistent_with_clusters(cells, clusters, length, True):
                            for i in range(length):
                                heat[r][c + i] += 1
            # Vertical
            for r in range(self.size - length + 1):
                for c in range(self.size):
                    if self._valid_placement_on_knowledge(knowledge, r, c, length, False):
                        cells = self._placement_cells(r, c, length, False)
                        if self._placement_consistent_with_clusters(cells, clusters, length, False):
                            for i in range(length):
                                heat[r + i][c] += 1

        # Slightly boost cells adjacent to known hits to focus targeting
        for r in range(self.size):
            for c in range(self.size):
                if knowledge[r][c] == HIT:
                    for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < self.size and 0 <= cc < self.size and knowledge[rr][cc] == -1:
                            heat[rr][cc] += 3

        # Parity pruning when hunting (no hits on board)
        any_hit = any(knowledge[r][c] == HIT for r in range(self.size) for c in range(self.size))
        if not any_hit and ships:
            min_len = min(ships)
            if min_len >= 2:
                for r in range(self.size):
                    for c in range(self.size):
                        if (r + c) % 2 == 1:
                            heat[r][c] = int(heat[r][c] * 0.25)  # heavily deprioritize off-parity

        return heat

    def _top_candidates(self, heat: List[List[int]], knowledge: List[List[int]], k: int = 8) -> List[Tuple[int, int]]:
        cells: List[Tuple[int, int, int]] = []  # (score, r, c)
        for r in range(self.size):
            for c in range(self.size):
                if knowledge[r][c] == -1:  # unknown
                    cells.append((heat[r][c], r, c))
        cells.sort(reverse=True)
        return [(r, c) for score, r, c in cells[:k] if score > 0] or [(r, c) for score, r, c in cells[:k]]

    def _target_candidates(self, knowledge: List[List[int]]) -> List[Tuple[int, int]]:
        # If there are hit clusters, return extension cells along lines and immediate neighbors
        clusters = self._hit_clusters(knowledge)
        cand: List[Tuple[int, int]] = []
        seen = set()
        for comp, orient in clusters:
            if not comp:
                continue
            if orient is None:
                # single or ambiguous: add orthogonal neighbors
                for r, c in comp:
                    for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < self.size and 0 <= cc < self.size and knowledge[rr][cc] == -1:
                            if (rr, cc) not in seen:
                                cand.append((rr, cc))
                                seen.add((rr, cc))
            else:
                # Oriented: extend on both ends
                if orient == 'h':
                    rows = next(iter({r for r, _ in comp}))
                    min_c = min(c for _, c in comp)
                    max_c = max(c for _, c in comp)
                    # extend left
                    cc = min_c - 1
                    while cc >= 0 and knowledge[rows][cc] == -1:
                        if (rows, cc) not in seen:
                            cand.append((rows, cc))
                            seen.add((rows, cc))
                        cc -= 1
                        break
                    # extend right
                    cc = max_c + 1
                    while cc < self.size and knowledge[rows][cc] == -1:
                        if (rows, cc) not in seen:
                            cand.append((rows, cc))
                            seen.add((rows, cc))
                        cc += 1
                        break
                else:  # vertical
                    cols = next(iter({c for _, c in comp}))
                    min_r = min(r for r, _ in comp)
                    max_r = max(r for r, _ in comp)
                    rr = min_r - 1
                    while rr >= 0 and knowledge[rr][cols] == -1:
                        if (rr, cols) not in seen:
                            cand.append((rr, cols))
                            seen.add((rr, cols))
                        rr -= 1
                        break
                    rr = max_r + 1
                    while rr < self.size and knowledge[rr][cols] == -1:
                        if (rr, cols) not in seen:
                            cand.append((rr, cols))
                            seen.add((rr, cols))
                        rr += 1
                        break
        return cand

    def _prob_of_hit(self, heat: List[List[int]]) -> float:
        total = sum(sum(row) for row in heat)
        return 0.0 if total <= 0 else 1.0 * max(max(row) for row in heat) / total

    def _best_counter_gain(self, player_knowledge_on_ai: List[List[int]], ai_remaining_ships: List[int]) -> float:
        # Estimate player's best immediate expected gain on AI's board
        heat_p = self.heatmap(player_knowledge_on_ai, ai_remaining_ships)
        total = sum(sum(row) for row in heat_p)
        if total <= 0:
            return 0.0
        best = 0
        best_r = best_c = -1
        for r in range(self.size):
            for c in range(self.size):
                if player_knowledge_on_ai[r][c] == -1 and heat_p[r][c] > best:
                    best = heat_p[r][c]
                    best_r, best_c = r, c
        return 0.0 if best <= 0 else best / total

    def choose_shot(
        self,
        player_board_knowledge: List[List[int]],
        player_shots_on_ai_board: List[List[int]],
        ai_remaining_ships: Optional[List[int]] = None,
    ) -> Tuple[int, int]:
        """
        Returns (r, c) to shoot at player's board.
        - player_board_knowledge: AI's knowledge grid of player's board (-1 unknown, 2 HIT, 3 MISS)
        - player_shots_on_ai_board: Player's knowledge of AI's board (-1 unknown, 2 HIT, 3 MISS)
        - ai_remaining_ships: Remaining ship lengths of AI (for estimating player's counterplay)
        """
        heat = self.heatmap(player_board_knowledge, self.remaining_ships)
        # Use target candidates if we have hit clusters
        target_cands = self._target_candidates(player_board_knowledge)
        candidates = target_cands or self._top_candidates(heat, player_board_knowledge)
        if not candidates:
            # Fallback random unknown
            for r in range(self.size):
                for c in range(self.size):
                    if player_board_knowledge[r][c] == -1:
                        return r, c
            return 0, 0

        # Estimate opponent's best immediate counter gain
        opp_gain = self._best_counter_gain(player_shots_on_ai_board, ai_remaining_ships or STANDARD_SHIPS)

        # Score each candidate by expected net gain
        total_heat = sum(sum(row) for row in heat)
        best_score = -1e9
        best_move = candidates[0]
        for r, c in candidates:
            phit = 0.0 if total_heat <= 0 else heat[r][c] / total_heat
            # Value of our hit is 1; miss is 0; subtract opponent best expected gain
            score = phit * 1.0 - opp_gain
            if score > best_score:
                best_score = score
                best_move = (r, c)
        return best_move
