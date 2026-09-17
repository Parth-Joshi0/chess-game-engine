from dataclasses import dataclass
from Engine.evaluation import evaluate
from board import Board, Move, HALFMOVE_DRAW_PLIES
import math
import time
from piece import Piece

# Deepest ply the PV table tracks, and the depth cap for an otherwise unbounded search.
MAX_PLY = 64

# Mate is scored as -(MATE_VALUE) + ply, so scores near the magnitude of MATE_VALUE are
# mates rather than evaluations. The threshold leaves room for the deepest possible ply.
MATE_VALUE = 1000000000
MATE_THRESHOLD = MATE_VALUE - 10000

class SearchTimeout(Exception):
    # Raised when the search must abort: deadline passed, node limit hit, or stop requested
    pass

class SearchEngine:
    def __init__(self, max_depth=None, max_time=None, on_info=None, verbose=True,
                 tt_size_mb=64):
        self.max_depth = max_depth
        self.max_time = max_time
        self._deadline = None
        self.nodes = 0
        self.seldepth = 0

        # Set from another thread to abort the search (UCI "stop"/"quit").
        self.stop_flag = False
        self.node_limit = None
        # Restrict the root to these move signatures (UCI "searchmoves"), or None for all.
        self.searchmoves = None

        # on_info(dict) receives one record per completed iteration; verbose controls the
        # legacy human-readable prints. The pygame GUI uses the defaults and is unaffected.
        self.on_info = on_info
        self.verbose = verbose

        self.set_hash_size(tt_size_mb)

        # Triangular PV table: pv[ply] holds the principal variation from that ply down.
        self.pv = [[None] * MAX_PLY for _ in range(MAX_PLY)]
        self.pv_len = [0] * MAX_PLY

    # ---------- Transposition table ----------
    def set_hash_size(self, mb):
        # Bucket array rather than an unbounded dict, so a long-running session cannot
        # grow without limit and hashfull becomes meaningful.
        entries = max(1024, int(mb) * 1024 * 1024 // 64)
        self.tt_size = entries
        self.transposition_table = [None] * entries
        self.tt_used = 0

    def clear_hash(self):
        self.transposition_table = [None] * self.tt_size
        self.tt_used = 0

    def tt_index(self, key):
        # position_key() is now a Zobrist hash (see board.py / zobrist.py): every bit is
        # the XOR of independent random 64-bit values, so it's already uniformly
        # distributed and any slice of it (mod table size) is a good index.
        return key % self.tt_size

    def tt_lookup(self, key):
        entry = self.transposition_table[self.tt_index(key)]
        # The slot stores its key so a collision is detected rather than trusted.
        if entry is not None and entry.key == key:
            return entry
        return None

    def tt_store(self, key, depth, value, flag, best_move):
        idx = self.tt_index(key)
        existing = self.transposition_table[idx]
        # Depth-preferred replacement: keep the more expensive result unless it is for a
        # different position, in which case the newer one is more relevant.
        if existing is not None and existing.key == key and existing.depth > depth:
            return
        if existing is None:
            self.tt_used += 1
        # Store a signature, not the Move: a Move pins a whole Piece graph and carries
        # per-application undo state, neither of which survives leaving this search.
        sig = None
        if best_move is not None:
            promo = (best_move.promo_piece.name
                     if best_move.typeOfMove == 3 and best_move.promo_piece else None)
            sig = (best_move.oldPos, best_move.newPos, promo)
        self.transposition_table[idx] = TranspositionTableEntry(
            key=key, depth=depth, value=value, flag=flag, best_move=sig)

    def hashfull(self):
        return min(1000, int(1000 * self.tt_used / self.tt_size))

    def choose_move(self, board):
        self.nodes = 0
        self.seldepth = 0
        self._deadline = None  # never inherit a deadline from a previous search
        start_time = time.perf_counter()

        if self.max_time is not None:
            result = self.iterative_deepening_time(board)
        else:
            result = self.iterative_deepening(board)

        end_time = time.perf_counter()
        duration = end_time - start_time

        if self.verbose:
            # Calculate NPS (avoid division by zero)
            nps = self.nodes / duration if duration > 0 else 0
            print(f"Nodes: {self.nodes}")
            print(f"Time: {duration:.2f}s")
            print(f"NPS: {int(nps)} ({int(nps / 1000)} kN/s)")

        return result

    def _emit_info(self, **fields):
        if self.on_info is not None:
            self.on_info(fields)

    def _collect_pv(self):
        # Snapshot the PV as UCI strings immediately: Move objects must never outlive the
        # search that produced them.
        from notation import move_to_uci
        return [move_to_uci(m) for m in self.pv[0][:self.pv_len[0]] if m is not None]

    def _update_pv(self, ply, move):
        if ply + 1 >= MAX_PLY:
            return
        self.pv[ply][ply] = move
        for n in range(ply + 1, self.pv_len[ply + 1]):
            self.pv[ply][n] = self.pv[ply + 1][n]
        self.pv_len[ply] = max(self.pv_len[ply + 1], ply + 1)

    def negamax(self, board: Board, depth, alpha, beta, ply):
        # Negamax search with alpha-beta pruning and transposition table

        self._check_time()
        alpha0 = alpha

        if ply < MAX_PLY:
            self.pv_len[ply] = ply

        key = board.position_key()

        entry = self.tt_lookup(key)

        # Check transposition table
        if entry is not None and entry.depth >= depth:
            if entry.flag == "EXACT":
                return entry.value
            elif entry.flag == "LOWER":
                alpha = max(alpha, entry.value)
            elif entry.flag == "UPPER":
                beta = min(beta, entry.value)
            if alpha >= beta:
                return entry.value

        # At leaf nodes use quiescence search instead
        if depth == 0:
            return self.quiescence_search(board, alpha, beta, ply)

        childMoves = board.get_pseudo_legal_moves(board.turn%2==0)
        best_move = None

        childMoves = self.order_moves(childMoves)
        value = -math.inf
        legal_move_found = False

        for move in childMoves:

            self.nodes += 1
            board._apply_temp_move(move)

            try:
                # Skip illegal moves, (king in check)
                if board.in_check(board.turn%2==1):
                    board._undo_temp_move(move)
                    continue

                legal_move_found = True

                # draw checks
                if board.moveRuleTurns >= HALFMOVE_DRAW_PLIES or board.position_counts[board.position_key()] >= 3:
                    board._undo_temp_move(move)

                    if 0 > value:
                        value = 0
                        best_move = move
                        # The PV ends here. Don't use _update_pv: we never recursed, so
                        # pv_len[ply + 1] still describes a previous sibling's subtree
                        # and splicing it would report a line that was not searched.
                        if ply < MAX_PLY:
                            self.pv[ply][ply] = move
                            self.pv_len[ply] = ply + 1
                    continue

                score = -self.negamax(board, depth - 1, -beta, -alpha, ply + 1)
                board._undo_temp_move(move)

                if score > value:
                    value = score
                    best_move = move
                    if ply < MAX_PLY:
                        self._update_pv(ply, move)

                alpha = max(alpha, value)

                # Beta cutoff
                if alpha >= beta:
                    break
            except:
                board._undo_temp_move(move)
                raise

        # No legal moves : Stalemate or Checkmate
        if not legal_move_found:
            if board.in_check(board.turn % 2 == 0):
                return -MATE_VALUE + ply  # Checkmate (ply for preferring faster mates)
            else:
                return 0 # Stalemate

        # store in transposition table
        if value <= alpha0:
            flag = "UPPER"
        elif value >= beta:
            flag = "LOWER"
        else:
            flag = "EXACT"

        if best_move is not None:
            self.tt_store(key, depth, value, flag, best_move)

        return value

    def order_moves(self, moves):
        # Sort moves for better alpha - beta pruning, (captures first)

        def abs_worth(p: Piece):
            return abs(p.piece_worth()) if p else 0

        def score_moves(m: Move):
            t = m.typeOfMove

            attacker = abs_worth(m.piece)
            victim_or_promo = abs_worth(m.piece2)

            if t == 3: # Promotion
                return 10000000 + victim_or_promo

            if t == 2 or t == 4:
                # Most Valuable Victim - Least Valuable Attacker
                mvv_lva = victim_or_promo * 10 - attacker
                return 500000 + mvv_lva

            if t == 1: # Castling
                return 100000

            return 0

        return sorted(moves, key=score_moves, reverse=True)

    def quiescence_search(self, board, alpha, beta, ply):
        # Search only tactical moves till the position is stabilized

        self._check_time()
        if ply > self.seldepth:
            self.seldepth = ply
        stand_pat = evaluate(board, False)

        if stand_pat >= beta:
            return beta

        if stand_pat > alpha:
            alpha = stand_pat

        moves = board.get_pseudo_legal_moves(board.turn%2==0)

        # Search only promotions, captures and en-passant
        tactical = [m for m in moves if m.typeOfMove in (2,3,4)]
        tactical = self.order_moves(tactical)

        for move in tactical:
            self.nodes += 1
            board._apply_temp_move(move)
            try:

                if board.in_check(board.turn%2==1):
                    board._undo_temp_move(move)
                    continue

                score = -self.quiescence_search(board, -beta, -alpha, ply + 1)
                board._undo_temp_move(move)

                if score >= beta:
                    return beta
                if score > alpha:
                    alpha = score

            except:
                board._undo_temp_move(move)
                raise

        return alpha

    def iterative_deepening(self, board):
        # Search Progressively Deeper till max depth reached

        best_move = None
        best_value = -math.inf
        start = time.perf_counter()

        max_depth = self.max_depth if self.max_depth is not None else MAX_PLY

        for depth in range(1, max_depth + 1):
            # A stop request or node limit aborts through _check_time even in fixed-depth
            # mode. Without this catch the exception would escape the search thread and
            # no bestmove would ever be sent.
            try:
                value, move = self._search_root(board, depth)
            except SearchTimeout:
                break

            if move is not None:
                best_move = move
                best_value = value
                self._emit_info(depth=depth, seldepth=self.seldepth, score=value,
                                nodes=self.nodes, time_s=time.perf_counter() - start,
                                hashfull=self.hashfull(), pv=self._collect_pv())

        if self.verbose:
            # Print evaluation from white's perspective
            if best_move is not None:
                shown = best_value if board.turn % 2 == 0 else -best_value
                print(f"Evaluation: {shown}")
            else:
                print(f"Evaluation: No legal moves (checkmate/stalemate)")

        return best_move

    def _search_root(self, board, depth):
        # Search from root position

        self._check_time()
        best_move = None
        best_value = -math.inf

        alpha = -math.inf
        beta = math.inf

        self.pv_len[0] = 0

        moves = board.get_pseudo_legal_moves(board.turn%2==0)
        moves = self.order_moves(moves)

        legal_move_found = False
        for move in moves:
            if self.searchmoves is not None and not self._in_searchmoves(move):
                continue

            board._apply_temp_move(move)
            try:
                if board.in_check(board.turn%2==1):
                    board._undo_temp_move(move)
                    continue
                value = -self.negamax(board, depth - 1, -beta, -alpha, 1)
                board._undo_temp_move(move)
                legal_move_found = True
                if value > best_value:
                    best_value = value
                    best_move = move
                    self._update_pv(0, move)

                alpha = max(alpha, best_value)
            except:
                board._undo_temp_move(move)
                raise

        if not legal_move_found:
            return -math.inf, None

        return best_value, best_move

    def _in_searchmoves(self, move):
        promo = (move.promo_piece.name
                 if move.typeOfMove == 3 and move.promo_piece else None)
        return (move.oldPos, move.newPos, promo) in self.searchmoves

    def _check_time(self):
        # Called at every node. Ordered cheapest-first; the perf_counter() call stays
        # behind the max_time guard so timed searches cost no more than before, while
        # stop and node limits now work in fixed-depth mode too.
        if self.stop_flag:
            raise SearchTimeout()
        if self.node_limit is not None and self.nodes >= self.node_limit:
            raise SearchTimeout()
        if self.max_time and self._deadline is not None and time.perf_counter() >= self._deadline:
            raise SearchTimeout()

    def iterative_deepening_time(self, board):
        # Search progressively deeper until time limit reached
        root_moves = board.generate_legal_moves(board.turn % 2 == 0)
        if not root_moves:
            return None

        start = time.perf_counter()
        self._deadline = start + float(self.max_time)

        best_move = root_moves[0]  # fallback
        best_value = -math.inf

        depth = 1
        while True:
            try:
                value_d, move_d = self._search_root(board, depth)

                if move_d is not None:
                    best_move, best_value = move_d, value_d
                    self._emit_info(depth=depth, seldepth=self.seldepth, score=value_d,
                                    nodes=self.nodes, time_s=time.perf_counter() - start,
                                    hashfull=self.hashfull(), pv=self._collect_pv())

                depth += 1

                if depth > MAX_PLY:
                    break

                # A depth cap and a clock can be given together (UCI "go depth N" with a
                # movetime); honour whichever runs out first.
                if self.max_depth is not None and depth > self.max_depth:
                    break

                # Each iteration costs several times the last, so with over half the
                # budget already spent the next one cannot finish. Returning now leaves
                # the time on the clock instead of throwing it away on a discarded search.
                if (time.perf_counter() - start) > 0.5 * self.max_time:
                    break

            except SearchTimeout:
                break

        if self.verbose:
            if best_move is not None:
                shown = best_value if board.turn % 2 == 0 else -best_value
                print(f"Evaluation: {shown}")
            else:
                print(f"Evaluation: No legal moves (checkmate/stalemate)")

        return best_move

@dataclass
class TranspositionTableEntry:
    key: bytes
    depth: int
    value: int
    flag: str # "EXACT", "LOWER", "UPPER"
    best_move: tuple | None # (oldPos, newPos, promo_name) -- never a Move object