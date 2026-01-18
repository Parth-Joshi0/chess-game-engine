# Python Chess Engine
Simple Playable Chess Game and Engine written fully in Python, featuring a complete ruleset, alpha–beta negamax search, quiescence search, and a custom board representation optimized for engine performance.
This project focuses on **correctness, extensibility, and engine fundamentals**, with the goal of evolving into a stronger, optimized engine over time.

## Features
### Complete Chess Rules
- Legal move generation for all pieces
- Special moves:
  - Castling
  - En passant
  - Pawn promotion (including capture promotions)
- Check, checkmate, stalemate detection
- 50-move rule and threefold repetition detection

### Search Engine
- **Negamax with alpha–beta pruning**
- **Quiescence search** to prevent horizon-effect blunders
- Ply-aware mate scoring (prefers faster mates, delays losses)

### Evaluation Function
- Material evaluation using signed piece values
- Positional evaluation using piece–square tables
- King safety heuristics (castling bonuses, positional penalties)
  
## Tech Stack
- **Language:** Python
- **Paradigms:** Object-oriented design, recursion, immutable undo patterns
- **Core Concepts:** Game tree search, pruning, state hashing, rule enforcement
  
## Current Status
- Engine plays legal, tactically sound chess
- Avoids obvious blunders via quiescence search
- Correctly handles promotions, captures, and undo logic
- Transposition table integration
- Ongoing work:
  - Evaluation refinement
  - Performance optimizations

## Learning Goals & Motivation
This project was built to deeply understand:
- How real chess engines work internally
- The interaction between search and evaluation
- Why correctness in make/unmake logic is critical
- How performance optimizations emerge from architecture, not micro-tweaks

## License
This project is for educational and personal development purposes.
