"""Self-play harness: what cutechess-cli would do, without the dependency.

Runs two independent uci.py subprocesses against each other under a real clock and
independently validates every bestmove for legality, flags clock overruns, and detects
crashes or hangs. This is the strongest end-to-end test of the UCI layer, because it
exercises position replay, time management and stop handling over hundreds of moves.

    python selfplay.py --games 4 --tc 5+0.05

If you do install cutechess-cli, the equivalent is:

    cutechess-cli -engine cmd=python3 arg=uci.py proto=uci \
                  -engine cmd=python3 arg=uci.py proto=uci \
                  -each tc=5+0.05 -games 20 -repeat
"""

import argparse
import subprocess
import sys
import threading
import time
from pathlib import Path

from board import Board
from notation import move_to_uci, uci_to_move, legal_moves

UCI_PY = str(Path(__file__).parent / "uci.py")

RESULT_NAMES = {1: "checkmate", 2: "stalemate", 3: "50-move rule", 4: "threefold"}


class UciEngine:
    def __init__(self, name):
        self.name = name
        self.proc = subprocess.Popen(
            [sys.executable, "-u", UCI_PY],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1)
        self.lines = []
        self._lock = threading.Lock()
        threading.Thread(target=self._read, daemon=True).start()

        self._send("uci")
        if not self._wait("uciok", 20):
            raise RuntimeError(f"{name}: no uciok")

    def _read(self):
        for line in self.proc.stdout:
            with self._lock:
                self.lines.append(line.rstrip("\n"))

    def _send(self, cmd):
        if self.proc.poll() is not None:
            raise RuntimeError(f"{self.name} died")
        self.proc.stdin.write(cmd + "\n")
        self.proc.stdin.flush()

    def _wait(self, prefix, timeout):
        deadline = time.time() + timeout
        while time.time() < deadline:
            with self._lock:
                for line in self.lines:
                    if line.startswith(prefix):
                        return line
            if self.proc.poll() is not None:
                raise RuntimeError(f"{self.name} exited during search")
            time.sleep(0.002)
        return None

    def new_game(self):
        with self._lock:
            self.lines.clear()
        self._send("ucinewgame")
        self._send("isready")
        if not self._wait("readyok", 20):
            raise RuntimeError(f"{self.name}: no readyok")

    def bestmove(self, moves, wtime_ms, btime_ms, winc_ms, binc_ms, timeout):
        with self._lock:
            self.lines.clear()
        pos = "position startpos"
        if moves:
            pos += " moves " + " ".join(moves)
        self._send(pos)
        self._send(f"go wtime {int(wtime_ms)} btime {int(btime_ms)} "
                   f"winc {int(winc_ms)} binc {int(binc_ms)}")
        line = self._wait("bestmove", timeout)
        if line is None:
            raise RuntimeError(f"{self.name}: no bestmove within {timeout}s")
        return line.split()[1]

    def close(self):
        try:
            self._send("quit")
            self.proc.wait(timeout=10)
        except Exception:
            self.proc.kill()


def play_game(white, black, base_s, inc_s, max_plies, verbose):
    board = Board()
    moves = []
    clock = {True: base_s * 1000.0, False: base_s * 1000.0}
    inc_ms = inc_s * 1000.0

    for engine in (white, black):
        engine.new_game()

    while len(moves) < max_plies:
        stm = board.turn % 2 == 0
        engine = white if stm else black

        if not legal_moves(board):
            end = board.game_end()
            return RESULT_NAMES.get(end, "no legal moves"), moves, None

        end = board.game_end()
        if end in (3, 4):
            return RESULT_NAMES[end], moves, None

        start = time.perf_counter()
        # Allow generous slack over the engine's own budget before calling it a hang.
        token = engine.bestmove(moves, clock[True], clock[False], inc_ms, inc_ms,
                                timeout=max(20.0, base_s))
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        clock[stm] -= elapsed_ms
        if clock[stm] < 0:
            return "time forfeit", moves, f"{engine.name} flagged ({-clock[stm]:.0f}ms over)"
        clock[stm] += inc_ms

        if token == "0000":
            return "null move returned with legal moves available", moves, engine.name

        mv = uci_to_move(board, token)
        if mv is None:
            return "ILLEGAL MOVE", moves, f"{engine.name} played {token} in {board.to_fen()}"

        board._apply_temp_move(mv)
        moves.append(token)

        if verbose and len(moves) % 20 == 0:
            print(f"    ply {len(moves)}  w={clock[True]/1000:5.1f}s b={clock[False]/1000:5.1f}s")

    return "adjudicated (ply limit)", moves, None


def main():
    ap = argparse.ArgumentParser(description="UCI self-play validation")
    ap.add_argument("--games", type=int, default=2)
    ap.add_argument("--tc", default="5+0.05", help="base+increment in seconds")
    ap.add_argument("--max-plies", type=int, default=200)
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    base_s, _, inc_str = args.tc.partition("+")
    base_s, inc_s = float(base_s), float(inc_str or 0)

    print(f"Self-play: {args.games} game(s) at {base_s}+{inc_s}s\n")

    white = UciEngine("engine1")
    black = UciEngine("engine2")
    problems = []

    try:
        for g in range(1, args.games + 1):
            # Alternate colours so both engines play each side.
            w, b = (white, black) if g % 2 else (black, white)
            print(f"  game {g}: {w.name} vs {b.name}")

            t = time.perf_counter()
            result, moves, detail = play_game(w, b, base_s, inc_s, args.max_plies, args.verbose)
            dur = time.perf_counter() - t

            bad = result in ("ILLEGAL MOVE", "time forfeit") or "null move" in result
            status = "PROBLEM" if bad else "ok"
            print(f"    {status}: {result} after {len(moves)} plies ({dur:.1f}s)")
            if detail:
                print(f"    {detail}")
            if bad:
                problems.append(f"game {g}: {result} -- {detail}")
    finally:
        white.close()
        black.close()

    print()
    if problems:
        print(f"{len(problems)} PROBLEM(S):")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("Self-play clean: no illegal moves, no forfeits, no crashes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
