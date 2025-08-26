import math
import random
import sys

import pygame

from ai import BattleshipAI
from board import EMPTY, HIT, MISS, SHIP, Board
from constants import ACCENT, BLACK, CELL_SIZE, FPS, GAP, GRID_LINE, GRID_SIZE
from constants import HIT as COLOR_HIT
from constants import MARGIN
from constants import MISS as COLOR_MISS
from constants import SCREEN_HEIGHT, SCREEN_WIDTH
from constants import SHIP as COLOR_SHIP
from constants import STANDARD_SHIPS, TEXT, WATER, WHITE
from sounds import load_sounds


def draw_grid(surface, top_left, board: Board, reveal_ships: bool = False):
    x0, y0 = top_left
    # Background water
    pygame.draw.rect(
        surface,
        WATER,
        pygame.Rect(x0 - 2, y0 - 2, GRID_SIZE * CELL_SIZE +
                    4, GRID_SIZE * CELL_SIZE + 4),
        border_radius=6,
    )

    # Cells
    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            rect = pygame.Rect(x0 + c * CELL_SIZE, y0 + r *
                               CELL_SIZE, CELL_SIZE - 1, CELL_SIZE - 1)
            val = board.grid[r][c]
            color = WATER
            if val == HIT:
                color = COLOR_HIT
            elif val == MISS:
                color = COLOR_MISS
            elif val == SHIP and reveal_ships:
                color = COLOR_SHIP
            else:
                color = WATER
            pygame.draw.rect(surface, color, rect, border_radius=3)

    # Grid lines
    for i in range(GRID_SIZE + 1):
        pygame.draw.line(
            surface,
            GRID_LINE,
            (x0, y0 + i * CELL_SIZE),
            (x0 + GRID_SIZE * CELL_SIZE, y0 + i * CELL_SIZE),
            1,
        )
        pygame.draw.line(
            surface,
            GRID_LINE,
            (x0 + i * CELL_SIZE, y0),
            (x0 + i * CELL_SIZE, y0 + GRID_SIZE * CELL_SIZE),
            1,
        )


def pos_to_cell(pos, top_left):
    x, y = pos
    x0, y0 = top_left
    if not (x0 <= x < x0 + GRID_SIZE * CELL_SIZE and y0 <= y < y0 + GRID_SIZE * CELL_SIZE):
        return None
    c = (x - x0) // CELL_SIZE
    r = (y - y0) // CELL_SIZE
    return int(r), int(c)


def render_text(surface, font, text, pos, color=TEXT):
    img = font.render(text, True, color)
    surface.blit(img, pos)


