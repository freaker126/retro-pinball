# 🕹️ PyPinball: Retro Vector Arcade Pinball

An authentic, single-table, top-view **black & white retro pinball game** built in Python with **pygame-ce**. Designed from the ground up to be **clean, modular, and educational** so that you can learn Python, 2D physics simulation, procedural sound synthesis, and binary file generation by studying the source code.

---

## ⚡ Quick Start: How to Run

1. Open your terminal and change directory to the game folder:
   ```bash
   cd pypinball
   ```

2. Run the game:
   ```bash
   python3 main.py
   ```

3. To run the automated unit and headless integration test suite:
   ```bash
   python3 test_pypinball.py
   ```

---

## 🎮 Controls

| Key | Action | Description |
| :--- | :--- | :--- |
| **`[A]` / `[Z]` / `[←]` Left Arrow** | **Left Flipper** | Energizes left flipper solenoid upward |
| **`[D]` / `[/]` / `[→]` Right Arrow** | **Right Flipper** | Energizes right flipper solenoid upward |
| **`[SPACE]` / `[↓]` Down Arrow** | **Plunger Spring** | Hold to compress spring in shooter lane; release to launch ball |
| **`[W]` / `[T]` / `[SPACE]`** | **Table Nudge** | Bump table during play *(Nudging too fast triggers `TILT!`)* |
| **`[H]`** | **Hall of Fame** | View the persistent Top Scores leaderboard |
| **`[M]`** | **Mute / Unmute Music** | Toggle the retro arcade MIDI soundtrack |
| **`[S]`** | **Mute / Unmute SFX** | Toggle procedural sound effects |
| **`[ESC]`** | **Menu / Quit** | Return to title screen or exit |

---

## 📐 Table Layout & Rules of Play

```
              [ CEILING ARCH ]
             /   (1) (2) (3)   \
 [SPINNER]  /  ROLLOVER LANES   \  [SHOOTER]
    ==     |     (B1)   (B2)     |  [  LANE ]
           |         (B3)        |  [       ]
  [TARGET] |     POP BUMPERS     |  [  ONE- ]
  [ BANK ] |                     |  [  WAY  ]
  [ ===  ] |    / \       / \    |  [  GATE ]
           |   / L \     / R \   |  [   |   ]
           |  /SLING\   /SLING\  |  [   |   ]
   [OUT]   | |       | |       | |  [   |   ]
   [IN ]   | |IN  OUT| |OUT  IN| |  [PLUNGER]
           \  \_____/   \_____/  /  [ SPRING]
            \   \__       __/   /
             \     \FLIP/      /
              \____[DRAIN]____/
```

### 1. The Shooter Lane & One-Way Wire Gate
- When a ball is loaded, hold `[SPACE]` or `[↓]` to draw back the spring plunger.
- Releasing fires the spring, blasting the ball up the shooter lane and around the top arch.
- A **one-way wire flap** prevents the ball from dropping back into the plunger lane once it enters the playfield.

### 2. The Pop Bumper Trio (100 Pts Each)
- Three active circular electromagnets arranged in a triangle.
- Striking any bumper flashes bright white with an expanding vector shockwave ring and propels the ball away with an explosive outward impulse.

### 3. Slingshots (50 Pts)
- Triangular rubber kickers above each flipper.
- Striking the angled rubber face kicks the ball diagonally across the playfield with rubber snap audio.

### 4. 4-Target Drop Bank (250 Pts Each + 5,000 Pt Bonus)
- A bank of 4 stand-up targets along the upper-left wall.
- Knocking down all 4 targets triggers the **Bank Cleared Fanfare** and awards a **5,000 Point Bonus**, followed by an automatic pop-up target reset.

### 5. Rollover Lanes & Bonus Multiplier (500 Pts Each + 3,000 Bonus)
- Three numbered rollover lanes `[ 1 ]`, `[ 2 ]`, and `[ 3 ]` below the top ceiling arch.
- Rolling over a lane lights its indicator.
- Lighting all three lanes increments your **Bonus Multiplier** (`2X` ➔ `3X` ➔ `5X`), awards a **3,000 Point Bonus**, and resets the lane lights.

### 6. Upper Orbit Spinner Gate (40 Pts per Revolution)
- Situated on the upper left loop entrance.
- High-velocity shots spin the gate blade into a rapid blur with high-speed clicks and continuous point scoring.

### 7. Inlanes & Outlanes
- **Inlanes (300 Pts)**: Return the ball safely down the wire guide directly to the flippers.
- **Outlanes (1,000 Pts)**: Dangerous side drain lanes that bypass the flippers.

### 8. Nudge & Tilt Penalty
- Press `[W]` or `[T]` to bump the table cabinet when the ball is heading toward an outlane or drain.
- Nudging too frequently inside a short cooldown window triggers `TILT!`: flippers go completely dead, active bumpers stop scoring, and the ball drains into the trough.

### 9. Extra Ball Reward
- Surpassing **100,000 Points** awards an **EXTRA BALL**!

---

## 🏆 Top Scores & Retro Name Entry

