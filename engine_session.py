"""Engine orchestration: board state, search configuration, and the search thread.

This layer is deliberately free of protocol text. It speaks in dataclasses and
callbacks so that both the UCI adapter (uci_protocol.py) and any other front end --
an HTTP or WebSocket server, for instance -- can sit on top of it as siblings, rather
than one having to parse the other's output.

Threading contract: only the search worker touches the Board. Commands that need to
read or replace the board must stop the search and join the worker first.
"""

import math
import threading
import time
from dataclasses import dataclass, field

from board import Board, STARTING_FEN
from Engine.search import SearchEngine, MATE_VALUE, MATE_THRESHOLD, MAX_PLY
from notation import move_to_uci, uci_to_move, legal_moves, NULL_MOVE

# Reported when the search never got a real evaluation; large but not mate-sized.
UNKNOWN_SCORE_CP = 30000


@dataclass
class GoParams:
    """Parsed UCI `go` arguments. Times are milliseconds, as the protocol sends them."""
    depth: int | None = None
    movetime: int | None = None
    wtime: int | None = None
    btime: int | None = None
    winc: int | None = None
    binc: int | None = None
    movestogo: int | None = None
    nodes: int | None = None
    mate: int | None = None
    infinite: bool = False
    ponder: bool = False
    searchmoves: list[str] = field(default_factory=list)


@dataclass
class SearchInfo:
    """One completed iteration. Exactly one of score_cp / score_mate is set."""
    depth: int
    seldepth: int
    nodes: int
    time_ms: int
    nps: int
    hashfull: int
    pv: list[str]
    score_cp: int | None = None
    score_mate: int | None = None