class Game:
    def __init__(self):
        # Configure audio first for best latency
        pygame.mixer.pre_init(22050, -16, 1, 256)
        pygame.init()
        pygame.display.set_caption("Battleship - Player vs AI")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 20)
        self.big_font = pygame.font.SysFont("consolas", 28, bold=True)

        self.left_origin = (MARGIN, MARGIN)
        self.right_origin = (MARGIN + GRID_SIZE * CELL_SIZE + GAP, MARGIN)

        # Sounds
        self.sfx = load_sounds()

        self.reset()

    def reset(self):
        self.player_board = Board()
        self.ai_board = Board()
        self.player_board.random_place_all(list(STANDARD_SHIPS))
        self.ai_board.random_place_all(list(STANDARD_SHIPS))
        self.ai = BattleshipAI()
        self.state = "ready"  # ready -> player_turn -> ai_turn -> game_over
        self.message = "Press SPACE to start. Press R to reroll."
        self.player_turn_ready = True
        self.ai_move_cooldown = 0
        self.winner = None
        self.hover_cell = None
        self.last_player_shot = None  # (r, c)
        self.last_ai_shot = None      # (r, c)
        self.particles = []  # list of dicts
        self.time_ms = 0

    def start(self):
        if self.state == "ready":
            self.state = "player_turn"
            self.message = "Your turn: click a cell on the right grid."
            self._play("start")

    def reroll(self):
        if self.state == "ready":
            self.player_board.random_place_all(list(STANDARD_SHIPS))
            self.ai_board.random_place_all(list(STANDARD_SHIPS))
            self.ai = BattleshipAI()

    def update(self, dt):
        self.time_ms += dt
        self._update_particles(dt)
        if self.state == "ai_turn":
            self.ai_move_cooldown -= dt
            if self.ai_move_cooldown <= 0:
                self.ai_take_shot()

    def ai_take_shot(self):
        # AI chooses shot on player's board
        player_knowledge = self.player_board.get_ai_knowledge()
        player_view_of_ai = self.ai_board.get_ai_knowledge()
        r, c = self.ai.choose_shot(player_knowledge, player_view_of_ai, ai_remaining_ships=[
                                   s.length for s in self.ai_board.ships if not s.sunk])
        hit, sunk_len, game_over = self.player_board.receive_shot(r, c)
        self.last_ai_shot = (r, c)
        if hit:
            self._play("hit")
            self._spawn_hit_effect(self.left_origin, r, c)
            if sunk_len:
                self._play("sunk")
        else:
            self._play("miss")
            self._spawn_miss_ripple(self.left_origin, r, c)
        if sunk_len:
            # Player ship sunk does not affect AI remaining_ships (AI tracks opponent's ships separately)
            pass
        if game_over:
            self.state = "game_over"
            self.winner = "AI"
            self.message = "AI wins! Press N for new game."
            return

        # Only switch turns if AI missed
        if hit:
            self.state = "ai_turn"
            self.message = "AI hit! AI gets another turn..."
            self.ai_move_cooldown = 350  # ms for next AI move
        else:
            self.state = "player_turn"
            self.message = "Your turn: click a cell on the right grid."

    def handle_player_shot(self, cell):
        if not cell:
            return
        r, c = cell
        if not self.ai_board.is_valid_shot(r, c):
            return
        self._play("click")
        hit, sunk_len, game_over = self.ai_board.receive_shot(r, c)
        self.last_player_shot = (r, c)
        if hit:
            self._play("hit")
            self._spawn_hit_effect(self.right_origin, r, c)
            if sunk_len:
                self._play("sunk")
        else:
            self._play("miss")
            self._spawn_miss_ripple(self.right_origin, r, c)
        if sunk_len:
            # Inform AI it sunk one of the opponent's ships (from AI's perspective)
            self.ai.notify_sunk(sunk_len)
        if game_over:
            self.state = "game_over"
            self.winner = "Player"
            self.message = "You win! Press N for new game."
            return

        # Only switch turns if player missed
        if hit:
            self.state = "player_turn"
            self.message = "Hit! You get another turn: click a cell on the right grid."
        else:
            # Switch to AI after a short delay
            self.state = "ai_turn"
            self.message = "AI thinking..."
            self.ai_move_cooldown = 350  # ms

    # --- Audio helpers ---
    def _play(self, key: str):
        s = self.sfx.get(key)
        if s:
            try:
                s.play()
            except pygame.error:
                pass

    # --- Visual effects ---
    def _cell_center(self, origin, r, c):
        x0, y0 = origin
        cx = x0 + c * CELL_SIZE + CELL_SIZE // 2
        cy = y0 + r * CELL_SIZE + CELL_SIZE // 2
        return cx, cy

    def _spawn_hit_effect(self, origin, r, c):
        cx, cy = self._cell_center(origin, r, c)
        for _ in range(12):
            ang = random.random() * math.tau
            speed = random.uniform(0.08, 0.22)  # px per ms
            life = random.randint(300, 550)     # ms
            self.particles.append({
                "x": cx,
                "y": cy,
                "vx": math.cos(ang) * speed,
                "vy": math.sin(ang) * speed,
                "life": life,
                "max": life,
                "color": (220, random.randint(80, 110), 70),
                "radius": random.randint(2, 4),
            })

    def _spawn_miss_ripple(self, origin, r, c):
        cx, cy = self._cell_center(origin, r, c)
        self.particles.append({
            "type": "ripple",
            "x": cx,
            "y": cy,
            "life": 500,
            "max": 500,
            "radius": 4,
            "color": (200, 220, 255),
        })

    def _update_particles(self, dt):
        alive = []
        for p in self.particles:
            p["life"] -= dt
            if p["life"] <= 0:
                continue
            if p.get("type") == "ripple":
                p["radius"] += 0.05 * dt
            else:
                p["x"] += p["vx"] * dt
                p["y"] += p["vy"] * dt
                p["vy"] += 0.0003 * dt  # slight gravity
            alive.append(p)
        self.particles = alive

    def draw(self):
        self.screen.fill(BLACK)
        # Titles
        render_text(self.screen, self.big_font, "Your Fleet",
                    (self.left_origin[0], self.left_origin[1] - 28), ACCENT)
        render_text(self.screen, self.big_font, "Enemy Waters",
                    (self.right_origin[0], self.right_origin[1] - 28), ACCENT)

        draw_grid(self.screen, self.left_origin,
                  self.player_board, reveal_ships=True)

        # For enemy board we draw public view (ships hidden). Clone a temporary board for drawing simplicity
        draw_grid(self.screen, self.right_origin,
                  self.ai_board, reveal_ships=False)

        # Hover highlight on enemy grid
        if self.state == "player_turn" and self.hover_cell:
            r, c = self.hover_cell
            if 0 <= r < GRID_SIZE and 0 <= c < GRID_SIZE and self.ai_board.is_valid_shot(r, c):
                surf = pygame.Surface(
                    (CELL_SIZE - 2, CELL_SIZE - 2), pygame.SRCALPHA)
                surf.fill((255, 255, 255, 28))
                x0, y0 = self.right_origin
                self.screen.blit(
                    surf, (x0 + c * CELL_SIZE + 1, y0 + r * CELL_SIZE + 1))

        # Last shot pulse indicators
        self._draw_pulse_marker(self.right_origin, self.last_player_shot)
        self._draw_pulse_marker(self.left_origin, self.last_ai_shot)

        # Message line
        render_text(self.screen, self.font, self.message,
                    (MARGIN, MARGIN + GRID_SIZE * CELL_SIZE + 12))

        # Footer controls
        render_text(
            self.screen,
            self.font,
            "SPACE: start  R: reroll setup  N: new game",
            (MARGIN, MARGIN + GRID_SIZE * CELL_SIZE + 40),
        )

        # Particles/effects
        self._draw_particles()

        # Game over banner
        if self.state == "game_over" and self.winner:
            banner = f"Game Over - {self.winner} wins"
            img = self.big_font.render(banner, True, TEXT)
            rect = img.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 40))
            self.screen.blit(img, rect)

        pygame.display.flip()

    def _draw_particles(self):
        for p in self.particles:
            life_ratio = max(0.0, min(1.0, p["life"] / p["max"]))
            if p.get("type") == "ripple":
                alpha = int(90 * life_ratio)
                color = (*p["color"], alpha)
                surf = pygame.Surface(
                    (CELL_SIZE * 2, CELL_SIZE * 2), pygame.SRCALPHA)
                pygame.draw.circle(
                    surf, color, (CELL_SIZE, CELL_SIZE), int(p["radius"]))
                self.screen.blit(
                    surf, (p["x"] - CELL_SIZE, p["y"] - CELL_SIZE))
            else:
                # sparks
                r = max(1, int(p["radius"] * (0.5 + 0.5 * life_ratio)))
                pygame.draw.circle(
                    self.screen, p["color"], (int(p["x"]), int(p["y"])), r)

    def _draw_pulse_marker(self, origin, cell):
        if not cell:
            return
        r, c = cell
        cx, cy = self._cell_center(origin, r, c)
        t = (self.time_ms % 1000) / 1000.0
        radius = int(6 + 4 * (1 - abs(0.5 - t) * 2))
        color = (255, 255, 255)
        pygame.draw.circle(self.screen, color, (cx, cy), radius, 1)

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    if event.key == pygame.K_SPACE:
                        self.start()
                    if event.key == pygame.K_r:
                        self.reroll()
                    if event.key == pygame.K_n:
                        self.reset()
                elif event.type == pygame.MOUSEMOTION:
                    self.hover_cell = pos_to_cell(event.pos, self.right_origin)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.state == "player_turn":
                        cell = pos_to_cell(event.pos, self.right_origin)
                        self.handle_player_shot(cell)

            self.update(dt)
            self.draw()

        pygame.quit()
        sys.exit(0)


if __name__ == "__main__":
    Game().run()
