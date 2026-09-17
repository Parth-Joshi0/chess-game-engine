"""Conversion between UCI long algebraic notation and internal Move objects.

Internal coordinates are (x, y) = (file, row) with row 0 = rank 8, so a8 is (0, 0)
and e1 is (4, 7). Note that boardList is indexed [y][x] -- the opposite order.
"""

from board import Board, Move, num_to_chess_notation

# UCI promotion suffix <-> internal piece name
PROMO_NAME = {"q": "queen", "r": "rook", "b": "bishop", "n": "knight"}
PROMO_LETTER = {v: k for k, v in PROMO_NAME.items()}

NULL_MOVE = "0000"


def square_to_uci(pos: tuple[int, int]) -> str:
    # (4, 6) -> "e2"
    return num_to_chess_notation(pos)


def uci_to_square(s: str) -> tuple[int, int]:
    # "e2" -> (4, 6)
    if len(s) < 2:
        raise ValueError(f"Not a square: {s!r}")
    x = ord(s[0].lower()) - ord('a')
    y = 8 - int(s[1])
    if not (0 <= x <= 7 and 0 <= y <= 7):
        raise ValueError(f"Square out of range: {s!r}")
    return x, y


def move_to_uci(move: Move) -> str:
    # Castling is encoded as the king's two-square move (e1g1 / e1c1), which is already
    # how newPos is stored, so it needs no special case outside of Chess960.
    s = square_to_uci(move.oldPos) + square_to_uci(move.newPos)
    if move.typeOfMove == 3 and move.promo_piece is not None:
        s += PROMO_LETTER[move.promo_piece.name]
    return s


def move_signature(move: Move) -> tuple:
    # Identity of a move that survives regeneration, unlike the Move object itself.
    # Move defines __eq__ without __hash__, so Move is unhashable -- use this for sets.
    promo = move.promo_piece.name if (move.typeOfMove == 3 and move.promo_piece) else None
    return move.oldPos, move.newPos, promo


def uci_to_move(board: Board, token: str) -> Move | None:
    """Resolve a UCI move token against the position, or None if it isn't legal.

    The returned Move is freshly generated, so its promo_piece is a new Piece and its
    _temp_* undo slots are clean -- _apply_temp_move stashes state on the Move object,
    so handing back a reused one would corrupt the next make/unmake.
    """
    if len(token) < 4:
        return None

    try:
        frm = uci_to_square(token[0:2])
        to = uci_to_square(token[2:4])
    except (ValueError, IndexError):
        return None

    want = PROMO_NAME.get(token[4].lower()) if len(token) >= 5 else None
    if len(token) >= 5 and want is None:
        return None

    stm = board.turn % 2 == 0

    for m in board.get_pseudo_legal_moves(stm):
        if m.oldPos != frm or m.newPos != to:
            continue

        if m.typeOfMove == 3:
            # Move.__eq__ ignores promo_piece, so all four promotion variants compare
            # equal -- the piece name is the only thing that distinguishes them.
            # A bare "e7e8" from a lenient GUI is taken as a queen promotion.
            if m.promo_piece is None or m.promo_piece.name != (want or "queen"):
                continue
        elif want is not None:
            continue  # "e2e4q" is not a real move

        board._apply_temp_move(m)
        legal = not board.in_check(stm)
        board._undo_temp_move(m)

        if legal:
            return m

    return None


def legal_moves(board: Board) -> list[Move]:
    # Legal moves for the side to move, filtered from pseudo-legal ones.
    stm = board.turn % 2 == 0
    out = []
    for m in board.get_pseudo_legal_moves(stm):
        board._apply_temp_move(m)
        legal = not board.in_check(stm)
        board._undo_temp_move(m)
        if legal:
            out.append(m)
    return out
