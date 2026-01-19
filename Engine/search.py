from dataclasses import dataclass

from Engine.evaluation import evaluate, terminal_eval
from board import Board, Move
import math
import time
from piece import Piece

class SearchEngine:
    def __init__(self, max_depth=4):
        self.max_depth = max_depth
        self.transposition_table : dict[bytes, TranspositionTableEntry] = {}
        self.nodes = 0

    def choose_move(self, board, iterative_deep = False):
        self.nodes = 0
        start_time = time.time()
        if not iterative_deep:
            self.nodes = 0
            best_move = None
            best_value = -math.inf

            alpha = -math.inf
            beta = math.inf

            moves = board.generate_legal_moves(board.turn%2 == 0)
            if not moves:
                print("No Moves")
                return None

            for move in moves:
                board._apply_temp_move(move)
                value = -self.negamax(
                    board,
                    self.max_depth - 1,
                    -beta,
                    -alpha,
                    1
                )
                board._undo_temp_move(move)

                if value > best_value:
                    best_value = value
                    best_move = move

                alpha = max(alpha, best_value)

            end_time = time.time()
            duration = end_time - start_time

            # Calculate NPS (avoid division by zero)
            nps = self.nodes / duration if duration > 0 else 0

            print(f"Nodes: {self.nodes}")
            print(f"Time: {duration:.2f}s")
            print(f"NPS: {int(nps)} ({int(nps / 1000)} kN/s)")

            return best_move
        else:
            result = self.iterative_deepening(board, self.max_depth)
            end_time = time.time()
            duration = end_time - start_time

            # Calculate NPS (avoid division by zero)
            nps = self.nodes / duration if duration > 0 else 0

            print(f"Nodes: {self.nodes}")
            print(f"Time: {duration:.2f}s")
            print(f"NPS: {int(nps)} ({int(nps / 1000)} kN/s)")
            return result

    def negamax(self, board: Board, depth, alpha, beta, ply):
        alpha0 = alpha
        key = board.position_key()

        entry = self.transposition_table.get(key)

        if entry is not None and entry.depth >= depth:
            if entry.flag == "EXACT":
                return entry.value
            elif entry.flag == "LOWER":
                alpha = max(alpha, entry.value)
            elif entry.flag == "UPPER":
                beta = min(beta, entry.value)
            if alpha >= beta:
                return entry.value

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
            if board.in_check(board.turn%2==1):
                board._undo_temp_move(move)
                continue
            score = -self.negamax(board, depth - 1, -beta, -alpha, ply + 1)
            legal_move_found = True
            if board.moveRuleTurns >= 50 or board.position_counts[board.position_key()] >= 3:
                board._undo_temp_move(move)
                return 0
            board._undo_temp_move(move)

            if score > value:
                value = score
                best_move = move

            alpha = max(alpha, value)
            if alpha >= beta:
                break

        if not legal_move_found:
            if board.in_check(board.turn % 2 == 0):
                return -1000000000 + ply  # Checkmate
            else:
                return 0 # Stalemate

        if value <= alpha0:
            flag = "UPPER"
        elif value >= beta:
            flag = "LOWER"
        else:
            flag = "EXACT"

        if best_move is not None:
            self.transposition_table[key] = TranspositionTableEntry(depth=depth, value=value, flag=flag, best_move=best_move)

        return value

    def order_moves(self, moves):

        def abs_worth(p: Piece):
            return abs(p.piece_worth()) if p else 0

        def score_moves(m: Move):
            t = m.typeOfMove

            attacker = abs_worth(m.piece)
            victim_or_promo = abs_worth(m.piece2)

            if t == 3: #promotion
                return 10000000 + victim_or_promo

            if t == 2 or t == 4:
                mvv_lva = victim_or_promo * 10 - attacker
                return 500000 + mvv_lva

            if t == 1:
                return 100000

            return 0

        return sorted(moves, key=score_moves, reverse=True)

    def quiescence_search(self, board, alpha, beta, ply):
        stand_pat = evaluate(board, False)

        if stand_pat >= beta:
            return beta

        if stand_pat > alpha:
            alpha = stand_pat

        moves = board.get_pseudo_legal_moves(board.turn%2==0)
        tactical = [m for m in moves if m.typeOfMove in (2,3,4)]
        tactical = self.order_moves(tactical)

        for move in tactical:
            self.nodes += 1
            board._apply_temp_move(move)
            if board.in_check(board.turn%2==1):
                board._undo_temp_move(move)
                continue
            score = -self.quiescence_search(board, -beta, -alpha, ply + 1)
            board._undo_temp_move(move)

            if score >= beta:
                return beta
            if score > alpha:
                alpha = score

        return alpha

    def iterative_deepening(self, board, max_depth=None):
        if max_depth is None:
            max_depth = self.max_depth

        best_move = None
        best_value = -math.inf

        for depth in range(1, max_depth + 1):
            value, move = self._search_root(board, depth)
            if move is not None:
                best_move = move
                best_value = value

        if best_move is not None:
            best_value = best_value if board.turn % 2 == 0 else -best_value
            print(f"Evaluation: {best_value}")
        else:
            print(f"Evaluation: No legal moves (checkmate/stalemate)")

        return best_move

    def _search_root(self, board, depth):
        best_move = None
        best_value = -math.inf

        alpha = -math.inf
        beta = math.inf

        moves = board.get_pseudo_legal_moves(board.turn%2==0)
        moves = self.order_moves(moves)

        legal_move_found = False
        for move in moves:
            board._apply_temp_move(move)
            if board.in_check(board.turn%2==1):
                board._undo_temp_move(move)
                continue
            value = -self.negamax(board, depth - 1, -beta, -alpha, 1)
            board._undo_temp_move(move)
            legal_move_found = True
            if value > best_value:
                best_value = value
                best_move = move

            alpha = max(alpha, best_value)

        if not legal_move_found:
            return -math.inf, None

        return best_value, best_move

@dataclass
class TranspositionTableEntry:
    depth: int
    value: int
    flag: str # "EXACT", "LOWER", "UPPER"
    best_move: object | None