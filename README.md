# Python Chess Engine
A fully playable chess game and engine written in Python, featuring complete chess rules, alpha-beta negamax search with quiescence, iterative deepening, transposition tables, and phase-aware piece-square evaluation.

Built from scratch to understand chess engine fundamentals—from move generation to search algorithms to positional evaluation.

<img width="643" height="668" alt="image" src="https://github.com/user-attachments/assets/5ccb1fef-2251-46d3-969f-68d99fcfe73f" />

## Features

### Complete Chess Implementation
- **Full ruleset**: All standard chess rules including castling, en passant, and pawn promotion
- **Legal move generation**: Pseudo-legal generation with check validation
- **Draw detection**: 50-move rule and threefold repetition
- **Game end conditions**: Checkmate and stalemate detection

### Search Engine
- **Negamax with alpha-beta pruning**: Efficient game tree search
- **Quiescence search**: Tactical move extension to avoid horizon effects
- **Iterative deepening**: Progressive depth search with time control support
- **Transposition table**: Position caching to avoid redundant search
- **Move ordering**: MVV-LVA (Most Valuable Victim - Least Valuable Attacker) heuristic
- **Ply-aware mate scoring**: Prefers faster checkmates, delays losses

### Evaluation Function
- **Material evaluation**: Signed piece values (White positive, Black negative)
- **Piece-square tables**: Phase-aware positional bonuses (middlegame/endgame)
- **King safety**: Pawn shield evaluation weighted by game phase
- **Pawn structure**: Doubled pawn penalties
- **Rook placement**: Open and semi-open file bonuses
- **Mobility**: Pseudo-legal move count bonus

### UCI Protocol
- **Standard UCI interface**: Plays in any UCI GUI (Arena, Banksia, cutechess-cli, En Croissant)
- **FEN support**: Load and serialise arbitrary positions
- **Real time management**: `wtime`/`btime`/`winc`/`binc`/`movestogo`, plus `movetime`, `depth`, `nodes` and `infinite`
- **Interruptible search**: `stop` aborts within milliseconds, in both timed and fixed-depth modes
- **Live analysis output**: `info` lines with depth, seldepth, score (cp or mate), nodes, nps and the principal variation
- **Embeddable core**: `EngineSession` exposes the engine through typed callbacks, so a web backend can drive it directly instead of parsing stdout

### User Interface
- **Interactive home screen**: Configure Human vs Human, Human vs Engine, or Engine vs Engine
- **Flexible engine settings**: Choose between fixed-depth or time-limited search
- **Visual feedback**: Move highlighting, capture indicators, legal move display
- **Promotion UI**: Interactive piece selection for pawn promotions

<img width="639" height="665" alt="image" src="https://github.com/user-attachments/assets/60ff0ff1-d24b-4365-9007-fc86308ff9f6" />


## Engine Strength

The engine plays at an estimated **~1800-2000 Elo** level:
- Defeats Chess.com 2000-rated bots
- Understands tactical patterns (pins, forks, skewers)
- Avoids horizon-effect blunders via quiescence search
- Makes positionally sound moves using piece-square tables

At 4-6 ply search depth with ~10-25 kN/s throughput, the engine achieves this strength through:
- Strong evaluation function (material + PST + king safety + pawn structure)
- Effective move ordering (MVV-LVA) for better alpha-beta cutoffs
- Quiescence search extending tactical lines to quiet positions

**Note**: Performance measured against Chess.com bots in standard time controls. Actual playing strength varies by position type and time settings.

## Technical Implementation

### Architecture
- **Incremental updates**: Board evaluation updated during make/unmake for efficiency
- **Reversible moves**: Complete state preservation for exact position restoration
- **Position hashing**: Binary position keys for repetition detection
- **Game phase calculation**: Dynamic middlegame/endgame weights based on material

### Performance
- **Typical search depth**: 4-6 ply in middlegame positions (depth-limited mode)
- **Node throughput**: ~9-25 kN/s depending on position complexity
- **Optimization techniques**: 
  - Pseudo-legal generation with late check validation
  - Move ordering for better alpha-beta cutoffs
  - Transposition table to avoid redundant computation

## Tech Stack
- **Language**: Python 3.10+
- **GUI**: Pygame
- **Paradigms**: Object-oriented design, negamax recursion, state restoration patterns
- **Data structures**: 2D list board representation, position hash tables, move stacks

## Installation & Usage
```bash
# Clone the repository
git clone <your-repo-url>
cd python-chess-engine

# Install dependencies
pip install pygame

# Run the game
python main.py
```

### Playing the Game
1. Configure players (Human/Engine) and search settings on the home screen
2. Click pieces to select, click destination to move
3. Game enforces all legal moves automatically
4. Press **R** to restart, **ESC** to quit

## UCI Mode

The engine speaks the Universal Chess Interface, so it can be used by any standard chess
GUI. UCI mode does not import pygame and needs no dependencies at all.

```bash
python uci.py
```

A minimal session:

