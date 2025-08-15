
#!/usr/bin/env python3
"""
Classic Snake — standalone pygame implementation in a single Python file.

Basic features:
- Arrow keys / WASD to move
- Eat food to grow and increase score
- Collision with walls or self ends the game
- Clean grid-based movement with consistent speed
- Pause (P), Restart (R), Quit (ESC)
- Optional sound toggle (M) if mixer is available

Requires: pygame (pip install pygame)
"""
from __future__ import annotations

import os
import sys
import random
from dataclasses import dataclass
import math

# Try to import pygame with a friendly error if missing
try:
    import pygame
except ImportError as e:
    print("This game requires the 'pygame' package. Install it with:\n  pip install pygame\n\nError:", e)
    sys.exit(1)

# ---------------------------- Config ---------------------------------

GRID_SIZE = 25           # pixel size of one cell
GRID_COLS = 24           # number of columns
GRID_ROWS = 24           # number of rows
MARGIN    = 16           # outer margin around the playfield
START_LENGTH = 4         # starting snake length
TICK_RATE = 10           # base moves per second
SPEEDUP_EVERY = 5        # increase speed every N foods eaten
SPEEDUP_AMOUNT = 1       # how many ticks per second to add

# Colors (R, G, B)
BLACK   = (12, 12, 12)
BG_DARK = (20, 22, 26)
WHITE   = (240, 240, 240)
GRAY    = (130, 136, 148)
GREEN   = (76, 175, 80)
GREEN_D = (56, 142, 60)
RED     = (233, 69, 96)
RED_D   = (200, 50, 70)
YELLOW  = (255, 202, 40)

# Derived sizes
PLAY_W = GRID_COLS * GRID_SIZE
PLAY_H = GRID_ROWS * GRID_SIZE
WIN_W = PLAY_W + MARGIN * 2
WIN_H = PLAY_H + MARGIN * 2 + 64  # space for HUD

# ---------------------------- Helpers --------------------------------

@dataclass(frozen=True)
class Vec:
    x: int
    y: int

    def __add__(self, other: "Vec") -> "Vec":
        return Vec(self.x + other.x, self.y + other.y)

UP    = Vec(0, -1)
DOWN  = Vec(0, 1)
LEFT  = Vec(-1, 0)
RIGHT = Vec(1, 0)

OPPOSITE = {UP: DOWN, DOWN: UP, LEFT: RIGHT, RIGHT: LEFT}

# Allow hashing of Vec for set membership
Vec.__hash__ = lambda self: hash((self.x, self.y))

# ---------------------------- Game -----------------------------------

