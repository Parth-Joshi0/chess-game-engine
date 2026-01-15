from dataclasses import dataclass

from Engine.evaluation import evaluate, terminal_eval
from board import Board, Move
import math
from piece import Piece

class SearchEngine:
    def __init__(self, max_depth=4):
        self.max_depth = max_depth
        self.transposition_table : dict[bytes, TranspositionTableEntry] = {}
        self.nodes = 0

    def choose_move(self, board):
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

        return best_move

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

        childMoves = board.generate_legal_moves(board.turn%2==0)

        state = board.game_end(childMoves)
        if state != 0:
            return terminal_eval(board, state, ply)

        childMoves = self.order_moves(childMoves)
        value = -math.inf

        for move in childMoves:
            self.nodes += 1
            board._apply_temp_move(move)
            score = -self.negamax(board, depth - 1, -beta, -alpha, ply + 1)
            board._undo_temp_move(move)

            if score > value:
                value = score
                best_move = move

            alpha = max(alpha, value)
            if alpha >= beta:
                break

        if value <= alpha0:
            flag = "UPPER"
        elif value >= beta:
            flag = "LOWER"
        else:
            flag = "EXACT"

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

        moves = board.generate_legal_moves(board.turn%2==0)
        tactical = [m for m in moves if m.typeOfMove in (2,3,4)]
        tactical = self.order_moves(tactical)

        for move in tactical:
            board._apply_temp_move(move)
            score = -self.quiescence_search(board, -beta, -alpha, ply + 1)
            board._undo_temp_move(move)

            if score >= beta:
                return beta
            if score > alpha:
                alpha = score

        return alpha

@dataclass
class TranspositionTableEntry:
    depth: int
    value: int
    flag: str # "EXACT", "LOWER", "UPPER"
    best_move: object | None