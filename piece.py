WHITE = True
BLACK = False

class Piece:
    def __init__(self, colour: bool, xpos: int, ypos: int):
        self.colour = colour
        self.pos = (xpos, ypos)
        self.name = ""

    def move(self, x, y):
        self.pos = (x,y)

    def moves_available(self) -> list[(int, int)]:
        return []

    def piece_worth(self) -> int:
        return 0

class King(Piece):
    def __init__(self, colour: bool, xpos: int, ypos: int):
        self.hasMoved = False # Tracker for castling rights
        super().__init__(colour, xpos, ypos)
        self.name = "king"

    def moves_available(self) -> list[(int, int)]:
        moves = []

        # King moves only one square in each direction
        for i in range(self.pos[0] - 1, self.pos[0] + 2):
            for j in range(self.pos[1] - 1, self.pos[1] + 2):
                if 0 <= i <= 7 and 0 <= j <= 7:
                    if (i, j) != (self.pos[0], self.pos[1]):
                        moves.append((i, j))

        return moves

    def move(self, x, y):
        self.hasMoved = True
        super().move(x, y)

class Rook(Piece):
    def __init__(self, colour: bool, xpos: int, ypos: int):
        self.hasMoved = False
        super().__init__(colour, xpos, ypos)
        self.name = "rook"

    def move(self, x, y):
        self.hasMoved = True
        super().move(x, y)

    def piece_worth(self) -> int:
        return 500 if self.colour == WHITE else -500

class Knight(Piece):
    def __init__(self, colour: bool, xpos: int, ypos: int):
        super().__init__(colour, xpos, ypos)
        self.name = "knight"

    def moves_available(self) -> list[(int, int)]:
        x = self.pos[0]
        y = self.pos[1]

        # King moves in L shape 2 in one direction 1 perpendicular to it
        candidates = [
            (x + 2, y + 1), (x + 2, y - 1),
            (x - 2, y + 1), (x - 2, y - 1),
            (x + 1, y + 2), (x + 1, y - 2),
            (x - 1, y + 2), (x - 1, y - 2),
        ]

        moves = []
        for (r, c) in candidates:
            if 0 <= r <= 7 and 0 <= c <= 7:
                moves.append((r, c))

        return moves

    def piece_worth(self) -> int:
        return 325 if self.colour == WHITE else -325

class Bishop(Piece):
    def __init__(self, colour: bool, xpos: int, ypos: int):
        super().__init__(colour, xpos, ypos)
        self.name = "bishop"

    def piece_worth(self) -> int:
        return 330 if self.colour == WHITE else -330

class Queen(Piece):
    def __init__(self, colour: bool, xpos: int, ypos: int):
        super().__init__(colour, xpos, ypos)
        self.name = "queen"

    def piece_worth(self) -> int:
        return 900 if self.colour == WHITE else -900

class Pawn(Piece):
    def __init__(self, colour: bool, xpos: int, ypos: int):
        super().__init__(colour, xpos, ypos)
        self.name = "pawn"

    def piece_worth(self) -> int:
        return 100 if self.colour == WHITE else -100