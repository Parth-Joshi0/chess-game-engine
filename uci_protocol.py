"""UCI text adapter over EngineSession.

This module only parses command lines and formats response lines; all state and
threading live in EngineSession. It never reads stdin or writes stdout itself --
uci.py supplies the output callback -- so it is testable without a subprocess.

Protocol reference: http://wbec-ridderkerk.nl/html/UCIProtocol.html
"""

import threading

from board import STARTING_FEN
from engine_session import EngineSession, GoParams, SearchInfo

ENGINE_NAME = "Chessathon Py 1.0"
ENGINE_AUTHOR = "Parth Joshi"

# `go` arguments that take an integer value
GO_INT_FIELDS = {
    "depth", "movetime", "wtime", "btime", "winc", "binc",
    "movestogo", "nodes", "mate",
}


class UciProtocol:
    def __init__(self, out):
        # out(line: str) is called for every protocol line. It must be safe to call from
        # the search thread as well as the command thread.
        self._out = out
        self._out_lock = threading.Lock()
        self.quitting = False

        self.session = EngineSession(on_info=self._send_info, on_bestmove=self._send_bestmove)

    def _send(self, line: str) -> None:
        with self._out_lock:
            self._out(line)

    # ---------- dispatch ----------
    def handle_line(self, line: str) -> None:
        tokens = line.split()
        if not tokens:
            return

        # Unknown leading tokens are skipped rather than failing the line, as the spec
        # requires ("if the engine doesn't understand a token, it should ignore it").
        while tokens and tokens[0] not in COMMANDS:
            tokens.pop(0)
        if not tokens:
            return

        COMMANDS[tokens[0]](self, tokens[1:])

    # ---------- commands ----------
    def cmd_uci(self, args):
        self._send(f"id name {ENGINE_NAME}")
        self._send(f"id author {ENGINE_AUTHOR}")
        self._send("option name Hash type spin default 64 min 1 max 1024")
        self._send("option name Move Overhead type spin default 50 min 0 max 5000")
        self._send("option name Threads type spin default 1 min 1 max 1")
        self._send("option name Clear Hash type button")
        self._send("uciok")

    def cmd_isready(self, args):
        # Must answer even mid-search, which is why this never touches the board.
        self._send("readyok")

    def cmd_ucinewgame(self, args):
        self.session.new_game()

    def cmd_setoption(self, args):
        # setoption name <name with spaces> [value <value with spaces>]
        if not args or args[0] != "name":
            return
        try:
            split = args.index("value")
            name = " ".join(args[1:split])
            value = " ".join(args[split + 1:])
        except ValueError:
            name = " ".join(args[1:])
            value = ""
        self.session.set_option(name, value)

    def cmd_position(self, args):
        if not args:
            return

        if args[0] == "startpos":
            fen, rest = STARTING_FEN, args[1:]
        elif args[0] == "fen":
            # Scan to the `moves` keyword instead of assuming six FEN fields; GUIs do
            # send truncated FENs.
            i = 1
            while i < len(args) and args[i] != "moves":
                i += 1
            fen, rest = " ".join(args[1:i]), args[i:]
        else:
            return

        moves = rest[1:] if rest and rest[0] == "moves" else []

        try:
            rejected = self.session.set_position(fen, moves)
        except ValueError as exc:
            self._send(f"info string bad position: {exc}")
            return

        for token in rejected:
            self._send(f"info string ignoring unplayable move: {token}")

    def cmd_go(self, args):
        params = GoParams()
        i = 0
        while i < len(args):
            tok = args[i]
            if tok in GO_INT_FIELDS and i + 1 < len(args):
                try:
                    setattr(params, tok, int(args[i + 1]))
                except ValueError:
                    pass
                i += 2
            elif tok == "infinite":
                params.infinite = True
                i += 1
            elif tok == "ponder":
                params.ponder = True
                i += 1
            elif tok == "searchmoves":
                # Consumes the rest of the line, per the spec.
                params.searchmoves = args[i + 1:]
                i = len(args)
            else:
                i += 1

        self.session.go(params)

    def cmd_stop(self, args):
        self.session.stop()

    def cmd_ponderhit(self, args):
        # Ponder is not advertised, so this should never arrive; treat it as "the guess
        # was right, keep searching" -- which for us means simply not stopping.
        pass

    def cmd_quit(self, args):
        self.quitting = True
        self.session.shutdown()

    # ---------- output from the search thread ----------
    def _send_info(self, info: SearchInfo) -> None:
        parts = [f"info depth {info.depth}", f"seldepth {info.seldepth}"]

        if info.score_mate is not None:
            parts.append(f"score mate {info.score_mate}")
        else:
            parts.append(f"score cp {info.score_cp}")

        parts.append(f"nodes {info.nodes}")
        parts.append(f"nps {info.nps}")
        parts.append(f"time {info.time_ms}")
        parts.append(f"hashfull {info.hashfull}")

        # `pv` must come last: GUIs treat every token after it as part of the line.
        if info.pv:
            parts.append("pv " + " ".join(info.pv))

        self._send(" ".join(parts))

    def _send_bestmove(self, move: str) -> None:
        self._send(f"bestmove {move}")


COMMANDS = {
    "uci": UciProtocol.cmd_uci,
    "isready": UciProtocol.cmd_isready,
    "ucinewgame": UciProtocol.cmd_ucinewgame,
    "setoption": UciProtocol.cmd_setoption,
    "position": UciProtocol.cmd_position,
    "go": UciProtocol.cmd_go,
    "stop": UciProtocol.cmd_stop,
    "ponderhit": UciProtocol.cmd_ponderhit,
    "quit": UciProtocol.cmd_quit,
}
