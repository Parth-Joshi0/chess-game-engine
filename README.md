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

## Project Structure
```
├── main.py              # Game loop and UI rendering
├── homeScreen.py        # Configuration menu
├── board.py             # Board representation and move logic
├── piece.py             # Piece classes
├── Engine/
│   ├── search.py        # Search algorithms
│   ├── evaluation.py    # Position evaluation
│   └── pst.py          # Piece-square tables
```

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
- UCI protocol compatibility
- Parallel search (lazy SMP)

## Acknowledgments
Built as a learning project to understand chess engine fundamentals. Inspired by classical engines like Stockfish and modern educational resources on game tree search.

## License
MIT License - Free for educational and personal use.
