from Engine.evaluation import evaluate, terminal_eval
from board import Board
import math

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
        elif self.is_terminal(board):
            return terminal_eval(board)

        childMoves = board.generate_legal_moves(board.turn%2==0)
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

    def is_terminal(self, board: Board):
        state = board.game_end()
        if state == 0:
            return False
        return True

    def order_moves(self, board, moves):
        return moves