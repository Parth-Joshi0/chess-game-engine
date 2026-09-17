"""Perft: count leaf nodes of the move tree to a fixed depth.

Perft is the standard correctness test for move generation. The counts below are
well-known published values, so any mismatch is a real bug in movegen or in the FEN
loader. Run `python perft.py` for the default suite, `--depth N` to go deeper, or
`--divide FEN DEPTH` to find which move diverges.
"""

import argparse
import sys
import time

from board import Board, STARTING_FEN
from notation import move_to_uci

# (name, fen, [count at depth 1, 2, 3, ...])
SUITE = [
    ("startpos", STARTING_FEN,
     [20, 400, 8902, 197281]),
    ("kiwipete", "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
     [48, 2039, 97862, 4085603]),
    ("position 3", "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
     [14, 191, 2812, 43238]),
    ("position 4", "r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1",
     [6, 264, 9467, 422333]),
    ("position 5", "rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8",
     [44, 1486, 62379, 2103487]),
]


def perft(board: Board, depth: int) -> int:
    if depth == 0:
        return 1

    stm = board.turn % 2 == 0
    total = 0

    for move in board.get_pseudo_legal_moves(stm):
        board._apply_temp_move(move)
        if board.in_check(stm):
            board._undo_temp_move(move)
            continue
        # At depth 1 the legality filter above is the whole count, so skip the recursion.
        total += 1 if depth == 1 else perft(board, depth - 1)
        board._undo_temp_move(move)

    return total


def perft_divide(board: Board, depth: int) -> dict[str, int]:
    # Per-root-move counts. Comparing these against a reference engine pinpoints the
    # single move whose subtree is wrong, then you recurse into it.
    stm = board.turn % 2 == 0
    out = {}

    for move in board.get_pseudo_legal_moves(stm):
        board._apply_temp_move(move)
        if board.in_check(stm):
            board._undo_temp_move(move)
            continue
        out[move_to_uci(move)] = 1 if depth == 1 else perft(board, depth - 1)
        board._undo_temp_move(move)

    return out


def run_suite(max_depth: int) -> bool:
    ok = True

    for name, fen, expected in SUITE:
        board = Board.from_fen(fen)
        print(f"\n{name}\n  {fen}")

        for depth in range(1, min(max_depth, len(expected)) + 1):
            want = expected[depth - 1]
            start = time.perf_counter()
            got = perft(board, depth)
            elapsed = time.perf_counter() - start
            nps = int(got / elapsed) if elapsed > 0 else 0

            if got == want:
                print(f"  depth {depth}: {got:>9}  OK    ({elapsed:6.2f}s, {nps:>7} nps)")
            else:
                ok = False
                print(f"  depth {depth}: {got:>9}  FAIL  (expected {want}, diff {got - want:+d})")

            # The board must come back exactly as it started, or undo is broken.
            if board.to_fen() != fen:
                ok = False
                print(f"  !! board not restored after depth {depth}: {board.to_fen()}")

    return ok


def main() -> int:
    ap = argparse.ArgumentParser(description="Perft move generation tests")
    ap.add_argument("--depth", type=int, default=3,
                    help="max depth for the suite (default 3; 4 takes a few minutes)")
    ap.add_argument("--divide", nargs=2, metavar=("FEN", "DEPTH"),
                    help="print per-root-move counts for a position")
    args = ap.parse_args()

    if args.divide:
        fen, depth = args.divide[0], int(args.divide[1])
        board = Board.from_fen(fen)
        counts = perft_divide(board, depth)
        for mv in sorted(counts):
            print(f"{mv}: {counts[mv]}")
        print(f"\nNodes searched: {sum(counts.values())}")
        return 0

    ok = run_suite(args.depth)
    print("\nAll perft counts match." if ok else "\nPERFT FAILURES -- see above.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
