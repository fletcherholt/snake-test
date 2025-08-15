# Snake Game

This is a classic Snake game implemented in Python using Pygame.

## Features
- Arrow keys / WASD to move
- Eat food to grow and increase score
- Collision with walls or self ends the game
- Clean grid-based movement with consistent speed
- Pause (P), Restart (R), Quit (ESC)
- Optional sound toggle (M) if mixer is available

## Requirements
- Python 3.7+
- [pygame](https://www.pygame.org/)
- [numpy](https://numpy.org/)

## Setup

1. **Install dependencies** (already installed if you used the setup script):
	```bash
	pip install pygame numpy
	```

2. **Run the game:**
	```bash
	python snake.py
	```
	If you are using the provided virtual environment, use:
	```bash
	.venv/bin/python snake.py
	```

## Controls
- Arrow keys or WASD: Move
- P: Pause
- R: Restart
- M: Toggle sound
- ESC: Quit

## Download
Get the packaged ZIP of the latest release:

- v1.0: https://github.com/fletcherholt/snake-test/archive/refs/tags/v1.0.zip

## Troubleshooting

Here are quick fixes for common issues when running the game.

### 1) Double‑click opens the file in an editor, not the game
Run it from Terminal instead of double‑clicking:

```bash
cd /Users/holt/snake-test
./.venv/bin/python snake.py
```

If you don’t have the venv yet, create it and install deps:

```bash
cd /Users/holt/snake-test
python3 -m venv .venv
./.venv/bin/pip install --upgrade pip
./.venv/bin/pip install pygame numpy
./.venv/bin/python snake.py
```

### 2) "ModuleNotFoundError: No module named 'pygame'"
You’re likely using a different Python than your venv.

```bash
./.venv/bin/pip install pygame
./.venv/bin/python -c "import pygame, sys; print(pygame.__version__, sys.executable)"
```

If install fails on macOS Apple Silicon, try upgrading build tools and reinstalling:

```bash
./.venv/bin/pip install --upgrade pip setuptools wheel
./.venv/bin/pip install pygame
```

### 3) No sound or music
- Press M to toggle sound on/off.
- Check macOS output volume and device.
- Custom SFX/music should be placed in the project root (same folder as `snake.py`).
- Prefer `.wav`/`.ogg` for sound effects; `.mp3` is fine for background music but can be less reliable for short SFX on some setups.
- If the mixer won’t initialize on macOS, try forcing the CoreAudio driver and run again:

```bash
export SDL_AUDIODRIVER=coreaudio
./.venv/bin/python snake.py
```

### 4) Window doesn’t open / pygame error about video system
- Make sure you’re not running over SSH/headless.
- Close other full‑screen apps that might grab exclusive display.
- Update pygame:

```bash
./.venv/bin/pip install --upgrade pygame
```

### 5) Controls don’t respond or the game looks paused
- On the start screen, press Enter or Space to begin.
- P toggles pause. If paused, HUD says “Paused”.
- Arrow keys or WASD move the snake.

### 6) Best score won’t update or looks wrong
Delete the best score file and it will be recreated next run:

```bash
rm -f .snake_best
```

### 7) The window is too big for my display
Reduce the grid size constant at the top of `snake.py` (e.g., `GRID_SIZE = 20`) and run again.

### 8) Still stuck? Share the exact Terminal output
Run the game from Terminal and copy the full error/traceback; include your macOS version and Python version:

```bash
sw_vers
./.venv/bin/python --version
./.venv/bin/python snake.py
```


