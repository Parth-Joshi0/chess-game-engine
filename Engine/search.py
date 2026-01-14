from Engine.evaluation import evaluate, terminal_eval
from board import Board, Move
import math
from piece import Piece

class SearchEngine:
    def __init__(self, max_depth=4):
        self.max_depth = max_depth

    def choose_move(self, board):
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

    def negamax(self, board, depth, alpha, beta, ply):
        if depth == 0:
            return evaluate(board, False)

        childMoves = board.generate_legal_moves(board.turn%2==0)

        state = board.game_end(childMoves)
        if state != 0:
            return terminal_eval(board, state)

        childMoves = self.order_moves(board, childMoves)
        value = -math.inf

        for move in childMoves:
            board._apply_temp_move(move)
            value = max(value, -self.negamax(board, depth - 1, -beta, -alpha, ply+1))
            board._undo_temp_move(move)
            alpha = max(alpha, value)
            if alpha >= beta:
                break
        return value

    def order_moves(self, board, moves):

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