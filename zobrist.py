"""Zobrist random tables for position hashing.

Each table entry is an independent random 64-bit int. XORing in the entries for
whatever is actually on the board (pieces, castling rights, en-passant file, side
to move) gives a well-distributed hash, and XORing the same entry in twice cancels
out -- which is what lets Board maintain its piece hash incrementally across
move/unmove instead of rebuilding it from scratch every call.

The seed is fixed so hashes are reproducible run to run (useful for tests/debugging);
it has no effect on hash quality.
"""

import random

_rng = random.Random(0xC0FFEE)

PIECE_INDEX = {"king": 0, "queen": 1, "rook": 2, "bishop": 3, "knight": 4, "pawn": 5}

# [colour][piece_index][y][x] -> random 64-bit key
PIECE_KEYS = [
    [[[_rng.getrandbits(64) for _ in range(8)] for _ in range(8)] for _ in range(6)]
    for _ in range(2)
]

# Castling rights order matches Board._castling_rights(): (K, Q, k, q)
CASTLING_KEYS = [_rng.getrandbits(64) for _ in range(4)]

# One key per file, used when an en-passant target exists on that file
EN_PASSANT_KEYS = [_rng.getrandbits(64) for _ in range(8)]

# XORed in whenever it's Black to move
SIDE_KEY = _rng.getrandbits(64)


def piece_key(piece, x: int, y: int) -> int:
    colour = 1 if piece.colour else 0
    return PIECE_KEYS[colour][PIECE_INDEX[piece.name]][y][x]


def castling_component(rights) -> int:
    key = 0
    for i, ok in enumerate(rights):
        if ok:
            key ^= CASTLING_KEYS[i]
    return key


def en_passant_component(en_passant_target) -> int:
    if en_passant_target is None:
        return 0
    x, _y = en_passant_target
    return EN_PASSANT_KEYS[x]
