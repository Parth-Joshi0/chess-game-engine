from Engine.pst import ENDGAME_PIECE_SQUARE_TABLE, MIDDLEGAME_PIECE_SQUARE_TABLE
from piece import *
from collections import defaultdict
import sys
import zobrist

STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

# The 50-move rule draws after 50 full moves, i.e. 100 plies. moveRuleTurns counts plies.
HALFMOVE_DRAW_PLIES = 100

# FEN letter -> piece class, and the reverse for serialisation
FEN_PIECES = {"k": King, "q": Queen, "r": Rook, "b": Bishop, "n": Knight, "p": Pawn}
FEN_LETTER = {"king": "k", "queen": "q", "rook": "r",
              "bishop": "b", "knight": "n", "pawn": "p"}

# Castling flag -> (king_x, king_y, rook_x, rook_y)
CASTLE_SQUARES = {
    "K": (4, 7, 7, 7), "Q": (4, 7, 0, 7),
    "k": (4, 0, 7, 0), "q": (4, 0, 0, 0),
}

def num_to_chess_notation(pos):
    # Convert Internal Coordinates to Algebraic Notation (0, 0) -> a8
    x, y = pos
    file_letter = chr(ord('a') + x)
    rank_number = 8 - y
    return f"{file_letter}{rank_number}"