```
uci
id name Chessathon Py 1.0
id author Parth Joshi
option name Hash type spin default 64 min 1 max 1024
option name Move Overhead type spin default 50 min 0 max 5000
option name Threads type spin default 1 min 1 max 1
option name Clear Hash type button
uciok
position startpos moves e2e4 e7e5
go movetime 1000
info depth 4 seldepth 8 score cp 31 nodes 9214 nps 5602 time 1644 hashfull 1 pv g1f3 b8c6
bestmove g1f3
```

**Supported commands**: `uci`, `isready`, `ucinewgame`, `setoption`, `position`
(`startpos` or `fen`, with an optional `moves` list), `go` (`depth`, `movetime`, `nodes`,
`wtime`/`btime`/`winc`/`binc`/`movestogo`, `infinite`, `searchmoves`), `stop`, `quit`.

**Options**: `Hash` (MB, bounds the transposition table), `Move Overhead` (ms subtracted
from the clock to cover GUI/network latency — raise it for a networked front end), and
`Clear Hash`.

Pondering is deliberately not advertised, so GUIs will not send `go ponder`. Chess960 is
not supported.

To register it in a GUI, point the engine path at your Python interpreter with `uci.py`
as the argument. For cutechess-cli:

```bash
cutechess-cli -engine cmd=python3 arg=/path/to/uci.py proto=uci \
              -engine cmd=python3 arg=/path/to/uci.py proto=uci \
              -each tc=10+0.1 -games 20 -repeat
```

### Embedding the engine

`uci.py` is a thin shell over two reusable layers, so a web backend does not need to
spawn a subprocess and parse text:

```python
from engine_session import EngineSession, GoParams

session = EngineSession(
    on_info=lambda info: print(info.depth, info.score_cp, info.pv),
    on_bestmove=lambda move: print("best:", move),
)
session.set_position(fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
session.go(GoParams(movetime=1000))
```

`EngineSession` speaks dataclasses and callbacks rather than protocol text; `UciProtocol`
is one adapter over it, and an HTTP or WebSocket handler would be another. Note that one
session represents one game — the `Board` is mutated in place, so concurrent users need
one session each.

## Testing

```bash
python perft.py                 # move generation correctness (depth 3; --depth 4 is slower)
python perft.py --divide <FEN> 3  # per-move breakdown, for locating a discrepancy
python test_uci.py              # protocol, FEN and notation round-trips
python selfplay.py --games 4    # full games under a clock, validating every move
```

`perft.py` checks node counts against published values for five standard positions
(including Kiwipete) chosen to exercise castling rights, en passant, pins and promotions.

## Project Structure
```
├── main.py              # Game loop and UI rendering
├── homeScreen.py        # Configuration menu
├── board.py             # Board representation, move logic, FEN
├── piece.py             # Piece classes
├── notation.py          # UCI move notation <-> Move objects
├── engine_session.py    # Engine orchestration, threading, time management (no protocol text)
├── uci_protocol.py      # UCI command parsing and response formatting
├── uci.py               # UCI entry point (stdin/stdout)
├── perft.py             # Move generation tests
├── test_uci.py          # Protocol and round-trip tests
├── selfplay.py          # Self-play validation harness
├── Engine/
│   ├── search.py        # Search algorithms
│   ├── evaluation.py    # Position evaluation
│   └── pst.py          # Piece-square tables
```

## Known Limitations

- **Evaluation is path-dependent.** `board.eval` is maintained incrementally, but the
  middlegame/endgame phase weights shift as material comes off, so an already-accumulated
  evaluation was computed partly at older weights. A position loaded from FEN is scored
  fresh and can therefore differ slightly (measured worst case ~42 cp) from the same
  position reached by playing moves. The fresh value is the more correct of the two.
- **Position keys are not Zobrist hashes.** `position_key()` builds a bitstring, which is
  correct but slow — it is called several times per node and is the single largest
  contributor to the engine's ~6 kN/s throughput in UCI mode.
- **No opening book or tablebases**, so early moves are searched from scratch.

## What I Learned
This project provided deep insights into:
- **Chess engine architecture**: How search, evaluation, and move generation interact
- **Alpha-beta pruning**: Why move ordering and quiescence search matter
- **State management**: The critical importance of exact make/unmake symmetry
- **Performance tradeoffs**: Where optimization matters (data structures, move ordering) vs. where it doesn't (micro-optimizations)
- **Debugging complexity**: How subtle bugs in special moves (castling, en passant, promotion) cascade through search

## Potential Future Enhancements
While this project is feature-complete for my learning goals, possible extensions include:
- Opening book integration
- Endgame tablebase support
- Bitboard representation for performance
- Advanced evaluation (passed pawns, king tropism, mobility improvements)
- Zobrist hashing to replace the bitstring position key (the biggest available speedup)
- Transposition-table move ordering (the stored best move is already being recorded)
- Parallel search (lazy SMP)

## Acknowledgments
Built as a learning project to understand chess engine fundamentals. Inspired by classical engines like Stockfish and modern educational resources on game tree search.

## License
MIT License - Free for educational and personal use.
