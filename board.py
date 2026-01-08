from piece import *
class Move:
    def __init__(self, oldPos, newPos, piece, piece2=None, typeOfMove=0):
        self.oldPos = oldPos
        self.newPos = newPos
        self.piece = piece
        self.piece2 = piece2
        self.typeOfMove = typeOfMove #0 for regular moving move, 1 for castling, 2 for enPassant, 3 for Promotion, 4 for capture
        self.piece2OldPos = (-1,-1)
        self.piece2NewPos = (-1,-1)

    def __eq__(self, other):
        if self.piece == other.piece and self.oldPos == other.oldPos and self.newPos == other.newPos:
            return True
        return False

class Board:
    def __init__(self):
        self.blackPieces = []
        self.whitePieces = []

        self.whiteKing = None
        self.blackKing = None

        self.turn = 0
        self.boardList = self.boardList = [[None for _ in range(8)] for _ in range(8)]

        self.blackCastle = True
        self.whiteCastle = True
        self.enPassantTarget = None

        self.generate_board()

    def generate_board(self):
        WHITE = True
        BLACK = False

        # White back rank (row 7)
        self.whiteKing = King(WHITE, 4, 7)
        self.whitePieces = [
            Rook(WHITE, 0, 7),
            Knight(WHITE, 1, 7),
            Bishop(WHITE, 2, 7),
            Queen(WHITE, 3, 7),
            self.whiteKing,
            Bishop(WHITE, 5, 7),
            Knight(WHITE, 6, 7),
            Rook(WHITE, 7, 7),
        ]

        # Black back rank (row 0)
        self.blackKing = King(BLACK, 4, 0)
        self.blackPieces = [
            Rook(BLACK, 0, 0),
            Knight(BLACK, 1, 0),
            Bishop(BLACK, 2, 0),
            Queen(BLACK, 3, 0),
            self.blackKing,
            Bishop(BLACK, 5, 0),
            Knight(BLACK, 6, 0),
            Rook(BLACK, 7, 0),
        ]

        for i in range(8):
            self.boardList[7][i] = self.whitePieces[i]
            self.boardList[0][i] = self.blackPieces[i]

            wp = Pawn(WHITE, i, 6)  # col=i, row=6
            self.boardList[6][i] = wp
            self.whitePieces.append(wp)

            bp = Pawn(BLACK, i, 1)  # col=i, row=1
            self.boardList[1][i] = bp
            self.blackPieces.append(bp)

    def get_pseudo_legal_moves_by_piece(self, piece : Piece) -> list[Move]:
        moves = []
        if piece.name == "king":
            moves = self.basic_moves(piece) + self.castling_moves(piece)
        elif piece.name == "knight":
            moves = self.basic_moves(piece)
        elif piece.name == "rook":
            moves = self.rook_legal_moves(piece)
        elif piece.name == "bishop":
            moves = self.bishop_legal_moves(piece)
        elif piece.name == "queen":
            moves = self.queen_legal_moves(piece)
        elif piece.name == "pawn":
            moves = self.pawn_legal_moves(piece)
        return moves

    def rook_legal_moves(self, piece: Piece) -> list[Move]:
        directions = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        return self.ray_moves(piece, directions)

    def bishop_legal_moves(self, piece: Piece) -> list[Move]:
        directions = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
        return self.ray_moves(piece, directions)

    def queen_legal_moves(self, piece: Piece) -> list[Move]:
        directions = [
            (1, 0), (-1, 0), (0, 1), (0, -1),
            (1, 1), (1, -1), (-1, 1), (-1, -1)
        ]
        return self.ray_moves(piece, directions)

    def pawn_legal_moves(self, piece: Piece) -> list[Move]:
        moves = []
        x, y = piece.pos

        direction = -1 if piece.colour else 1
        start_row = 6 if piece.colour else 1
        promotion_row = 0 if piece.colour else 7

        #1 square forward
        y1 = y + direction
        if 0 <= y1 <= 7 and self.boardList[y1][x] is None:
            moves.append(Move((x, y), (x, y1), piece))

            #2 squares forward
            y2 = y + 2 * direction
            if y == start_row and self.boardList[y2][x] is None:
                moves.append(Move((x, y), (x, y2), piece))

        #captures
        for dx in (-1, 1):
            x2 = x + dx
            y2 = y + direction
            if 0 <= x2 <= 7 and 0 <= y2 <= 7:
                target = self.boardList[y2][x2]
                if target is not None and target.colour != piece.colour:
                    moves.append(Move((x, y), (x2, y2), piece, piece2=target, typeOfMove=4))

        #promotion flag
        for m in moves:
            if m.newPos[1] == promotion_row:
                m.typeOfMove = 3  # promotion

        # en Passant
        if self.enPassantTarget is not None:
            tx, ty = self.enPassantTarget
            pawn = self.boardList[ty-direction][tx]
            if ty == piece.pos[1] + direction and abs(tx - piece.pos[0]) == 1:
                if pawn and pawn.colour != piece.colour and pawn.name == "pawn":
                    m = Move(piece.pos, (tx, ty), piece, piece2=pawn, typeOfMove=2)
                    m.piece2OldPos = (tx, ty-direction)
                    moves.append(m)

        return moves

    def ray_moves(self, piece: Piece, directions) -> list[Move]:
        moves = []
        x1, y1 = piece.pos

        for dx, dy in directions:
            x, y = x1 + dx, y1 + dy

            while 0 <= x <= 7 and 0 <= y <= 7:
                target = self.boardList[y][x]

                # empty square: can move, keep going
                if target is None:
                    moves.append(Move((x1, y1), (x, y), piece))
                else:
                    # occupied: capture if enemy, then stop
                    if target.colour != piece.colour:
                        moves.append(Move((x1, y1), (x, y), piece, piece2=target, typeOfMove=4))
                    break

                x += dx
                y += dy

        return moves

    def basic_moves(self, piece: Piece) -> list[Move]:
        moves = piece.moves_available()
        legals = []
        x1 = piece.pos[0]
        y1 = piece.pos[1]
        for m in moves:
            x2 = m[0]
            y2 = m[1]
            target = self.boardList[y2][x2]
            if target is None:
                legals.append(Move((x1, y1), (x2, y2), piece))
            elif target.colour != piece.colour:
                legals.append(Move((x1,y1), (x2,y2), piece, piece2=target, typeOfMove=4))
        return legals

    def castling_moves(self, piece: Piece) -> list[Move]:
        king = self.whiteKing if piece.colour else self.blackKing
        row = 7 if piece.colour else 0
        if king.hasMoved:
            return []

        rook1 = self.boardList[row][0]
        rook2 = self.boardList[row][7]

        moves = []
        if rook1 and rook1.name == "rook" and not rook1.hasMoved:
            empty = self.boardList[row][1] is None and self.boardList[row][2] is None and self.boardList[row][3] is None
            attacked = self.is_square_attacked(4, row, not piece.colour) or self.is_square_attacked(2, row, not piece.colour) or self.is_square_attacked(3, row, not piece.colour)
            if empty and not attacked:
                move = Move(king.pos, (2, row), king, rook1, 1)
                move.piece2NewPos = (3, row)
                move.piece2OldPos = rook1.pos
                moves.append(move)

        if rook2 and rook2.name == "rook" and not rook2.hasMoved:
            empty = self.boardList[row][5] is None and self.boardList[row][6] is None
            attacked = self.is_square_attacked(5, row, not piece.colour) or self.is_square_attacked(6, row, not piece.colour) or self.is_square_attacked(4, row, not piece.colour)
            if empty and not attacked:
                move = Move(king.pos, (6, row), king, rook2, 1)
                move.piece2NewPos = (5, row)
                move.piece2OldPos = rook2.pos
                moves.append(move)

        return moves

    def move(self, move: Move) -> bool:
        legal_moves = self.get_legal_moves_by_piece((move.piece))

        found = False
        for m in legal_moves:
            if m.oldPos == move.oldPos and m.newPos == move.newPos:
                move = m
                found = True
                break

        if not found:
            return False

        x1, y1 = move.oldPos
        x2, y2 = move.newPos

        self.enPassantTarget = None

        if move.typeOfMove == 0:
            piece = self.boardList[y1][x1]
            self.boardList[y1][x1] = None

            self.boardList[y2][x2] = piece
            piece.move(x2,y2)
            self.turn += 1

            if move.piece.name == "pawn" and abs(y2 - y1) == 2:
                passed_y = (y1 + y2) // 2
                self.enPassantTarget = (x1, passed_y)

        elif move.typeOfMove == 1: #Castle
            king = self.boardList[y1][x1]
            self.boardList[y1][x1] = None
            self.boardList[y2][x2] = king
            king.move(x2, y2)

            rx1, ry1 = move.piece2OldPos
            rx2, ry2 = move.piece2NewPos

            rook = self.boardList[ry1][rx1]
            self.boardList[ry1][rx1] = None
            self.boardList[ry2][rx2] = rook
            rook.move(ry2, ry1)

            self.turn += 1

        elif move.typeOfMove == 2: #en-passant
            piece = self.boardList[y1][x1]
            self.boardList[y1][x1] = None

            px1, py1 = move.piece2OldPos
            self.boardList[py1][px1] = None

            if move.piece2.colour:
                self.whitePieces.remove(move.piece2)
            else:
                self.blackPieces.remove(move.piece2)

            self.boardList[y2][x2] = piece
            piece.move(x2, y2)
            self.turn += 1

        elif move.typeOfMove == 4: #Capture
            piece = self.boardList[y1][x1]
            self.boardList[y1][x1] = None

            target = self.boardList[y2][x2]
            if target:
                if target.colour:
                    self.whitePieces.remove(target)
                else:
                    self.blackPieces.remove(target)

            self.boardList[y2][x2] = piece
            piece.move(x2, y2)
            self.turn += 1
        return True

    def is_square_attacked(self, x: int, y: int, by_colour: bool) -> bool:
        def in_bounds(cx, cy):
            return 0 <= cx <= 7 and 0 <= cy <= 7

        #Pawn attacks
        pawn_dir = -1 if by_colour else 1
        for dx in (-1, 1):
            ax, ay = x + dx, y + pawn_dir
            if in_bounds(ax, ay):
                p = self.boardList[ay][ax]
                if p is not None and p.colour == by_colour and p.name == "pawn":
                    return True

        #Knight attacks
        knight_offsets = [(2, 1), (2, -1), (-2, 1), (-2, -1), (1, 2), (1, -2), (-1, 2), (-1, -2)]
        for dx, dy in knight_offsets:
            ax, ay = x + dx, y + dy
            if in_bounds(ax, ay):
                p = self.boardList[ay][ax]
                if p is not None and p.colour == by_colour and p.name == "knight":
                    return True

        #King Attacks: No castling checks
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                ax, ay = x + dx, y + dy
                if in_bounds(ax, ay):
                    p = self.boardList[ay][ax]
                    if p is not None and p.colour == by_colour and p.name == "king":
                        return True

        #Rook & Queen Attacks
        rook_dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        for dx, dy in rook_dirs:
            ax, ay = x + dx, y + dy
            while in_bounds(ax, ay):
                p = self.boardList[ay][ax]
                if p is None:
                    ax += dx
                    ay += dy
                    continue
                # first piece on this ray blocks further
                if p.colour == by_colour and (p.name == "rook" or p.name == "queen"):
                    return True
                break

        #Bishop & Queen Attacks
        bishop_dirs = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
        for dx, dy in bishop_dirs:
            ax, ay = x + dx, y + dy
            while in_bounds(ax, ay):
                p = self.boardList[ay][ax]
                if p is None:
                    ax += dx
                    ay += dy
                    continue
                if p.colour == by_colour and (p.name == "bishop" or p.name == "queen"):
                    return True
                break
        return False

    def in_check(self, colour: bool):
        king = self.whiteKing if colour else self.blackKing
        return self.is_square_attacked(king.pos[0], king.pos[1], not colour)

    def get_legal_moves_by_piece(self, piece: Piece):
        pseudo = self.get_pseudo_legal_moves_by_piece(piece)
        legal = []

        for mv in pseudo:
            self._apply_temp_move(mv)
            if not self.in_check(piece.colour):
                legal.append(mv)
            self._undo_temp_move(mv)

        return legal

    def _apply_temp_move(self, move: Move):
        x1, y1 = move.oldPos
        x2, y2 = move.newPos

        piece = self.boardList[y1][x1]
        captured = self.boardList[y2][x2]

        move._temp_captured = captured
        move._temp_old_pos = piece.pos

        self.boardList[y1][x1] = None
        self.boardList[y2][x2] = piece
        piece.pos = (x2, y2)

    def _undo_temp_move(self, move: Move):
        x1, y1 = move.oldPos
        x2, y2 = move.newPos

        piece = self.boardList[y2][x2]

        self.boardList[y2][x2] = move._temp_captured
        self.boardList[y1][x1] = piece
        piece.pos = move._temp_old_pos

        del move._temp_captured
        del move._temp_old_pos

    def game_end(self) -> int: #0 for game not ended, 1 for checkmate, 2 for stalemate
        colour = True if self.turn % 2 == 0 else False
        pieces = self.whitePieces if colour else self.blackPieces
        king = self.whiteKing if colour else self.blackKing

        for piece in pieces:
            if (len(self.get_legal_moves_by_piece(piece)) != 0):
                return 0

        if (self.is_square_attacked(king.pos[0], king.pos[1], not colour)):
            return 1

        return 2