from dataclasses import dataclass
from board import Board
import math

WHITE = True
BLACK = False

KING_CASTLED_BONUS = 90
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
    from Engine.pst import PIECE_SQUARE_TABLE

    breakdown = EvalBreakdown()

    for piece in board.whitePieces + board.blackPieces:
        x, y = piece.pos
        name = piece.name
        value = piece.piece_worth()

        breakdown.material += value
        table = PIECE_SQUARE_TABLE.get(name)

        if name != "king":
            pct = table[mirrored_y(piece.colour, y)][x]
            pct = clamp(pct, -MAX_MULT_BONUS, MAX_MULT_BONUS)
            breakdown.pst += int(round(value * pct))
        else:
            king_pst = table[mirrored_y(piece.colour, y)][x]
            breakdown.king += int(round(100 * king_pst)) if piece.colour else -int(round(100 * king_pst))

            if is_castled_square(piece.colour, x, y):
                breakdown.king += KING_CASTLED_BONUS if piece.colour else -KING_CASTLED_BONUS
            else:
                breakdown.king += KING_NOT_CASTLED_PENALTY if piece.colour else -KING_NOT_CASTLED_PENALTY

    if debug:
        return breakdown.total, breakdown
    return breakdown.total

def terminal_eval(board, state):
    if state != 1:
        return 0
    else:
        return -math.inf if board.turn % 2 == 0 else math.inf