- High scores are saved persistently in [`highscores.json`](file:///Users/along123/PyProjects/pypinball/highscores.json).
- When a 3-ball game ends, if your score ranks among the Top 8 on the leaderboard:
  1. An interactive retro arcade 3-letter initials screen appears (`_ _ _`).
  2. Use `[↑]` / `[↓]` (or type letters directly) to change letters, and `[ENTER]` or `[SPACE]` to lock in your name.
  3. Your score is permanently recorded on the **Hall of Fame** leaderboard!

---

## 📂 Project Architecture

```
pypinball/
├── constants.py         # Physics parameters, window size, colors, scoring rules
├── physics.py           # 2D vector math, segment collision, circle collision, reflection
├── entities.py          # Ball, Flipper, Bumper, Slingshot, TargetBank, RolloverLane, Plunger
├── table.py             # Playfield layout, walls, arches, wire guides, drain sensor
├── audio.py             # Procedural sound synthesizer & pure-Python MIDI file generator
├── highscores.py        # JSON leaderboard persistence, ranking, defensive file I/O
├── game.py              # Finite State Machine, sub-step physics update loop, vector renderer
├── main.py              # Master game loop (Input -> Update -> Render -> Clock tick)
├── test_pypinball.py    # 15 automated headless unit & integration tests
├── pypinball_theme.mid  # Generated 16-bar retro arcade MIDI soundtrack
└── README.md            # You are here!
```

---

## 🧠 Educational Guide: What You Can Learn from This Codebase

Studying `pypinball` provides practical examples of real-world software design patterns and game engineering concepts in Python:

### 1. The Master Game Loop (`main.py`)
Almost every real-time simulation relies on the classic 3-phase game loop:
```python
while running:
    dt = clock.tick(FPS) / 1000.0   # Measure elapsed seconds
    for event in pygame.event.get(): # 1. Process Input
        handle_input(event)
    update(dt)                       # 2. Advance Physics & State
    render()                         # 3. Draw Scene to Back Buffer
    pygame.display.flip()            # Swap buffer to display
```

### 2. Preventing Ball Tunneling via Sub-Stepping (`game.py`, `physics.py`)
In pinball, balls can reach velocities of $1,200 \text{ px/s}$. At 60 FPS, a ball moves up to 20 pixels in a single frame, which can cause it to "tunnel" (phase through) thin walls or fast flippers.
To solve this, we divide each frame's `dt` into 8 sub-steps:
```python
dt_sub = dt / PHYSICS_SUB_STEPS
for _ in range(PHYSICS_SUB_STEPS):
    table.update_physics_substep(dt_sub)
```

### 3. Vector Dot Product Projection (`physics.py`)
To test if a circular ball collides with a line segment $A \to B$:
1. Vector from $A$ to ball center $C$: $V = C - A$.
2. Segment vector: $S = B - A$.
3. The normalized scalar projection parameter $t$ is calculated via dot product:
   $$t = \text{clamp}\left(\frac{V \cdot S}{\|S\|^2}, 0.0, 1.0\right)$$
4. The closest point on the segment is $Q = A + t \times S$.
5. If the distance $\|C - Q\| < \text{radius}$, a collision occurred!

### 4. Flipper Kinematics & Angular Momentum (`entities.py`)
When a flipper rotates around pivot $P$ at angular velocity $\omega$:
- A contact point at distance $s$ along the arm moves with linear velocity:
  $$V_{\text{flipper}} = \omega \cdot s \cdot (-\sin\theta, \cos\theta)$$
- The ball's relative velocity is reflected, and $V_{\text{flipper}}$ is added back.
- This creates authentic pinball behavior: flipping while contacting the ball near the tip sends it soaring!

### 5. Pure-Python Procedural Sound Synthesis (`audio.py`)
Rather than depending on external audio files, all sound effects are synthesized from mathematical waveforms:
- **Sine Wave** (`math.sin`): Pure musical chimes (bumpers, bells).
- **Square Wave**: Authentic 8-bit retro arcade tones.
- **Frequency Sweep**: Downward pitch drops (slingshot recoil, drain slide).
- **White Noise** (`random.random`): Explosive mechanical impacts and clicks.
The samples are packed into signed 16-bit PCM stereo buffers (`array.array('h')`) and passed to `pygame.mixer.Sound(buffer=...)`.

### 6. Binary MIDI File Construction (`audio.py`)
The game composes its own 16-bar retro soundtrack and encodes it into a standard binary MIDI file (`.mid`):
- Uses Python's `struct.pack` to generate big-endian binary chunks (`MThd` and `MTrk`).
- Implements **Variable-Length Quantity (VLQ)** encoding for delta timestamps.
- Sequences Bass (Ch 1), Square Lead (Ch 0), and Drums (Ch 9).

### 7. Defensive Persistence with JSON (`highscores.py`)
- Reads and writes structured leaderboard data using `json.load()` and `json.dump()`.
- Implements defensive fallbacks: if `highscores.json` is missing or corrupted, the game catches the error and restores default scores without crashing.

---

## 🧪 Running the Tests

To verify that all physics math, entities, sound synthesis, MIDI generation, and game loop state transitions are functioning correctly:

```bash
python3 test_pypinball.py
```

Expected output:
```
...............
----------------------------------------------------------------------
Ran 15 tests in 0.257s

OK
```

Happy pinballing and happy Python learning! 🚀