def classify_score(value) -> tuple[int | None, int | None]:
    """Split a raw negamax score into (centipawns, mate_in_moves).

    Scores are from the side to move's perspective, which is what UCI wants, so no
    negation happens here. Mates are stored as -MATE_VALUE + ply, so the distance in
    plies is MATE_VALUE - |score|; UCI reports moves, hence the halving.
    """
    if value == math.inf:
        return UNKNOWN_SCORE_CP, None
    if value == -math.inf:
        return -UNKNOWN_SCORE_CP, None

    # evaluate() returns a float (the mg/eg phase weights are floats), and mate scores
    # propagate back through quiescence search, so round before comparing.
    v = int(round(value))

    if v >= MATE_THRESHOLD:
        return None, (MATE_VALUE - v + 1) // 2
    if v <= -MATE_THRESHOLD:
        return None, -((MATE_VALUE + v + 1) // 2)
    return v, None


def allocate_time(white_to_move: bool, p: GoParams, overhead_ms: int = 50) -> float | None:
    """Per-move budget in seconds, or None when no clock was given (depth/infinite)."""
    if p.movetime is not None:
        return max(0.001, (p.movetime - overhead_ms) / 1000.0)

    my_time = p.wtime if white_to_move else p.btime
    if my_time is None:
        return None

    my_inc = (p.winc if white_to_move else p.binc) or 0
    my_time = max(0, my_time - overhead_ms)

    if p.movestogo:
        budget = my_time / max(1, p.movestogo) + my_inc * 0.75
    else:
        # Sudden death: assume roughly 30 moves still to play.
        budget = my_time / 30.0 + my_inc * 0.75

    # Never gamble more than 40% of the remaining clock on a single move.
    budget = min(budget, my_time * 0.4)
    return max(0.01, budget / 1000.0)


class EngineSession:
    def __init__(self, on_info=None, on_bestmove=None):
        self.board = Board()
        self.engine = SearchEngine(verbose=False, on_info=self._handle_info)

        self.on_info = on_info
        self.on_bestmove = on_bestmove

        self.move_overhead_ms = 50
        self.hash_mb = 64

        self._worker: threading.Thread | None = None
        self._search_start = 0.0
        self._infinite = False
        self._stop_requested = False

    # ---------- state ----------
    @property
    def is_searching(self) -> bool:
        return self._worker is not None and self._worker.is_alive()

    def new_game(self):
        self.abort()
        self.board = Board()
        self.engine.clear_hash()

    def set_position(self, fen: str | None = None, moves: list[str] | None = None) -> list[str]:
        """Rebuild the board from scratch and replay the move list.

        Rebuilding rather than mutating keeps incremental state honest, and replaying is
        what reseeds position_counts so threefold repetition works over the given moves
        (a bare FEN carries no repetition history).

        Returns the tokens it could not apply, so the caller can report them.
        """
        self.abort()
        self.board = Board.from_fen(fen or STARTING_FEN)

        rejected = []
        for token in (moves or []):
            mv = uci_to_move(self.board, token)
            if mv is None:
                rejected.append(token)
                break  # everything after an unplayable move is meaningless
            self.board._apply_temp_move(mv)

        return rejected

    def set_option(self, name: str, value: str) -> None:
        key = name.strip().lower()
        if key == "hash":
            try:
                self.hash_mb = max(1, min(1024, int(value)))
                self.engine.set_hash_size(self.hash_mb)
            except ValueError:
                pass
        elif key == "move overhead":
            try:
                self.move_overhead_ms = max(0, min(5000, int(value)))
            except ValueError:
                pass
        elif key == "clear hash":
            self.engine.clear_hash()
        # Unknown options are ignored, per the UCI spec.

    # ---------- search ----------
    def go(self, params: GoParams) -> None:
        if self.is_searching:
            return  # one search at a time: Move objects carry per-application undo state

        white_to_move = self.board.turn % 2 == 0
        budget = allocate_time(white_to_move, params, self.move_overhead_ms)

        if params.infinite or params.ponder:
            max_time, max_depth = None, MAX_PLY
        elif budget is not None:
            max_time, max_depth = budget, params.depth
        elif params.depth is not None:
            max_time, max_depth = None, params.depth
        else:
            # A bare `go` means search until told to stop.
            max_time, max_depth = None, MAX_PLY

        self.engine.max_time = max_time
        self.engine.max_depth = max_depth
        self.engine.node_limit = params.nodes
        self.engine.stop_flag = False

        # searchmoves is matched by signature: Move defines __eq__ without __hash__ and
        # so is unhashable, and regenerated Moves are different objects anyway.
        self.engine.searchmoves = None
        if params.searchmoves:
            sigs = set()
            for token in params.searchmoves:
                mv = uci_to_move(self.board, token)
                if mv is not None:
                    promo = (mv.promo_piece.name
                             if mv.typeOfMove == 3 and mv.promo_piece else None)
                    sigs.add((mv.oldPos, mv.newPos, promo))
            if sigs:
                self.engine.searchmoves = sigs

        self._infinite = params.infinite or params.ponder
        self._stop_requested = False
        self._search_start = time.perf_counter()

        self._worker = threading.Thread(target=self._run_search, daemon=True)
        self._worker.start()

    def stop(self) -> None:
        self._stop_requested = True
        self.engine.stop_flag = True

    def abort(self, timeout: float = 5.0) -> None:
        # Stop and wait. Used before anything that replaces or reads the board, since the
        # worker mutates it in place.
        if self.is_searching:
            self.stop()
            self._worker.join(timeout=timeout)

    def shutdown(self) -> None:
        self.abort()

    # ---------- internals ----------
    def _run_search(self):
        try:
            move = self.engine.choose_move(self.board)
        except Exception:
            import traceback, sys
            traceback.print_exc(file=sys.stderr)
            move = None

        # `go infinite` must not answer before `stop` arrives. The search only returns
        # early here if it somehow exhausts MAX_PLY, but the contract is explicit.
        while self._infinite and not self._stop_requested:
            time.sleep(0.005)

        if move is None:
            # No legal move, or the search was stopped before finding one.
            best = NULL_MOVE
            fallback = legal_moves(self.board)
            if fallback:
                best = move_to_uci(fallback[0])
        else:
            best = move_to_uci(move)

        if self.on_bestmove is not None:
            self.on_bestmove(best)

    def _handle_info(self, fields: dict):
        if self.on_info is None:
            return

        elapsed = fields.get("time_s", 0.0)
        nodes = fields.get("nodes", 0)
        cp, mate = classify_score(fields.get("score", 0))

        self.on_info(SearchInfo(
            depth=fields.get("depth", 0),
            seldepth=max(fields.get("seldepth", 0), fields.get("depth", 0)),
            nodes=nodes,
            time_ms=int(elapsed * 1000),
            nps=int(nodes / elapsed) if elapsed > 0 else 0,
            hashfull=fields.get("hashfull", 0),
            pv=fields.get("pv", []),
            score_cp=cp,
            score_mate=mate,
        ))
