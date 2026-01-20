from board import Board, Move

WHITE = True
BLACK = False

# Evaluation bonuses/penalties (in centipawns)
KING_PAWN_SHIELD_BONUS = 15
DOUBLED_PAWN_PENALTY = -20
ROOK_OPEN_FILE_BONUS = 25
ROOK_SEMI_OPEN_FILE_BONUS = 15

MAX_MULT_BONUS = 0.6

def evaluate(board: Board, debug: bool) -> int:
    score = board.eval

    white_moves = board.get_pseudo_legal_moves(WHITE)
    black_moves = board.get_pseudo_legal_moves(BLACK)

    # Relative Move Bonus
    score += 2*(len(white_moves) - len(black_moves))

    score += board.mg * king_safety(board)
    score += file_bonuses(board)

    if board.turn % 2 != 0:  # Black to move
        score = -score

    if debug:
        return score
    return score

def king_safety(board):
    # Calculates king safety based on amount of pawns in front of king
    score = 0

    kx, ky = board.whiteKing.pos

    # White king safety
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

    # Black King Safety
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
    # Calculates Double Pawn Penalty, Bishop Pair Bonus and Open File for rooks bonuses
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