class Move:
    def __init__(self, oldPos, newPos, piece, piece2=None, typeOfMove=0, promo_piece=None):
        self.oldPos = oldPos
        self.newPos = newPos
        self.piece = piece
        self.piece2 = piece2 # Captured Piece or Rook for Castling
        self.typeOfMove = typeOfMove # 0=regular , 1=castling, 2=enPassant, 3=Promotion, 4=capture
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
    def __init__(self, fen: str | None = None):
        self.blackPieces = []
        self.whitePieces = []

        self.whiteKing = None
        self.blackKing = None

        self.turn = 0
        self.moveRuleTurns = 0 # 50 move rule counter

        self.boardList : list[list[Piece | None]] = [[None for _ in range(8)] for _ in range(8)]

        self.enPassantTarget = None

        self.promotionPiece = None
        self.promotionSquare = None

        # Both paths must end with _recompute_derived(), which seeds eval / mg / eg /
        # position_counts from whatever pieces are now on the board.
        if fen is None:
            self.generate_board()
            self._recompute_derived()
        else:
            self.load_fen(fen)

    @classmethod
    def from_fen(cls, fen: str) -> "Board":
        return cls(fen)

    def _recompute_derived(self) -> None:
        # Recompute every cached value that depends on the piece placement.
        # phase_weights() must run first: pst_value() reads self.mg / self.eg.
        self.mg, self.eg = self.phase_weights()
        self.eval = sum(p.piece_worth() + self.pst_value(p, *p.pos)
                        for p in self.whitePieces + self.blackPieces)

        # Zobrist hash of just the piece placement, maintained incrementally by every
        # move/unmove from here on. Side to move, castling rights and en-passant are cheap
        # to derive on demand, so position_key() layers them on rather than tracking them
        # here too.
        self.zobrist_pieces = 0
        for p in self.whitePieces + self.blackPieces:
            self.zobrist_pieces ^= zobrist.piece_key(p, *p.pos)

        self.position_counts = defaultdict(int)
        self.position_counts[self.position_key()] = 1

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

    # ---------- FEN ----------
    def load_fen(self, fen: str) -> None:
        # Replace the entire board state with the position described by a FEN string.
        fields = fen.split()
        if len(fields) < 2:
            raise ValueError(f"FEN needs at least a placement and a side to move: {fen!r}")

        placement = fields[0]
        stm = fields[1]
        castling = fields[2] if len(fields) > 2 else "-"
        ep = fields[3] if len(fields) > 3 else "-"
        halfmove = int(fields[4]) if len(fields) > 4 and fields[4].isdigit() else 0
        fullmove = int(fields[5]) if len(fields) > 5 and fields[5].isdigit() else 1

        if stm not in ("w", "b"):
            raise ValueError(f"FEN side to move must be 'w' or 'b': {stm!r}")

        ranks = placement.split("/")
        if len(ranks) != 8:
            raise ValueError(f"FEN placement needs 8 ranks, got {len(ranks)}: {placement!r}")

        self.boardList = [[None for _ in range(8)] for _ in range(8)]
        self.whitePieces = []
        self.blackPieces = []
        self.whiteKing = None
        self.blackKing = None
        self.promotionPiece = None
        self.promotionSquare = None

        # Rank 8 is listed first and is row 0, which matches boardList's ordering directly.
        for y, rank in enumerate(ranks):
            x = 0
            for ch in rank:
                if ch.isdigit():
                    x += int(ch)
                    continue
                cls_ = FEN_PIECES.get(ch.lower())
                if cls_ is None:
                    raise ValueError(f"Unknown piece letter {ch!r} in FEN rank {rank!r}")
                if x > 7:
                    raise ValueError(f"FEN rank overflows 8 files: {rank!r}")

                colour = ch.isupper()
                p = cls_(colour, x, y)

                # Castling rights are stored as hasMoved on the king/rook objects, so start
                # from "no rights" and grant back only what the castling field allows.
                if p.name in ("king", "rook"):
                    p.hasMoved = True

                self.boardList[y][x] = p
                if colour:
                    self.whitePieces.append(p)
                    if p.name == "king":
                        self.whiteKing = p
                else:
                    self.blackPieces.append(p)
                    if p.name == "king":
                        self.blackKing = p
                x += 1

            if x != 8:
                raise ValueError(f"FEN rank does not describe 8 squares: {rank!r}")

        # in_check() dereferences these unconditionally, so a kingless FEN would crash
        # somewhere deep in the search rather than here.
        if self.whiteKing is None or self.blackKing is None:
            raise ValueError(f"FEN is missing a king: {fen!r}")

        if castling != "-":
            for flag, (kx, ky, rx, ry) in CASTLE_SQUARES.items():
                if flag not in castling:
                    continue
                king = self.boardList[ky][kx]
                rook = self.boardList[ry][rx]
                want_white = flag.isupper()
                # A right that doesn't match the pieces actually present is dropped rather
                # than trusted; castling_moves() would otherwise move whatever is there.
                if king is None or king.name != "king" or king.colour is not want_white:
                    continue
                if rook is None or rook.name != "rook" or rook.colour is not want_white:
                    continue
                king.hasMoved = False
                rook.hasMoved = False

        self.enPassantTarget = None
        if ep != "-" and len(ep) >= 2:
            self.enPassantTarget = (ord(ep[0]) - ord('a'), 8 - int(ep[1]))

        self.moveRuleTurns = halfmove
        self.turn = (max(1, fullmove) - 1) * 2 + (0 if stm == "w" else 1)

        self._recompute_derived()

    def _castling_rights(self) -> tuple[bool, bool, bool, bool]:
        # (white kingside, white queenside, black kingside, black queenside).
        # A right survives only if both the king and that specific rook are unmoved.
        rights = []
        for flag in ("K", "Q", "k", "q"):
            kx, ky, rx, ry = CASTLE_SQUARES[flag]
            king = self.boardList[ky][kx]
            rook = self.boardList[ry][rx]
            want_white = flag.isupper()
            ok = (king is not None and king.name == "king" and king.colour is want_white
                  and not king.hasMoved
                  and rook is not None and rook.name == "rook" and rook.colour is want_white
                  and not rook.hasMoved)
            rights.append(ok)
        return tuple(rights)

    def to_fen(self) -> str:
        # Serialise the current position back to a FEN string.
        ranks = []
        for y in range(8):
            rank = ""
            empty = 0
            for x in range(8):
                p = self.boardList[y][x]
                if p is None:
                    empty += 1
                    continue
                if empty:
                    rank += str(empty)
                    empty = 0
                letter = FEN_LETTER[p.name]
                rank += letter.upper() if p.colour else letter
            if empty:
                rank += str(empty)
            ranks.append(rank)

        placement = "/".join(ranks)
        stm = "w" if self.turn % 2 == 0 else "b"
        castling = "".join(c for c, ok in zip("KQkq", self._castling_rights()) if ok) or "-"
        ep = num_to_chess_notation(self.enPassantTarget) if self.enPassantTarget else "-"

        return f"{placement} {stm} {castling} {ep} {self.moveRuleTurns} {self.turn // 2 + 1}"

    # ---------- Move Generation ----------
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

        # 1 square forward
        y1 = y + direction
        if 0 <= y1 <= 7 and self.boardList[y1][x] is None:
            moves.append(Move((x, y), (x, y1), piece))

            # 2 squares forward
            y2 = y + 2 * direction
            if y == start_row and self.boardList[y2][x] is None:
                moves.append(Move((x, y), (x, y2), piece))

        # captures
        for dx in (-1, 1):
            x2 = x + dx
            y2 = y + direction
            if 0 <= x2 <= 7 and 0 <= y2 <= 7:
                target = self.boardList[y2][x2]
                if target is not None and target.colour != piece.colour:
                    moves.append(Move((x, y), (x2, y2), piece, piece2=target, typeOfMove=4))

        extraPromos = []
        # promotion flag
        for m in moves:
            if m.newPos[1] == promotion_row:
                m.typeOfMove = 3  # promotion
                m.promo_piece = Queen(m.piece.colour, m.newPos[0], m.newPos[1])
                rookPromo = Move(m.oldPos, m.newPos, piece,
                                 promo_piece=Rook(colour=piece.colour, xpos=m.newPos[0], ypos=m.newPos[1]),
                                 typeOfMove=3)
                bishopPromo = Move(m.oldPos, m.newPos, piece,
                                 promo_piece=Bishop(colour=piece.colour, xpos=m.newPos[0], ypos=m.newPos[1]),
                                 typeOfMove=3)
                knightPromo = Move(m.oldPos, m.newPos, piece,
                                   promo_piece=Knight(colour=piece.colour, xpos=m.newPos[0], ypos=m.newPos[1]),
                                   typeOfMove=3)
                extraPromos.extend([rookPromo, bishopPromo, knightPromo])

        moves.extend(extraPromos)

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
        # Generate sliding piece moves in given directions until blocked
        # For Queens, Rooks, Bishops
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
        # Convert piece's available squares to Move objects, checking for captures
        # For Kings and Knights
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
        king = piece
        row = 7 if piece.colour else 0
        if king.hasMoved:
            return []

        rook1 = self.boardList[row][0] # Queen side Rook
        rook2 = self.boardList[row][7] # King side Rook

        moves = []

        # Queen Side Castling
        if rook1 and rook1.name == "rook" and not rook1.hasMoved:
            empty = self.boardList[row][1] is None and self.boardList[row][2] is None and self.boardList[row][3] is None
            attacked = self.is_square_attacked(4, row, not piece.colour) or self.is_square_attacked(2, row, not piece.colour) or self.is_square_attacked(3, row, not piece.colour)
            if empty and not attacked:
                move = Move(king.pos, (2, row), king, rook1, 1)
                move.piece2NewPos = (3, row)
                move.piece2OldPos = rook1.pos
                moves.append(move)

        # King Side Castling
        if rook2 and rook2.name == "rook" and not rook2.hasMoved:
            empty = self.boardList[row][5] is None and self.boardList[row][6] is None
            attacked = self.is_square_attacked(5, row, not piece.colour) or self.is_square_attacked(6, row, not piece.colour) or self.is_square_attacked(4, row, not piece.colour)
            if empty and not attacked:
                move = Move(king.pos, (6, row), king, rook2, 1)
                move.piece2NewPos = (5, row)
                move.piece2OldPos = rook2.pos
                moves.append(move)

        return moves

    def get_legal_moves_by_piece(self, piece: Piece):
        pseudo = self.get_pseudo_legal_moves_by_piece(piece)
        legal = []

        for mv in pseudo:
            self._apply_temp_move(mv)
            if not self.in_check(piece.colour):
                legal.append(mv)
            self._undo_temp_move(mv)

        return legal

    def generate_legal_moves(self, colour: bool):
        pieceList = self.whitePieces if colour else self.blackPieces
        moves = []
        # Snapshot the list: get_legal_moves_by_piece applies and undoes each move, and a
        # promotion's undo re-appends the pawn at the end. Iterating the live list would
        # shift later pieces left and skip one while visiting the pawn twice.
        for piece in list(pieceList):
            moves += self.get_legal_moves_by_piece(piece)
        return moves

    def get_pseudo_legal_moves(self, colour: bool):
        pieceList = self.whitePieces if colour else self.blackPieces
        moves = []
        # No snapshot needed here (and this is the hot search path): pseudo-legal generation
        # never applies a move, so the piece list cannot be reordered underneath us.
        for piece in pieceList:
            moves += self.get_pseudo_legal_moves_by_piece(piece)
        return moves

    # ---------- Move Execution ----------
    def move(self, move: Move) -> str:
        # Reset any prior promotion state
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

    def finalize_promotion(self, choice):
        # Complete a promotion after UI selection
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

        # Update Evaluation
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

        self.zobrist_pieces ^= zobrist.piece_key(pawn, x1, y1)
        if captured is not None:
            self.zobrist_pieces ^= zobrist.piece_key(captured, x2, y2)
        self.zobrist_pieces ^= zobrist.piece_key(promo, x2, y2)

        self.eval += promo_delta
        self.turn += 1
        self.position_counts[self.position_key()] += 1

        self.promotionPiece = None
        self.promotionSquare = None

    def _apply_temp_move(self, move: Move):
        move._temp_eval_delta = 0
        move._temp_turn = self.turn
        self.turn += 1

        move._mg = self.mg
        move._eg = self.eg

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

            move._temp_zobrist_delta = zobrist.piece_key(piece, x1, y1) ^ zobrist.piece_key(promo, x2, y2)
            if captured:
                move._temp_zobrist_delta ^= zobrist.piece_key(captured, x2, y2)
            self.zobrist_pieces ^= move._temp_zobrist_delta

            self.position_counts[self.position_key()] += 1

            self.eval += move._temp_eval_delta
            self.mg, self.eg = self.phase_weights()
            return  # Exit early for promotions

        # NORMAL MOVES (non-promotion)
        self.boardList[y1][x1] = None
        move._temp_eval_delta += self.pst_value(piece, x2, y2)

        move._temp_zobrist_delta = zobrist.piece_key(piece, x1, y1) ^ zobrist.piece_key(piece, x2, y2)

        if captured:
            self._remove_piece_from_list(captured)
            move._temp_eval_delta -= self.pst_value(captured, x2, y2)
            move._temp_eval_delta -= captured.piece_worth()
            move._temp_zobrist_delta ^= zobrist.piece_key(captured, x2, y2)
            self.mg, self.eg = self.phase_weights()

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

            move._temp_zobrist_delta ^= zobrist.piece_key(rook, rx1, ry1) ^ zobrist.piece_key(rook, rx2, ry2)

        elif move.typeOfMove == 2:  # En passant
            px1, py1 = move.piece2OldPos
            ep_piece = self.boardList[py1][px1]

            move._temp_eval_delta -= self.pst_value(ep_piece, px1, py1)
            move._temp_eval_delta -= ep_piece.piece_worth()
            move._temp_en_passant_piece = ep_piece

            self.boardList[py1][px1] = None
            self._remove_piece_from_list(ep_piece)

            move._temp_zobrist_delta ^= zobrist.piece_key(ep_piece, px1, py1)

        self.zobrist_pieces ^= move._temp_zobrist_delta

        self.position_counts[self.position_key()] += 1
        self.eval += move._temp_eval_delta

    def _undo_temp_move(self, move: Move):
        x1, y1 = move.oldPos
        x2, y2 = move.newPos
        self.mg = move._mg
        self.eg = move._eg

        self.eval -= move._temp_eval_delta

        # Drop keys that fall back to zero. defaultdict(int) still reads them as 0, but
        # leaving them in place grows the dict by one entry per search node (~9.5k for a
        # single depth-4 search) and it lives on the Board, so no TT clear would reclaim it.
        # Must run before the zobrist/board-state restoration below: position_key() needs
        # to see the post-move state here, matching what _apply_temp_move incremented.
        k = self.position_key()
        c = self.position_counts[k] - 1
        if c:
            self.position_counts[k] = c
        else:
            self.position_counts.pop(k, None)

        # XOR is its own inverse, so re-applying the exact delta _apply_temp_move computed
        # restores the pre-move piece hash regardless of how many pieces moved.
        self.zobrist_pieces ^= move._temp_zobrist_delta
        del move._temp_zobrist_delta

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

            # ADD PAWN BACK TO PIECE LIST
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

    # ---------- Attack Detection ----------
    def is_square_attacked(self, x: int, y: int, by_colour: bool) -> bool:
        # Check if a square is attacked by a given colour
        def in_bounds(cx, cy):
            return 0 <= cx <= 7 and 0 <= cy <= 7

        # Pawn attacks
        pawn_dir = 1 if by_colour else -1
        for dx in (-1, 1):
            ax, ay = x + dx, y + pawn_dir
            if in_bounds(ax, ay):
                p = self.boardList[ay][ax]
                if p is not None and p.colour == by_colour and p.name == "pawn":
                    return True

        # Knight attacks
        knight_offsets = [(2, 1), (2, -1), (-2, 1), (-2, -1), (1, 2), (1, -2), (-1, 2), (-1, -2)]
        for dx, dy in knight_offsets:
            ax, ay = x + dx, y + dy
            if in_bounds(ax, ay):
                p = self.boardList[ay][ax]
                if p is not None and p.colour == by_colour and p.name == "knight":
                    return True

        # King Attacks: No castling checks
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                ax, ay = x + dx, y + dy
                if in_bounds(ax, ay):
                    p = self.boardList[ay][ax]
                    if p is not None and p.colour == by_colour and p.name == "king":
                        return True

        # Rook & Queen Attacks
        rook_dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        for dx, dy in rook_dirs:
            ax, ay = x + dx, y + dy
            while in_bounds(ax, ay):
                p = self.boardList[ay][ax]
                if p is None:
                    ax += dx
                    ay += dy
                    continue
                # First piece on this ray blocks further
                if p.colour == by_colour and (p.name == "rook" or p.name == "queen"):
                    return True
                break

        # Bishop & Queen Attacks
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

    # ---------- Piece List Management ----------
    def _remove_piece_from_list(self, piece):
        if piece is None:
            return
        # These diagnostics go to stderr: stdout is the UCI channel and any stray line
        # there would corrupt the protocol.
        if piece.colour:
            if piece not in self.whitePieces:
                print("REMOVE FAIL:", piece.name, piece.pos, "white", file=sys.stderr)
                print("whitePieces has:", [(p.name, p.pos) for p in self.whitePieces], file=sys.stderr)
                raise ValueError("Piece not in whitePieces")
            self.whitePieces.remove(piece)
        else:
            if piece not in self.blackPieces:
                print("REMOVE FAIL:", piece.name, piece.pos, "black", file=sys.stderr)
                raise ValueError("Piece not in blackPieces")
            self.blackPieces.remove(piece)

    def _add_piece_to_list(self, piece):
        if piece is None:
            return
        if piece.colour:
            self.whitePieces.append(piece)
        else:
            self.blackPieces.append(piece)

    # ---------- Game State ----------
    def game_end(self, moves=None) -> int:
        # 0=Ongoing, 1=checkmate, 2=stalemate, 3=50 move rule draw, 4=3fold repetition
        colour = True if self.turn % 2 == 0 else False
        pieces = self.whitePieces if colour else self.blackPieces
        king = self.whiteKing if colour else self.blackKing

        if self.position_counts[self.position_key()] >= 3:
            return 4

        if self.moveRuleTurns >= HALFMOVE_DRAW_PLIES:
            return 3

        if moves is None:
            # Snapshot for the same reason as generate_legal_moves()
            for piece in list(pieces):
                if len(self.get_legal_moves_by_piece(piece)) != 0:
                    return 0
        else:
            if len(moves) != 0:
                return 0

        if self.is_square_attacked(king.pos[0], king.pos[1], not colour):
            return 1

        return 2

    # ---------- Position Hashing ----------
    def position_key(self) -> int:
        # Zobrist hash: self.zobrist_pieces is the XOR of every piece's key and is kept
        # up to date incrementally by every move/unmove (see _apply_temp_move /
        # _undo_temp_move / finalize_promotion). Side to move, castling rights and
        # en-passant are cheap (O(1)-O(4)) so they're layered on fresh each call instead
        # of being tracked incrementally too -- that avoids having to reconstruct
        # "what the en-passant/castling state was before this move" at the couple of call
        # sites (finalize_promotion in particular) where it's already been overwritten by
        # the time the hash would need updating.
        key = self.zobrist_pieces
        if self.turn % 2 == 1:
            key ^= zobrist.SIDE_KEY
        # Shared with to_fen() so the hash and the FEN can never disagree about rights
        key ^= zobrist.castling_component(self._castling_rights())
        key ^= zobrist.en_passant_component(self.enPassantTarget)
        return key

    # ---------- Evaluation Helpers ----------
    def pst_value(self, piece, x: int, y: int) -> int:
        # Get Piece-Square Table bonus for a given piece at a given position
        endgame_table = ENDGAME_PIECE_SQUARE_TABLE.get(piece.name)
        middlegame_table = MIDDLEGAME_PIECE_SQUARE_TABLE.get(piece.name)
        ty = (7 - y) if piece.colour == WHITE else y
        bonus = endgame_table[ty][x] * self.eg + middlegame_table[ty][x] * self.mg

        # convert to White POV: black's bonus counts negatively
        return bonus if piece.colour == WHITE else -bonus

    def phase_weights(self) -> tuple[float, float]:
        # Calculate middlegame/endgame phase weights based on material
        mg = 0.0

        for p in self.whitePieces:
            if p.name == "queen":
                mg += 0.1666667
            elif p.name == "rook":
                mg += 0.0833333
            elif p.name == "bishop" or p.name == "knight":
                mg += 0.0416667

        for p in self.blackPieces:
            if p.name == "queen":
                mg += 0.1666667
            elif p.name == "rook":
                mg += 0.0833333
            elif p.name == "bishop" or p.name == "knight":
                mg += 0.0416667

        # mg ∈ [0, 1]
        if mg > 1.0:
            mg = 1.0
        return mg, 1 - mg