class SnakeGame:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Snake — classic")
        self.screen = pygame.display.set_mode((WIN_W, WIN_H))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 24)
        self.font_big = pygame.font.SysFont("consolas", 42, bold=True)

        # Optional sounds
        self.sound_on = False
        self.snd_eat = None
        self.snd_die = None
        try:
            pygame.mixer.init()
            self.snd_eat = self._make_beep(600, 0.08)
            self.snd_die = self._make_beep(120, 0.25)
            self.sound_on = True
        except Exception:
            self.sound_on = False

        # Menu state & options
        self.state = "menu"  # 'menu' | 'playing' | 'paused'
        self.menu_speed = TICK_RATE

        # Background music (optional)
        self.music_path = None
        self.music_loaded = False
        try:
            self.music_path = self._find_music_file()
            if self.music_path:
                pygame.mixer.music.load(self.music_path)
                pygame.mixer.music.set_volume(0.45)
                # Do not auto-play at launch; start when the player presses Start
                self.music_loaded = True
        except Exception:
            # If loading/playing fails, continue without music
            self.music_loaded = False

        # Explosion SFX (optional)
        self.snd_explosion = None
        try:
            exp_path = self._find_explosion_file()
            if exp_path:
                self.snd_explosion = pygame.mixer.Sound(exp_path)
                self.snd_explosion.set_volume(0.9)
        except Exception:
            self.snd_explosion = None

        # Death animation state
        self.death_particles = []
        self.death_anim_elapsed = 0.0

        self.reset()

    def reset(self, base_speed: int | None = None):
        cx = GRID_COLS // 2
        cy = GRID_ROWS // 2
        self.dir = RIGHT
        self.next_dir = RIGHT
        # Build initial snake centered, heading right
        self.snake: list[Vec] = [Vec(cx - i, cy) for i in range(START_LENGTH)]
        self.snake_set = set(self.snake)
        self.grow = 0
        self.score = 0
        self.best = 0
        self.moves_per_sec = base_speed if base_speed is not None else TICK_RATE
        self.spawn_food()
        self.alive = True
        self.paused = False
        self.time_since_step = 0.0

    def spawn_food(self):
        empty = [(x, y) for x in range(GRID_COLS) for y in range(GRID_ROWS)
                 if Vec(x, y) not in self.snake_set]
        if not empty:
            self.food = None
            return
        x, y = random.choice(empty)
        self.food = Vec(x, y)

    def _make_beep(self, freq: int, duration: float):
        # Generate a simple square beep in a Sound object
        import numpy as np
        sample_rate = 22050
        n = int(duration * sample_rate)
        t = (np.arange(n) / sample_rate)
        wave = ((np.sin(2 * np.pi * freq * t) > 0) * 2 - 1).astype("float32") * 0.2
        return pygame.sndarray.make_sound((wave * (2**15 - 1)).astype("int16"))

    def _find_music_file(self) -> str | None:
        """Find a music file in project root to play as background music.
        Preference order: a known filename placed by the user, then any mp3/ogg/wav/flac.
        """
        root = os.path.dirname(os.path.abspath(__file__))
        preferred = [
            "Lenny Pixels - Motherboard Encore - 8bit.mp3",
        ]
        for name in preferred:
            path = os.path.join(root, name)
            if os.path.isfile(path):
                return path
        exts = (".mp3", ".ogg", ".wav", ".flac", ".mod")
        try:
            for fname in sorted(os.listdir(root)):
                if fname.lower().endswith(exts):
                    return os.path.join(root, fname)
        except Exception:
            pass
        return None

    def _find_explosion_file(self) -> str | None:
        """Find an explosion sfx in root; prefer names starting with 'explosion'."""
        root = os.path.dirname(os.path.abspath(__file__))
        candidates: list[str] = []
        try:
            for fname in os.listdir(root):
                lower = fname.lower()
                if any(lower.endswith(ext) for ext in (".wav", ".ogg", ".mp3", ".flac")):
                    if lower.startswith("explosion") or "explosion" in lower:
                        candidates.append(fname)
        except Exception:
            return None
        if not candidates:
            return None
        # Prefer wav/ogg over mp3 for Sound compatibility
        def rank(name: str) -> int:
            n = name.lower()
            if n.endswith(".wav"): return 0
            if n.endswith(".ogg"): return 1
            if n.endswith(".flac"): return 2
            if n.endswith(".mp3"): return 3
            return 10
        best = sorted(candidates, key=rank)[0]
        return os.path.join(root, best)

    # ------------------------ Update & Logic -------------------------

    def handle_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit(0)
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE,):
                    pygame.quit(); sys.exit(0)

                # Menu keyboard controls
                if self.state == "menu":
                    if event.key in (pygame.K_LEFT, pygame.K_a):
                        self.menu_speed = max(1, self.menu_speed - 1)
                    elif event.key in (pygame.K_RIGHT, pygame.K_d):
                        self.menu_speed = min(60, self.menu_speed + 1)
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        self.start_game()
                        return
                    elif event.key in (pygame.K_m,):
                        self.sound_on = not self.sound_on
                        # Toggle music playback
                        if self.music_loaded:
                            try:
                                if not self.sound_on:
                                    pygame.mixer.music.pause()
                                else:
                                    if pygame.mixer.music.get_busy():
                                        pygame.mixer.music.unpause()
                                    else:
                                        pygame.mixer.music.play(-1)
                            except Exception:
                                pass
                        return
                elif self.state == "paused":
                    if event.key in (pygame.K_LEFT, pygame.K_a):
                        self.moves_per_sec = max(1, int(self.moves_per_sec) - 1)
                    elif event.key in (pygame.K_RIGHT, pygame.K_d):
                        self.moves_per_sec = min(60, int(self.moves_per_sec) + 1)
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        self.state = "playing"
                        self.paused = False
                        return
                    elif event.key in (pygame.K_m,):
                        self.sound_on = not self.sound_on
                        if self.music_loaded:
                            try:
                                if not self.sound_on:
                                    pygame.mixer.music.pause()
                                else:
                                    if pygame.mixer.music.get_busy():
                                        pygame.mixer.music.unpause()
                                    else:
                                        pygame.mixer.music.play(-1)
                            except Exception:
                                pass
                        return

                # In-game keyboard controls
                if event.key in (pygame.K_p,):
                    if self.alive:
                        if self.state == "playing":
                            self.state = "paused"
                            self.paused = True
                        elif self.state == "paused":
                            self.state = "playing"
                            self.paused = False
                if event.key in (pygame.K_m,):
                    self.sound_on = not self.sound_on
                    # Toggle music playback
                    if self.music_loaded:
                        try:
                            if not self.sound_on:
                                pygame.mixer.music.pause()
                            else:
                                if pygame.mixer.music.get_busy():
                                    pygame.mixer.music.unpause()
                                else:
                                    pygame.mixer.music.play(-1)
                        except Exception:
                            pass
                if event.key in (pygame.K_r,):
                    self.reset(base_speed=self.moves_per_sec)
                    self.state = "playing"
                    self.paused = False
                    # Ensure music is playing after restart if sound is on
                    if self.music_loaded and self.sound_on:
                        try:
                            if pygame.mixer.music.get_busy():
                                pygame.mixer.music.unpause()
                            else:
                                pygame.mixer.music.play(-1)
                        except Exception:
                            pass

                # Direction changes
                if event.key in (pygame.K_UP, pygame.K_w):
                    self.queue_dir(UP)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    self.queue_dir(DOWN)
                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    self.queue_dir(LEFT)
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    self.queue_dir(RIGHT)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.state in ("menu", "paused"):
                    self.handle_menu_click(event.pos)

    def queue_dir(self, d: Vec):
        if not self.alive:
            return
        if d == OPPOSITE.get(self.dir):
            return  # disallow 180 turns in one tick
        self.next_dir = d

    def step(self):
        if not self.alive or self.paused:
            return
        self.dir = self.next_dir
        head = self.snake[0]
        new_head = head + self.dir

        # Wall collision (classic — no wrap)
        if not (0 <= new_head.x < GRID_COLS and 0 <= new_head.y < GRID_ROWS):
            self.game_over(); return

        # Self collision
        if new_head in self.snake_set:
            self.game_over(); return

        # Move
        self.snake.insert(0, new_head)
        self.snake_set.add(new_head)

        if self.food and new_head == self.food:
            self.score += 1
            self.grow += 1
            if self.sound_on and self.snd_eat:
                self.snd_eat.play()
            if self.score % SPEEDUP_EVERY == 0:
                self.moves_per_sec += SPEEDUP_AMOUNT
            self.spawn_food()
        if self.grow > 0:
            self.grow -= 1
        else:
            tail = self.snake.pop()
            self.snake_set.remove(tail)

    def game_over(self):
        self.alive = False
        self.best = max(self.best, self.score)
        # Spawn disintegration particles
        try:
            self._create_death_particles()
            self.death_anim_elapsed = 0.0
            self.state = "dying"
        except Exception:
            # If anything goes wrong, fall back to direct game over
            self.state = "gameover"
        # Stop background music
        if self.music_loaded:
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass
        # Play explosion sfx if available, else fallback to die beep
        if self.sound_on:
            try:
                if self.snd_explosion is not None:
                    self.snd_explosion.play()
                elif self.snd_die is not None:
                    self.snd_die.play()
            except Exception:
                pass

    # --------------------------- Draw --------------------------------

    def draw_grid(self):
        # Background
        self.screen.fill(BG_DARK)
        # Playfield
        pf_rect = pygame.Rect(MARGIN, MARGIN, PLAY_W, PLAY_H)
        pygame.draw.rect(self.screen, BLACK, pf_rect, border_radius=10)

        # Subtle grid lines
        for x in range(GRID_COLS + 1):
            px = MARGIN + x * GRID_SIZE
            pygame.draw.line(self.screen, (30, 33, 38), (px, MARGIN), (px, MARGIN + PLAY_H))
        for y in range(GRID_ROWS + 1):
            py = MARGIN + y * GRID_SIZE
            pygame.draw.line(self.screen, (30, 33, 38), (MARGIN, py), (MARGIN + PLAY_W, py))

    def draw_block(self, cell: Vec, color, inset=2):
        r = pygame.Rect(
            MARGIN + cell.x * GRID_SIZE + inset,
            MARGIN + cell.y * GRID_SIZE + inset,
            GRID_SIZE - inset * 2,
            GRID_SIZE - inset * 2,
        )
        pygame.draw.rect(self.screen, color, r, border_radius=6)

    def draw(self):
        if self.state in ("menu", "paused"):
            self.draw_menu()
            pygame.display.flip()
            return
        if self.state == "dying":
            # Draw grid and death particles
            self.draw_grid()
            self._draw_death_particles()
            self._draw_hud()
            pygame.display.flip()
            return

        self.draw_grid()

        # Food
        if self.food:
            self.draw_block(self.food, RED)

        # Snake
        for i, c in enumerate(self.snake):
            color = GREEN if i == 0 else GREEN_D
            self.draw_block(c, color)

        # HUD
        self._draw_hud()

        # Game over overlay (only after death animation completes)
        if self.state == "gameover":
            overlay = pygame.Surface((PLAY_W, PLAY_H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            self.screen.blit(overlay, (MARGIN, MARGIN))
            text = self.font_big.render("GAME OVER", True, YELLOW)
            sub = self.font.render("Press R to restart", True, WHITE)
            self.screen.blit(text, (MARGIN + (PLAY_W - text.get_width()) // 2,
                                    MARGIN + (PLAY_H - text.get_height()) // 2 - 12))
            self.screen.blit(sub, (MARGIN + (PLAY_W - sub.get_width()) // 2,
                                   MARGIN + (PLAY_H - sub.get_height()) // 2 + 28))

        pygame.display.flip()

    # --------------------------- Menu ---------------------------------

    def get_menu_layout(self):
        # Compute and return rects for menu UI elements
        center_x = WIN_W // 2
        title_y = MARGIN + 40
        controls_y = title_y + 80
        buttons_y = controls_y + 90

        # Speed controls
        speed_label_rect = pygame.Rect(center_x - 140, controls_y - 10, 280, 40)
        minus_rect = pygame.Rect(center_x - 110, controls_y + 36, 48, 42)
        plus_rect = pygame.Rect(center_x + 62, controls_y + 36, 48, 42)
        speed_value_rect = pygame.Rect(center_x - 50, controls_y + 36, 100, 42)

        # Start button
        start_rect = pygame.Rect(center_x - 90, buttons_y + 30, 180, 52)

        return {
            "speed_label": speed_label_rect,
            "minus": minus_rect,
            "plus": plus_rect,
            "speed_value": speed_value_rect,
            "start": start_rect,
        }

    def draw_button(self, rect: pygame.Rect, label: str, *, primary=False):
        mouse_pos = pygame.mouse.get_pos()
        hovered = rect.collidepoint(mouse_pos)
        base = (60, 65, 72) if not primary else (76, 175, 80)
        base_hover = (80, 86, 94) if not primary else (56, 142, 60)
        color = base_hover if hovered else base
        pygame.draw.rect(self.screen, color, rect, border_radius=8)
        pygame.draw.rect(self.screen, (30, 33, 38), rect, width=2, border_radius=8)
        text_color = WHITE if primary else WHITE
        surf = self.font.render(label, True, text_color)
        self.screen.blit(surf, (rect.centerx - surf.get_width() // 2,
                                rect.centery - surf.get_height() // 2))

    def draw_menu(self):
        # Background & panel
        self.screen.fill(BG_DARK)
        panel = pygame.Rect(MARGIN, MARGIN, WIN_W - 2 * MARGIN, WIN_H - 2 * MARGIN)
        pygame.draw.rect(self.screen, BLACK, panel, border_radius=12)

        layout = self.get_menu_layout()

        # Title
        title_text = "SNAKE" if self.state == "menu" else "PAUSED"
        title = self.font_big.render(title_text, True, YELLOW)
        self.screen.blit(title, (panel.centerx - title.get_width() // 2, MARGIN + 40))

        # Speed label
        label_text = "Starting Speed (moves per second)" if self.state == "menu" else "Speed (moves per second)"
        label = self.font.render(label_text, True, GRAY)
        self.screen.blit(label, (panel.centerx - label.get_width() // 2, MARGIN + 120))

        # Speed controls
        self.draw_button(layout["minus"], "−")
        self.draw_button(layout["plus"], "+")
        current_speed = self.menu_speed if self.state == "menu" else int(self.moves_per_sec)
        val_surf = self.font.render(str(current_speed), True, WHITE)
        pygame.draw.rect(self.screen, (40, 44, 52), layout["speed_value"], border_radius=8)
        pygame.draw.rect(self.screen, (30, 33, 38), layout["speed_value"], width=2, border_radius=8)
        self.screen.blit(val_surf, (layout["speed_value"].centerx - val_surf.get_width() // 2,
                                    layout["speed_value"].centery - val_surf.get_height() // 2))

        # Start button
        btn_label = "Start" if self.state == "menu" else "Resume"
        self.draw_button(layout["start"], btn_label, primary=True)

        # Footer help
        help_line = "Left/Right adjust • Enter/Space start • M toggle sound • ESC quit" if self.state == "menu" else "Left/Right adjust • Enter/Space resume • M toggle sound • ESC quit"
        help_text = self.font.render(help_line, True, GRAY)
        self.screen.blit(help_text, (panel.centerx - help_text.get_width() // 2, WIN_H - MARGIN - 34))

    def handle_menu_click(self, pos):
        layout = self.get_menu_layout()
        if layout["minus"].collidepoint(pos):
            if self.state == "menu":
                self.menu_speed = max(1, self.menu_speed - 1)
            else:
                self.moves_per_sec = max(1, int(self.moves_per_sec) - 1)
        elif layout["plus"].collidepoint(pos):
            if self.state == "menu":
                self.menu_speed = min(60, self.menu_speed + 1)
            else:
                self.moves_per_sec = min(60, int(self.moves_per_sec) + 1)
        elif layout["start"].collidepoint(pos):
            if self.state == "menu":
                self.start_game()
            else:
                self.state = "playing"
                self.paused = False

    def start_game(self):
        # Begin playing with chosen speed
        self.reset(base_speed=self.menu_speed)
        self.state = "playing"
        # Start background music on first start (and subsequent starts) if enabled
        if self.music_loaded and self.sound_on:
            try:
                if pygame.mixer.music.get_busy():
                    pygame.mixer.music.unpause()
                else:
                    pygame.mixer.music.play(-1)
            except Exception:
                pass

    # --------------------------- Loop ---------------------------------

    def run(self):
        step_timer = 0.0
        while True:
            dt = self.clock.tick(60) / 1000.0  # seconds since last frame
            self.handle_input()
            if self.state == "playing":
                step_timer += dt
                step_len = 1.0 / float(self.moves_per_sec)
                while step_timer >= step_len:
                    self.step()
                    step_timer -= step_len
            elif self.state == "dying":
                if self._update_death(dt):
                    # Transition to gameover screen after animation
                    self.state = "gameover"
            self.draw()

    # --------------------------- HUD/Helpers -------------------------

    def _draw_hud(self):
        hud_y = MARGIN + PLAY_H + 8
        msg = f"Score: {self.score}    Best: {self.best}    Speed: {self.moves_per_sec}"
        if self.state == "paused":
            msg += "    [PAUSED]"
        surf = self.font.render(msg, True, WHITE)
        self.screen.blit(surf, (MARGIN, hud_y))

        help_line = "Arrows/WASD move • P pause • R restart • M sound • ESC quit"
        help_s = self.font.render(help_line, True, GRAY)
        self.screen.blit(help_s, (MARGIN, hud_y + 26))

    # --------------------- Death Animation ---------------------------

    def _create_death_particles(self):
        self.death_particles.clear()
        rng = random.Random()
        # Generate particles from each snake segment
        for i, c in enumerate(self.snake):
            cx = MARGIN + c.x * GRID_SIZE + GRID_SIZE / 2
            cy = MARGIN + c.y * GRID_SIZE + GRID_SIZE / 2
            n = 3 + (1 if i == 0 else 0)  # head slightly more
            for _ in range(n):
                angle = rng.uniform(0, 2 * 3.1415926)
                speed = rng.uniform(80, 220)
                vx = speed * float(math.cos(angle))
                vy = speed * float(math.sin(angle))
                life = rng.uniform(0.6, 1.2)
                col = GREEN if i == 0 else GREEN_D
                self.death_particles.append({
                    "x": cx,
                    "y": cy,
                    "vx": vx,
                    "vy": vy,
                    "life": life,
                    "max_life": life,
                    "col": col,
                })

    def _update_death(self, dt: float) -> bool:
        # Returns True when the animation is finished
        self.death_anim_elapsed += dt
        still_alive = 0
        gravity = 380.0
        drag = 0.98
        for p in self.death_particles:
            if p["life"] <= 0:
                continue
            p["life"] -= dt
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["vy"] += gravity * dt
            p["vx"] *= drag
            p["vy"] *= drag
            if p["life"] > 0:
                still_alive += 1
        # Finish when no particles alive or after 1.6s
        return still_alive == 0 or self.death_anim_elapsed >= 1.6

    def _draw_death_particles(self):
        for p in self.death_particles:
            if p["life"] <= 0:
                continue
            t = max(0.0, min(1.0, p["life"] / p["max_life"]))
            col = p["col"]
            color = (int(col[0] * t + 10), int(col[1] * t + 10), int(col[2] * t + 10))
            size = max(2, int(GRID_SIZE * 0.22))
            r = pygame.Rect(int(p["x"]) - size // 2, int(p["y"]) - size // 2, size, size)
            pygame.draw.rect(self.screen, color, r, border_radius=3)

# ---------------------------- Entry ----------------------------------

def main():
    game = SnakeGame()
    game.run()

if __name__ == "__main__":
    main()
