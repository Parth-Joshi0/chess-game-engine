from Engine.pst import PIECE_SQUARE_TABLE
from piece import *
from collections import defaultdict

def num_to_chess_notation(pos):
    x, y = pos
    file_letter = chr(ord('a') + x)
    rank_number = 8 - y
    return f"{file_letter}{rank_number}"

class Move:
    def __init__(self, oldPos, newPos, piece, piece2=None, typeOfMove=0, promo_piece=None):
        self.oldPos = oldPos
        self.newPos = newPos
        self.piece = piece
        self.piece2 = piece2
        self.typeOfMove = typeOfMove #0 for regular moving move, 1 for castling, 2 for enPassant, 3 for Promotion, 4 for capture
        self.piece2OldPos = (-1,-1)
        self.piece2NewPos = (-1,-1)
        self.promo_piece = promo_piece

    def __eq__(self, other):
        if self.piece == other.piece and self.oldPos == other.oldPos and self.newPos == other.newPos:
            return True
        return False

    def __str__(self):
        return f"Piece: ({self.piece.colour} {self.piece.name}), From: {num_to_chess_notation(self.oldPos)}, To: {num_to_chess_notation(self.newPos)}"

class Board:
    def __init__(self):
        self.blackPieces = []
        self.whitePieces = []

        self.whiteKing = None
        self.blackKing = None

        self.turn = 0
        self.moveRuleTurns = 0

        self.boardList : list[list[Piece | None]] = [[None for _ in range(8)] for _ in range(8)]

        self.enPassantTarget = None

        self.promotionPiece = None
        self.promotionSquare = None

        self.generate_board()

        self.position_counts = defaultdict(int)
        self.position_counts[self.position_key()] = 1
        self.eval = 0

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
                m.promo_piece = Queen(m.piece.colour, m.newPos[0], m.newPos[1])

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

    def move(self, move: Move) -> str:
        # reset any prior promotion state
        self.promotionPiece = None

        # Validate move against legal moves for that piece
        legal_moves = self.get_legal_moves_by_piece(move.piece)

        matched = None
        for m in legal_moves:
            if m.oldPos == move.oldPos and m.newPos == move.newPos:
                matched = m
                break

        if matched is None:
            return "ILLEGAL_MOVE"

        move = matched

        # Promotion Moves - Special
        if move.typeOfMove == 3:
            x1, y1 = move.oldPos
            x2, y2 = move.newPos

            self.enPassantTarget = None

            self.promotionPiece = self.boardList[y1][x1]
            self.promotionSquare = (x2, y2)
            self.moveRuleTurns = 0
            return "PROMOTION"

        # All other moves
        self._apply_temp_move(move)

        return "VALID_MOVE"

    def is_square_attacked(self, x: int, y: int, by_colour: bool) -> bool:
        def in_bounds(cx, cy):
            return 0 <= cx <= 7 and 0 <= cy <= 7

        #Pawn attacks
        pawn_dir = 1 if by_colour else -1
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
                if mv.typeOfMove == 3:
                    knightPromo = Move(mv.oldPos, mv.newPos, piece, promo_piece=Knight(colour=piece.colour, xpos=mv.newPos[0], ypos=mv.newPos[1]), typeOfMove=3)
                    QueenPromo = Move(mv.oldPos, mv.newPos, piece, promo_piece=Queen(colour=piece.colour, xpos=mv.newPos[0], ypos=mv.newPos[1]), typeOfMove=3)
                    RookPromo = Move(mv.oldPos, mv.newPos, piece, promo_piece=Rook(colour=piece.colour, xpos=mv.newPos[0], ypos=mv.newPos[1]), typeOfMove=3)
                    BishopPromo = Move(mv.oldPos, mv.newPos, piece, promo_piece=Bishop(colour=piece.colour, xpos=mv.newPos[0], ypos=mv.newPos[1]), typeOfMove=3)
                    legal.append(knightPromo)
                    legal.append(QueenPromo)
                    legal.append(BishopPromo)
                    legal.append(RookPromo)
                else:
                    legal.append(mv)
            self._undo_temp_move(mv)

        return legal

    def _remove_piece_from_list(self, piece):
        if piece is None:
            return
        if piece.colour:
            if piece not in self.whitePieces:
                print("REMOVE FAIL:", piece.name, piece.pos, "white")
                print("whitePieces has:", [(p.name, p.pos) for p in self.whitePieces])
                raise ValueError("Piece not in whitePieces")
            self.whitePieces.remove(piece)
        else:
            if piece not in self.blackPieces:
                print("REMOVE FAIL:", piece.name, piece.pos, "black")
                raise ValueError("Piece not in blackPieces")
            self.blackPieces.remove(piece)

    def _add_piece_to_list(self, piece):
        if piece is None:
            return
        if piece.colour:
            self.whitePieces.append(piece)
        else:
            self.blackPieces.append(piece)

    def _apply_temp_move(self, move: Move):
        move._temp_eval_delta = 0
        move._temp_turn = self.turn
        self.turn += 1

        x1, y1 = move.oldPos
        x2, y2 = move.newPos

        piece = self.boardList[y1][x1]
        captured = self.boardList[y2][x2]

        move._temp_eval_delta -= self.pst_value(piece, x1, y1)

        # save global state
        move._temp_enPassantTarget = self.enPassantTarget
        move._temp_moveRuleTurns = self.moveRuleTurns
        move._temp_captured = captured
        move._temp_old_pos = piece.pos
        move._temp_hasMoved = getattr(piece, "hasMoved", None)

        # update 50-move rule
        is_pawn_move = (piece.name == "pawn")
        is_capture = (captured is not None) or (move.typeOfMove == 2)
        if is_pawn_move or is_capture:
            self.moveRuleTurns = 0
        else:
            self.moveRuleTurns += 1

        # en passant target
        self.enPassantTarget = None
        if piece.name == "pawn" and abs(y2 - y1) == 2:
            passed_y = (y1 + y2) // 2
            self.enPassantTarget = (x1, passed_y)

        # HANDLE PROMOTION FIRST (includes promotion-capture)
        if move.typeOfMove == 3:
            promo = move.promo_piece
            move._temp_pawn_obj = piece

            move._temp_eval_delta += self.pst_value(promo, x2, y2)
            move._temp_eval_delta -= self.pst_value(piece, x1, y1)
            move._temp_eval_delta -= piece.piece_worth()
            move._temp_eval_delta += promo.piece_worth()

            # Remove pawn from origin square
            self.boardList[y1][x1] = None

            # Remove captured piece if it exists
            if captured:
                move._temp_eval_delta -= captured.piece_worth()
                move._temp_eval_delta -= self.pst_value(captured, x2, y2)
                self._remove_piece_from_list(captured)

            # Remove pawn from piece list
            self._remove_piece_from_list(piece)

            # Place promoted piece on destination
            self.boardList[y2][x2] = promo
            promo.pos = (x2, y2)

            # Add promoted piece to list
            self._add_piece_to_list(promo)

            if hasattr(promo, "hasMoved"):
                promo.hasMoved = True

            self.position_counts[self.position_key()] += 1

            self.eval += move._temp_eval_delta
            return  #Exit early for promotions

        # NORMAL MOVES (non-promotion)
        self.boardList[y1][x1] = None
        move._temp_eval_delta += self.pst_value(piece, x2, y2)

        if captured:
            self._remove_piece_from_list(captured)
            move._temp_eval_delta -= self.pst_value(captured, x2, y2)
            move._temp_eval_delta -= captured.piece_worth()

        self.boardList[y2][x2] = piece
        piece.pos = (x2, y2)

        if hasattr(piece, "hasMoved"):
            piece.hasMoved = True

        # Special moves
        if move.typeOfMove == 1:  # Castling
            rx1, ry1 = move.piece2OldPos
            rx2, ry2 = move.piece2NewPos
            rook = self.boardList[ry1][rx1]

            move._temp_eval_delta += self.pst_value(rook, rx2, ry2)
            move._temp_eval_delta -= self.pst_value(rook, rx1, ry1)
            move._temp_rook_pos = rook.pos
            move._temp_rook_hasMoved = rook.hasMoved

            self.boardList[ry1][rx1] = None
            self.boardList[ry2][rx2] = rook
            rook.pos = (rx2, ry2)
            rook.hasMoved = True

        elif move.typeOfMove == 2:  # En passant
            px1, py1 = move.piece2OldPos
            ep_piece = self.boardList[py1][px1]

            move._temp_eval_delta -= self.pst_value(ep_piece, px1, py1)
            move._temp_eval_delta -= ep_piece.piece_worth()
            move._temp_en_passant_piece = ep_piece

            self.boardList[py1][px1] = None
            self._remove_piece_from_list(ep_piece)

        self.position_counts[self.position_key()] += 1
        self.eval += move._temp_eval_delta

    def _undo_temp_move(self, move: Move):
        x1, y1 = move.oldPos
        x2, y2 = move.newPos

        self.eval -= move._temp_eval_delta
        self.position_counts[self.position_key()] -= 1

        # restore turn
        self.turn = move._temp_turn
        del move._temp_turn

        # restore global state
        self.enPassantTarget = move._temp_enPassantTarget
        self.moveRuleTurns = move._temp_moveRuleTurns
        del move._temp_enPassantTarget
        del move._temp_moveRuleTurns

        # Promotion undo (must happen first)
        if move.typeOfMove == 3:
            promo_piece = self.boardList[y2][x2]  # Get promoted piece from board
            pawn = move._temp_pawn_obj

            # Remove promoted piece from list
            self._remove_piece_from_list(promo_piece)

            # Restore captured piece on destination (if any)
            self.boardList[y2][x2] = move._temp_captured
            if move._temp_captured:
                self._add_piece_to_list(move._temp_captured)

            # Restore pawn to origin
            self.boardList[y1][x1] = pawn
            pawn.pos = move._temp_old_pos

            #ADD PAWN BACK TO PIECE LIST
            self._add_piece_to_list(pawn)

            if move._temp_hasMoved is not None:
                pawn.hasMoved = move._temp_hasMoved

            # Cleanup
            del move._temp_pawn_obj
            del move._temp_captured
            del move._temp_old_pos
            del move._temp_hasMoved
            return

        # Normal undo (non-promotion)
        piece = self.boardList[y2][x2]

        self.boardList[y2][x2] = move._temp_captured
        self.boardList[y1][x1] = piece
        piece.pos = move._temp_old_pos

        # Restore captured piece back into lists (normal capture)
        if move._temp_captured:
            self._add_piece_to_list(move._temp_captured)

        # Restore hasMoved
        if move._temp_hasMoved is not None:
            piece.hasMoved = move._temp_hasMoved

        # Undo special moves
        if move.typeOfMove == 1:  # Castling
            rx1, ry1 = move.piece2OldPos
            rx2, ry2 = move.piece2NewPos
            rook = self.boardList[ry2][rx2]

            self.boardList[ry2][rx2] = None
            self.boardList[ry1][rx1] = rook
            rook.pos = move._temp_rook_pos
            rook.hasMoved = move._temp_rook_hasMoved

            del move._temp_rook_pos
            del move._temp_rook_hasMoved

        elif move.typeOfMove == 2:  # En passant
            px1, py1 = move.piece2OldPos
            ep_piece = move._temp_en_passant_piece

            self.boardList[py1][px1] = ep_piece
            self._add_piece_to_list(ep_piece)

            del move._temp_en_passant_piece

        # Cleanup
        del move._temp_captured
        del move._temp_old_pos
        del move._temp_hasMoved

    def game_end(self, moves=None) -> int: #0 for game not ended, 1 for checkmate, 2 for stalemate, 3 for 50 move rule draw, 4 for 3fold repetion
        colour = True if self.turn % 2 == 0 else False
        pieces = self.whitePieces if colour else self.blackPieces
        king = self.whiteKing if colour else self.blackKing

        if self.position_counts[self.position_key()] >= 3:
            return 4

        if self.moveRuleTurns >= 50:
            return 3

        if moves is None:
            for piece in pieces:
                if len(self.get_legal_moves_by_piece(piece)) != 0:
                    return 0
        else:
            if len(moves) != 0:
                return 0

        if self.is_square_attacked(king.pos[0], king.pos[1], not colour):
            return 1

        return 2

    def finalize_promotion(self, choice):
        pawn = self.promotionPiece
        if pawn is None:
            return

        colour = pawn.colour
        x1, y1 = pawn.pos
        x2, y2 = self.promotionSquare

        match choice:
            case "Q":
                promo = Queen(colour, x2, y2)
            case "N":
                promo = Knight(colour, x2, y2)
            case "B":
                promo = Bishop(colour, x2, y2)
            case "R":
                promo = Rook(colour, x2, y2)
            case _:
                return

        captured = self.boardList[y2][x2]

        promo_delta = 0
        promo_delta -= pawn.piece_worth()
        promo_delta += promo.piece_worth()
        promo_delta -= self.pst_value(pawn, x1, y1)
        promo_delta += self.pst_value(promo, x2, y2)
        if captured is not None:
            promo_delta -= captured.piece_worth()
            promo_delta -= self.pst_value(captured, x2, y2)

        self.boardList[y1][x1] = None
        self.boardList[y2][x2] = promo

        self._remove_piece_from_list(pawn)
        if captured is not None:
            self._remove_piece_from_list(captured)
        self._add_piece_to_list(promo)

        self.eval += promo_delta
        self.turn += 1
        self.position_counts[self.position_key()] += 1

        self.promotionPiece = None
        self.promotionSquare = None

    def position_key(self) -> bytes:
        #Stores the position in a bit key, the first bit is the side to move,
        #The next 4 bits are the castling rights, (white king, white queen, black king, black queen)
        #The next 8 bits are the target square for en-passant (x, y) - all 1's if it is none
        #The next 256 bits are the pieces, each mapped to a seperate code, where the first bit is the colour

        MAPPING = {
            "king": "110",
            "knight": "101",
            "queen": "100",
            "bishop": "011",
            "rook": "010",
            "pawn": "001",
        }

        bits = []
        append = bits.append

        append("1" if self.turn % 2 == 0 else "0")

        rooks = [self.boardList[7][0], self.boardList[7][7], self.boardList[0][0], self.boardList[0][7]]
        for rook in rooks:
            if rook and rook.name == "rook":
                king = self.whiteKing if rook.colour else self.blackKing
                if (not rook.hasMoved) and (not king.hasMoved):
                    append("1")
                else:
                    append("0")
            else:
                append("0")

        if self.enPassantTarget:
            x, y = self.enPassantTarget
            append(format(x, "04b"))
            append(format(y, "04b"))
        else:
            append("11111111")

        for y in range(8):
            for x in range(8):
                p = self.boardList[y][x]
                if p is None:
                    append("0000")
                else:
                    append(("1" if p.colour else "0") + MAPPING[p.name])

        bitstr = "".join(bits)

        pad = (-len(bitstr)) % 8
        if pad:
            bitstr += "0" * pad

        return int(bitstr, 2).to_bytes(len(bitstr) // 8, byteorder="big")

    def generate_legal_moves(self, colour: bool):
        pieceList = self.whitePieces if colour else self.blackPieces
        moves = []
        for piece in pieceList:
            moves += self.get_legal_moves_by_piece(piece)
        return moves

    def get_pseudo_legal_moves(self, colour: bool):
        pieceList = self.whitePieces if colour else self.blackPieces
        moves = []
        for piece in pieceList:
            moves += self.get_pseudo_legal_moves_by_piece(piece)
        return moves

    def mirrored_y(self, colour: bool, y: int) -> int:
        return y if colour else 7 - y

    def clamp(self, v, lo, hi):
        return max(lo, min(hi, v))

    def pst_value(self, piece, x: int, y: int) -> int:
        table = PIECE_SQUARE_TABLE.get(piece.name)
        if table is None:
            return 0

        my = self.mirrored_y(piece.colour, y)

        if piece.name != "king":
            pct = table[my][x]
            pct = self.clamp(pct, -0.6, 0.6)
            return int(round(piece.piece_worth() * pct))

        # king PST ONLY (no castling bonus/penalty)
        king_pst = table[my][x]
        val = int(round(100 * king_pst))
        return val if piece.colour else -val