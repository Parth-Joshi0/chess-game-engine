from dataclasses import dataclass
from board import Board, Move

WHITE = True
BLACK = False

KING_CASTLED_BONUS = 150
KING_NOT_CASTLED_PENALTY = -30

MAX_MULT_BONUS = 0.6

def clamp(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else hi if x > hi else x

def mirrored_y(colour: bool, y: int):
    return y if colour == WHITE else 7 - y

def is_castled_square(colour: bool, x: int, y: int) -> bool:
    return (
            (colour == WHITE and (x, y) in [(6, 0), (2, 0)]) or
            (colour == BLACK and (x, y) in [(6, 7), (2, 7)])
    )

@dataclass
class EvalBreakdown:
    material: int = 0
    pst: int = 0
    king: int = 0

    @property
    def total(self) -> int:
        return self.material + self.pst + self.king

def evaluate(board: Board, debug: bool) -> int | tuple[int, EvalBreakdown]:
    score = board.eval

    white_moves = board.get_pseudo_legal_moves(WHITE)
    black_moves = board.get_pseudo_legal_moves(BLACK)

    score += relative_mobility_bonus(white_moves)
    score += relative_mobility_bonus(black_moves)

    if board.turn % 2 != 0:  # Black to move
        score = -score

    if debug:
        return score
    return score

def terminal_eval(board, state, ply):
    if state != 1:
        return 0
    else:
        return -1000000000 + ply

def relative_mobility_bonus(moves : [Move]):
    MOBILITY_BONUS = {
        "king": 1,
        "pawn": 2,
        "queen": 3,
        "bishop": 5,
        "rook": 5,
        "knight": 3
    }

    score = 0
    for move in moves:
        if move.piece.colour == WHITE:
            score += MOBILITY_BONUS.get(move.piece.name)
        else:
            score -= MOBILITY_BONUS.get(move.piece.name)

    return score