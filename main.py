import pygame
from board import *
from piece import *

BOARD_SIZE = 8
SQ_SIZE = 80
WIDTH = HEIGHT = BOARD_SIZE * SQ_SIZE
FPS = 60

LIGHT = (240, 217, 181)
DARK = (181, 136, 99)
SELECTION_HIGHLIGHT = (100, 200, 255)
MOVE_HIGHLIGHT = (235, 200, 40)
CAPTURE_HIGHLIGHT = (200, 60, 60)

UNICODE = {
    "wK": "♔", "wQ": "♕", "wR": "♖", "wB": "♗", "wN": "♘", "wP": "♙",
    "bK": "♚", "bQ": "♛", "bR": "♜", "bB": "♝", "bN": "♞", "bP": "♟",
}
GAME_END_STATE = {
    1: "Checkmate!", 2: "Stalemate!", 3: "Draw by 50 move rule"
}

class Square:
    def __init__(self, row, col):
        self.row = row
        self.col = col

    def __eq__(self, other):
        return isinstance(other, Square) and self.row == other.row and self.col == other.col

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Chess")
        self.clock = pygame.time.Clock()
        self.running = True
        self.board = Board()

        self.selected = None
        self.selected_from = None

        self.font = pygame.font.SysFont("arialunicode", 64)

        self.game_over = False
        self.game_over_text = ""

        self.big_font = pygame.font.SysFont("arialunicode", 48)
        self.small_font = pygame.font.SysFont("arialunicode", 28)

        self.promotion_pending_ui = False
        self.promotion_choices = ["Q", "R", "B", "N"]
        self.promotion_rects = {}

    def run(self):
        while self.running:
            self.clock.tick(FPS)
            self.handle_events()
            self.render()

        pygame.quit()

    # ---------- Input ----------
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.promotion_pending_ui:
                    choice = self.get_promotion_choice_from_click(pygame.mouse.get_pos())
                    if choice:
                        self.board.finalize_promotion(choice)
                        self.promotion_pending_ui = False
                        game_status = self.board.game_end()
                        if game_status != 0:
                            self.game_over = True
                            self.game_over_text = GAME_END_STATE[game_status]
                        return
                    return

                sq = self.mouse_to_square(pygame.mouse.get_pos())
                if sq:
                    self.on_click_square(sq)
            elif event.type == pygame.KEYDOWN and self.game_over:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_r:
                    self.board = Board()
                    self.selected = None
                    self.selected_from = None
                    self.game_over = False
                    self.game_over_text = ""

    def mouse_to_square(self, pos):
        x, y = pos
        if 0 <= x < WIDTH and 0 <= y < HEIGHT:
            return Square(y // SQ_SIZE, x // SQ_SIZE)
        return None

    def on_click_square(self, sq):
        if self.game_over:
            return

        x, y = sq.col, sq.row  # (col,row)
        pos = (x, y)  # (x,y)

        # If nothing selected: try selecting a piece
        if self.selected_from is None:
            piece = self.board.boardList[y][x]  # boardList[row][col]
            if piece is not None:
                if (self.board.turn % 2 == 0 and piece.colour is True) or (self.board.turn % 2 == 1 and piece.colour is False):
                    self.selected_from = pos
                    self.selected = sq
            return

        # Otherwise attempt move
        from_pos = self.selected_from
        to_pos = pos

        if to_pos == from_pos:
            self.selected_from = None
            self.selected = None
            return

        x1, y1 = from_pos
        piece = self.board.boardList[y1][x1]
        if piece is None:
            self.selected_from = None
            self.selected = None
            return

        attempted = Move(from_pos, to_pos, piece)
        moved = self.board.move(attempted)

        if moved == "VALID_MOVE":
            # success: clear selection
            self.selected_from = None
            self.selected = None
            if (self.board.game_end() != 0):
                self.game_over = True
                self.game_over_text = "Checkmate!" if self.board.game_end() == 1 else "Stalemate!"
        elif moved == "PROMOTION":
            self.promotion_pending_ui = True
            self.selected = None
            self.selected_from = None
        else:
            # failed: either keep selection, or switch selection to clicked piece
            clicked_piece = self.board.boardList[y][x]
            if clicked_piece is not None and clicked_piece.colour is piece.colour:
                self.selected_from = to_pos
                self.selected = sq
            # else keep current selection (do nothing)

    def get_promotion_choice_from_click(self, mouse_pos):
        for choice, rect in self.promotion_rects.items():
            if rect.collidepoint(mouse_pos):
                return choice
        return None

    # ---------- Rendering ----------
    def render(self):
        self.draw_board()
        if self.promotion_pending_ui:
            self.draw_promotion_overlay()
        self.draw_selection()
        self.draw_pieces()
        if self.game_over:
            self.draw_game_over_popup()
        pygame.display.flip()

    def draw_board(self):
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                color = LIGHT if (r + c) % 2 == 0 else DARK
                rect = pygame.Rect(c * SQ_SIZE, r * SQ_SIZE, SQ_SIZE, SQ_SIZE)
                pygame.draw.rect(self.screen, color, rect)

    def draw_selection(self):
        if not self.selected:
            return
        r, c = self.selected.row, self.selected.col
        rect = pygame.Rect(c * SQ_SIZE, r * SQ_SIZE, SQ_SIZE, SQ_SIZE)
        pygame.draw.rect(self.screen, SELECTION_HIGHLIGHT, rect, 4)
        self.draw_avaliable_moves()

    def draw_avaliable_moves(self):
        r, c = self.selected.row, self.selected.col
        p = self.board.boardList[r][c]

        if p is None:
            return

        moves = self.board.get_legal_moves_by_piece(p)
        for move in moves:
            x, y = move.newPos[0], move.newPos[1]
            rect = pygame.Rect(x * SQ_SIZE, y * SQ_SIZE, SQ_SIZE, SQ_SIZE)
            if move.typeOfMove == 4 or move.typeOfMove == 2:
                pygame.draw.rect(self.screen, CAPTURE_HIGHLIGHT, rect, 4)
            elif move.typeOfMove == 3 and move.oldPos[0] != move.newPos[0]:
                pygame.draw.rect(self.screen, CAPTURE_HIGHLIGHT, rect, 4)
            else:
                pygame.draw.rect(self.screen, MOVE_HIGHLIGHT, rect, 4)

    def draw_pieces(self):
        for row in range(8):
            for col in range(8):
                p = self.board.boardList[row][col]
                if p is None:
                    continue

                code = self.piece_to_code(p)
                symbol = UNICODE[code]
                img = self.font.render(symbol, True, (0, 0, 0))

                center_x = col * SQ_SIZE + SQ_SIZE // 2
                center_y = row * SQ_SIZE + SQ_SIZE // 2
                rect = img.get_rect(center=(center_x, center_y))
                self.screen.blit(img, rect)

    def piece_to_code(self, p: Piece):
        prefix = "w" if p.colour else "b"
        letter = {
            "king": "K",
            "queen": "Q",
            "rook": "R",
            "bishop": "B",
            "knight": "N",
            "pawn": "P",
        }[p.name]
        return prefix + letter

    def draw_game_over_popup(self):
        print(self.game_over_text)
        # dark transparent overlay
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))  # last value = alpha
        self.screen.blit(overlay, (0, 0))

        # popup box
        box_w, box_h = 520, 220
        box = pygame.Rect((WIDTH - box_w) // 2, (HEIGHT - box_h) // 2, box_w, box_h)
        pygame.draw.rect(self.screen, (245, 245, 245), box, border_radius=16)
        pygame.draw.rect(self.screen, (40, 40, 40), box, 3, border_radius=16)


        title = self.big_font.render(self.game_over_text, True, (20, 20, 20))
        hint = self.small_font.render("Press R to restart  •  Esc to quit", True, (40, 40, 40))

        title_rect = title.get_rect(center=(WIDTH // 2, box.centery - 30))
        hint_rect = hint.get_rect(center=(WIDTH // 2, box.centery + 50))

        self.screen.blit(title, title_rect)
        self.screen.blit(hint, hint_rect)

    def draw_promotion_overlay(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        self.screen.blit(overlay, (0, 0))

        # buttons
        w, h = 140, 60
        gap = 20
        total_w = 4 * w + 3 * gap
        start_x = (WIDTH - total_w) // 2
        y = (HEIGHT - h) // 2

        self.promotion_rects = {}
        for i, choice in enumerate(self.promotion_choices):
            rect = pygame.Rect(start_x + i * (w + gap), y, w, h)
            self.promotion_rects[choice] = rect
            pygame.draw.rect(self.screen, (240, 240, 240), rect, border_radius=8)
            pygame.draw.rect(self.screen, (30, 30, 30), rect, 2, border_radius=8)

            label = UNICODE["b" + choice]
            img = self.font.render(label, True, (0, 0, 0))
            self.screen.blit(img, img.get_rect(center=rect.center))

        # optional instruction text
        msg = self.small_font.render("Choose promotion:", True, (255, 255, 255))
        self.screen.blit(msg, (start_x, y - 40))

if __name__ == '__main__':
    Game().run()