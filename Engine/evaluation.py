from dataclasses import dataclass
from board import Board, Move

WHITE = True
BLACK = False

KING_PAWN_SHIELD_BONUS = 15
DOUBLED_PAWN_PENALTY = -20
ROOK_OPEN_FILE_BONUS = 25
ROOK_SEMI_OPEN_FILE_BONUS = 15

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

    score += 2*(len(white_moves) - len(black_moves))

    score += board.mg * king_safety(board)
    score += file_bonuses(board)

    if board.turn % 2 != 0:  # Black to move
        score = -score

    if debug:
        return score
    return score

def terminal_eval(state, ply):
    if state != 1:
        return 0
    else:
        return -1000000000 + ply

def king_safety(board):
    score = 0

    kx, ky = board.whiteKing.pos

    y = ky - 1
    if y >= 0:
        for dx in (-1, 0, 1):
            x = kx + dx
            if 0 <= x < 8:
                p = board.boardList[y][x]
                if p and p.name == "pawn" and p.colour == WHITE:
                    score += KING_PAWN_SHIELD_BONUS
                    if dx == 0:
                        score += 3

    kx, ky = board.blackKing.pos

    y = ky + 1
    if y < 8:
        for dx in (-1, 0, 1):
            x = kx + dx
            if 0 <= x < 8:
                p = board.boardList[y][x]
                if p and p.name == "pawn" and p.colour == BLACK:
                    score -= KING_PAWN_SHIELD_BONUS
                    if dx == 0:
                        score -= 3

    return score

def file_bonuses(board):
    #Caluclates Double Pawn Penalty, Bishop Pair Bonus and Open File for rooks bonuses
    white_pawns_per_file = [0] * 8
    black_pawns_per_file = [0] * 8

    white_rooks_per_file = [0] * 8
    black_rooks_per_file = [0] * 8

    white_bishops = 0
    black_bishops = 0

    score = 0

    for p in board.whitePieces:
        if p.name == "pawn":
            white_pawns_per_file[p.pos[0]] += 1
        elif p.name == "rook":
            white_rooks_per_file[p.pos[0]] += 1
        elif p.name == "bishop":
            white_bishops += 1

    for p in board.blackPieces:
        if p.name == "pawn":
            black_pawns_per_file[p.pos[0]] += 1
        elif p.name == "rook":
            black_rooks_per_file[p.pos[0]] += 1
        elif p.name == "bishop":
            black_bishops += 1

    for i in range(8):
        wp = white_pawns_per_file[i]
        bp = black_pawns_per_file[i]

        if wp > 1:
            score += (wp - 1) * DOUBLED_PAWN_PENALTY
        if bp > 1:
            score -= (bp - 1) * DOUBLED_PAWN_PENALTY
        if wp == 0 and bp == 0:
            score += white_rooks_per_file[i] * ROOK_OPEN_FILE_BONUS
            score -= black_rooks_per_file[i] * ROOK_OPEN_FILE_BONUS
        elif wp == 0:
            score += white_rooks_per_file[i] * ROOK_SEMI_OPEN_FILE_BONUS
        elif bp == 0:
            score -= black_rooks_per_file[i] * ROOK_SEMI_OPEN_FILE_BONUS

    return score