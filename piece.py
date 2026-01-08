class Piece:
    def __init__(self, colour: bool, xpos: int, ypos: int):
        self.colour = colour
        self.pos = (xpos, ypos)
        self.name = ""

    def move(self, x, y):
        self.pos = (x,y)

    def moves_available(self) -> list[(int, int)]:
        return []

class King(Piece):
    def __init__(self, colour: bool, xpos: int, ypos: int):
        self.hasMoved = False
        super().__init__(colour, xpos, ypos)
        self.name = "king"

    def moves_available(self) -> list[(int, int)]:
        moves = []

        for i in range(self.pos[0] - 1, self.pos[0] + 2):
            for j in range(self.pos[1] - 1, self.pos[1] + 2):
                if 0 <= i <= 7 and 0 <= j <= 7:
                    if i != self.pos[0] and j != self.pos[1]:
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

    def moves_available(self) -> list[(int, int)]:
        moves = []
        x = self.pos[0]
        y = self.pos[1]
        for i in range(0, 8):
            if i != y:
                moves.append((x, i))
            if i != x:
                moves.append((i, y))
        return list(dict.fromkeys(moves))

    def move(self, x, y):
        self.hasMoved = True
        super().move(x, y)

class Knight(Piece):
    def __init__(self, colour: bool, xpos: int, ypos: int):
        super().__init__(colour, xpos, ypos)
        self.name = "knight"

    def moves_available(self) -> list[(int, int)]:
        x = self.pos[0]
        y = self.pos[1]
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

class Bishop(Piece):
    def __init__(self, colour: bool, xpos: int, ypos: int):
        super().__init__(colour, xpos, ypos)
        self.name = "bishop"

    def moves_available(self) -> list[(int, int)]:
        x = self.pos[0]
        y = self.pos[1]
        moves = []

        for i in range(1, 8):
            if (x+i) <= 7 and (y+i) <= 7:
                moves.append((x+i, y+i))
            if (x+i) <= 7 and (y-i) >= 0:
                moves.append((x+i, y-i))
            if (x-i) >= 0 and (y+i) <= 7:
                moves.append((x-i, y+i))
            if (x-i) >= 0 and (y-i) >= 0:
                moves.append((x-i, y-i))

        return moves

class Queen(Piece):
    def __init__(self, colour: bool, xpos: int, ypos: int):
        super().__init__(colour, xpos, ypos)
        self.name = "queen"

    def moves_available(self) -> list[(int, int)]:
        moves = []
        x = self.pos[0]
        y = self.pos[1]
        for i in range(0, 8):
            if i != y:
                moves.append((x, i))
            if i != x:
                moves.append((i, y))

            if i == 0:
                continue

            if (x+i) <= 7 and (y+i) <= 7:
                moves.append((x+i, y+i))
            if (x+i) <= 7 and (y-i) >= 0:
                moves.append((x+i, y-i))
            if (x-i) >= 0 and (y+i) <= 7:
                moves.append((x-i, y+i))
            if (x-i) >= 0 and (y-i) >= 0:
                moves.append((x-i, y-i))
        return list(dict.fromkeys(moves))

class Pawn(Piece):
    def __init__(self, colour: bool, xpos: int, ypos: int):
        super().__init__(colour, xpos, ypos)
        self.name = "pawn"

    def moves_available(self) -> list[(int, int)]:
        direction = 1
        if self.colour:
            direction = -1

        x = self.pos[0]
        y = self.pos[1]
        moves = [(x, y+direction)]

        if ((not self.colour) and y == 1) or (self.colour and y == 6):
            moves.append((x, y+2*direction))

        return moves