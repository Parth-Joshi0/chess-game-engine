"""End-to-end checks for the UCI layer.

Drives `uci.py` as a real subprocess, the same way a GUI does, plus in-process
round-trip tests for FEN and move notation. Run with `python test_uci.py`.
"""

import random
import subprocess
import sys
import threading
import time
from pathlib import Path

from board import Board, STARTING_FEN
from notation import move_to_uci, uci_to_move, legal_moves, move_signature

UCI_PY = str(Path(__file__).parent / "uci.py")

# Every line an engine may legally send on stdout.
VALID_PREFIXES = ("id", "option", "uciok", "readyok", "info", "bestmove",
                  "copyprotection", "registration")

failures = []


def check(cond, label, detail=""):
    if cond:
        print(f"  PASS  {label}")
    else:
        failures.append(label)
        print(f"  FAIL  {label}{(': ' + detail) if detail else ''}")


class Engine:
    """A live uci.py subprocess with a background stdout reader."""

    def __init__(self):
        self.proc = subprocess.Popen(
            [sys.executable, "-u", UCI_PY],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1)
        self.lines = []
        self._lock = threading.Lock()
        self._reader = threading.Thread(target=self._read, daemon=True)
        self._reader.start()

    def _read(self):
        for line in self.proc.stdout:
            with self._lock:
                self.lines.append(line.rstrip("\n"))

    def send(self, cmd):
        self.proc.stdin.write(cmd + "\n")
        self.proc.stdin.flush()

    def wait_for(self, prefix, timeout=30.0):
        """Wait for a line starting with prefix; return it, or None on timeout."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            with self._lock:
                for line in self.lines:
                    if line.startswith(prefix):
                        return line
            time.sleep(0.005)
        return None

    def all_lines(self):
        with self._lock:
            return list(self.lines)

    def close(self):
        try:
            self.send("quit")
            self.proc.wait(timeout=10)
        except Exception:
            self.proc.kill()


def test_handshake():
    print("\nhandshake")
    e = Engine()
    try:
        e.send("uci")
        check(e.wait_for("uciok", 15) is not None, "uci -> uciok")

        lines = e.all_lines()
        check(any(l == "id name Chessathon Py 1.0" for l in lines), "id name")
        check(any(l == "id author Parth Joshi" for l in lines), "id author")
        check(any(l.startswith("option name Hash") for l in lines), "advertises Hash")
        # Ponder must NOT be advertised, or GUIs will send `go ponder`.
        check(not any("name Ponder" in l for l in lines), "does not advertise Ponder")

        e.send("isready")
        check(e.wait_for("readyok", 15) is not None, "isready -> readyok")
    finally:
        e.close()


def test_search_and_bestmove():
    print("\nsearch")
    e = Engine()
    try:
        e.send("uci"); e.wait_for("uciok", 15)
        e.send("ucinewgame")
        e.send("position startpos")
        e.send("go depth 3")

        bm = e.wait_for("bestmove", 60)
        check(bm is not None, "go depth 3 -> bestmove")

        if bm:
            mv = bm.split()[1]
            board = Board()
            check(uci_to_move(board, mv) is not None, "bestmove is legal", mv)

        infos = [l for l in e.all_lines() if l.startswith("info depth")]
        check(len(infos) >= 3, "emits an info line per depth", f"got {len(infos)}")
        check(all(" pv " in l or l.rstrip().endswith("pv") or "pv" not in l for l in infos),
              "pv is well formed")
        check(any("score cp" in l for l in infos), "reports a cp score")

        # The single most valuable assertion: nothing but protocol on stdout.
        bad = [l for l in e.all_lines() if l and not l.startswith(VALID_PREFIXES)]
        check(not bad, "no non-protocol output on stdout", str(bad[:3]))
    finally:
        e.close()


def test_position_with_moves():
    print("\nposition")
    e = Engine()
    try:
        e.send("uci"); e.wait_for("uciok", 15)
        e.send("position startpos moves e2e4 e7e5 g1f3")
        e.send("go depth 2")
        bm = e.wait_for("bestmove", 60)
        check(bm is not None, "position startpos moves ... -> bestmove")

        if bm:
            b = Board()
            for m in ["e2e4", "e7e5", "g1f3"]:
                b._apply_temp_move(uci_to_move(b, m))
            check(uci_to_move(b, bm.split()[1]) is not None,
                  "bestmove legal after replayed moves", bm)
    finally:
        e.close()

    # A FEN position, and a mate the engine should actually find.
    e = Engine()
    try:
        e.send("uci"); e.wait_for("uciok", 15)
        # Back-rank mate in one: Ra8#
        e.send("position fen 6k1/5ppp/8/8/8/8/8/R3K3 w - - 0 1")
        e.send("go depth 4")
        bm = e.wait_for("bestmove", 120)
        check(bm is not None and bm.split()[1] == "a1a8", "finds mate in one", str(bm))
        mates = [l for l in e.all_lines() if "score mate" in l]
        check(any("score mate 1" in l for l in mates), "reports score mate 1",
              str(mates[-1:]))
    finally:
        e.close()


def test_stalemate_and_no_moves():
    print("\nterminal positions")
    e = Engine()
    try:
        e.send("uci"); e.wait_for("uciok", 15)
        # Black to move, stalemated.
        e.send("position fen 7k/5Q2/6K1/8/8/8/8/8 b - - 0 1")
        e.send("go depth 3")
        bm = e.wait_for("bestmove", 60)
        check(bm is not None and bm.split()[1] == "0000",
              "stalemate -> bestmove 0000", str(bm))
    finally:
        e.close()


def test_stop():
    print("\nstop")
    e = Engine()
    try:
        e.send("uci"); e.wait_for("uciok", 15)
        e.send("position startpos")
        e.send("go infinite")
        time.sleep(1.5)

        check(e.wait_for("bestmove", 0.1) is None, "go infinite does not answer early")

        t = time.time()
        e.send("stop")
        bm = e.wait_for("bestmove", 10)
        elapsed = time.time() - t
        check(bm is not None, "stop -> bestmove")
        check(elapsed < 2.0, "stop responds promptly", f"{elapsed:.2f}s")
    finally:
        e.close()

    # The case that hangs forever without the SearchTimeout catch in fixed-depth mode.
    e = Engine()
    try:
        e.send("uci"); e.wait_for("uciok", 15)
        e.send("position startpos")
        e.send("go depth 20")
        time.sleep(1.5)
        t = time.time()
        e.send("stop")
        bm = e.wait_for("bestmove", 15)
        elapsed = time.time() - t
        check(bm is not None, "stop during go depth 20 -> bestmove")
        check(elapsed < 3.0, "fixed-depth stop responds promptly", f"{elapsed:.2f}s")
    finally:
        e.close()


def test_time_control():
    print("\ntime control")
    e = Engine()
    try:
        e.send("uci"); e.wait_for("uciok", 15)
        e.send("position startpos")
        t = time.time()
        e.send("go wtime 10000 btime 10000 winc 100 binc 100")
        bm = e.wait_for("bestmove", 30)
        elapsed = time.time() - t
        # 10s / 30 + 75ms ~= 0.4s budget; allow generous slack for a slow iteration.
        check(bm is not None, "clock-based go -> bestmove")
        check(elapsed < 5.0, "respects the clock budget", f"{elapsed:.2f}s")
    finally:
        e.close()

    e = Engine()
    try:
        e.send("uci"); e.wait_for("uciok", 15)
        e.send("position startpos")
        t = time.time()
        e.send("go movetime 1000")
        bm = e.wait_for("bestmove", 30)
        elapsed = time.time() - t
        check(bm is not None and elapsed < 3.0, "go movetime 1000", f"{elapsed:.2f}s")
    finally:
        e.close()


def test_fen_roundtrip():
    print("\nFEN round-trip (random playout)")
    random.seed(7)
    bad_fen = bad_key = 0

    for _ in range(12):
        b = Board()
        for _ in range(60):
            moves = legal_moves(b)
            if not moves:
                break
            b._apply_temp_move(random.choice(moves))

            fen = b.to_fen()
            reloaded = Board.from_fen(fen)
            if reloaded.to_fen() != fen:
                bad_fen += 1
            # The key comparison is the one that catches hasMoved and en passant bugs.
            if reloaded.position_key() != b.position_key():
                bad_key += 1

    check(bad_fen == 0, "fen -> board -> fen is stable", f"{bad_fen} mismatches")
    check(bad_key == 0, "reloaded position_key matches", f"{bad_key} mismatches")


def test_move_roundtrip():
    print("\nmove notation round-trip")
    positions = [
        STARTING_FEN,
        "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
        "r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1",
        "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
        # Pawns on a7/b7/c7 with knights on a8/c8: pushes and capture-promotions both.
        "n1n5/PPPk4/8/8/8/8/4Kppp/5N1N w - - 0 1",
    ]
    mismatches = []
    promos_seen = 0

    for fen in positions:
        b = Board.from_fen(fen)
        for m in legal_moves(b):
            token = move_to_uci(m)
            back = uci_to_move(b, token)
            if back is None or move_signature(back) != move_signature(m):
                mismatches.append((fen, token))
            if m.typeOfMove == 3:
                promos_seen += 1

    check(not mismatches, "every legal move survives uci round-trip", str(mismatches[:3]))
    check(promos_seen >= 4, "exercised all promotion variants", f"{promos_seen} promotions")

    # The specific trap: Move.__eq__ ignores promo_piece, so these must not collapse.
    b = Board.from_fen("8/P6k/8/8/8/8/7K/8 w - - 0 1")
    got = set()
    for suffix in "qrbn":
        mv = uci_to_move(b, "a7a8" + suffix)
        got.add(mv.promo_piece.name if mv else None)
    check(got == {"queen", "rook", "bishop", "knight"},
          "a7a8q/r/b/n resolve to four distinct pieces", str(got))


def test_garbage_input():
    print("\nrobustness")
    e = Engine()
    try:
        e.send("uci"); e.wait_for("uciok", 15)
        for junk in ["", "   ", "nonsense", "position", "position fen garbage",
                     "go depth", "setoption", "position startpos moves e2e9",
                     "position startpos moves e2e4 zzzz"]:
            e.send(junk)
        e.send("isready")
        check(e.wait_for("readyok", 15) is not None, "survives malformed input")

        e.send("position startpos")
        e.send("go depth 2")
        check(e.wait_for("bestmove", 60) is not None, "still searches afterwards")

        bad = [l for l in e.all_lines() if l and not l.startswith(VALID_PREFIXES)]
        check(not bad, "no non-protocol output after garbage", str(bad[:3]))
    finally:
        e.close()


def main():
    test_fen_roundtrip()
    test_move_roundtrip()
    test_handshake()
    test_search_and_bestmove()
    test_position_with_moves()
    test_stalemate_and_no_moves()
    test_stop()
    test_time_control()
    test_garbage_input()

    print("\n" + "=" * 50)
    if failures:
        print(f"{len(failures)} FAILURE(S):")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("All UCI tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
