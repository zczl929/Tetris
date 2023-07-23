from enum import Enum
from threading import Lock
from exceptions import NoBlockException
from types import GeneratorType

class Action(Enum):
    Bomb = 'BOMB'
    Discard = 'DISCARD'

class Direction(Enum):
    """
    Possible directions to move a block, plus dropping.
    """

    Left = 'LEFT'
    Right = 'RIGHT'
    Down = 'DOWN'
    Drop = 'DROP'


class Rotation(Enum):
    """
    Possible rotations available to the player.
    """

    Clockwise = 'CLOCKWISE'
    Anticlockwise = 'ANTICLOCKWISE'


class Shape(Enum):
    """
    Possible shapes of tetrominoes.
    """

    I = 'I'  # noqa
    J = 'J'
    L = 'L'
    O = 'O'  # noqa
    S = 'S'
    T = 'T'
    Z = 'Z'
    B = 'B'


# Translate names of shapes to initial coordinates.
shape_to_cells = {
    Shape.I: {
        (0, 0),
        (0, 1),
        (0, 2),
        (0, 3),
    },
    Shape.J: {
                (1, 0),
                (1, 1),
        (0, 2), (1, 2), # noqa
    },
    Shape.L: {
        (0, 0),
        (0, 1),
        (0, 2), (1, 2),
    },
    Shape.O: {
        (0, 0), (1, 0),
        (0, 1), (1, 1),
    },
    Shape.S: {
                (1, 0), (2, 0),
        (0, 1), (1, 1),
    },
    Shape.T: {
        (0, 0), (1, 0), (2, 0),
                (1, 1),
    },
    Shape.Z: {
        (0, 0), (1, 0),
                (1, 1), (2, 1),
    },
    Shape.B: { (0,0)}
}

shape_to_color = {
    Shape.I: "cyan",
    Shape.J: "blue",
    Shape.L: "orange",
    Shape.O: "yellow",
    Shape.S: "green",
    Shape.T: "magenta",
    Shape.Z: "red",
    Shape.B: "white",
}


shape_to_center = {
    Shape.I: (0.5, 1.5),
    Shape.J: (1, 1),
    Shape.L: (0, 1),
    Shape.O: (0.5, 0.5),
    Shape.S: (1, 1),
    Shape.T: (1, 0),
    Shape.Z: (1, 1),
    Shape.B: (0.5, 0.5),
}


class MoveFailedException(Exception):
    pass


class Position:
    x = None
    y = None

    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y


class Bitmap:
    """
    Base class for classes that store information about cells.
    """

    cells = None

    def collides(self, other):
        return any(cell in other for cell in self)

    def __iter__(self):
        return iter(self.cells)

    def __contains__(self, cell):
        return cell in self.cells


class Block(Bitmap):
    """
    Keeps track of the position of cells of a block.
    """

    shape = None
    color = None
    center = None

    def __init__(self, shape=None):
        self.shape = shape
        self.color = shape_to_color[shape]
        self.cells = shape_to_cells[shape]
        self.center = shape_to_center[shape]

    @property
    def left(self):
        """
        The leftmost x-position of the block.
        """

        return min(x for (x, y) in self)

    @property
    def right(self):
        """
        The rightmost x-position of the block.
        """

        return max(x for (x, y) in self)

    @property
    def top(self):
        """
        The topmost y-position of the block.
        """

        return min(y for (x, y) in self)

    @property
    def bottom(self):
        """
        The bottommost y-position of the block.
        """

        return max(y for (x, y) in self)

    def initialize(self, board):
        """
        Centers the block on the board.
        """

        center = self.left + (self.right - self.left) // 2
        shift = board.width // 2 - center
        self.cells = {(x+shift, y) for (x, y) in self}
        self.center = self.center[0] + shift, self.center[1]

    def supported(self, board):
        """
        Returns true if and only if the block is supported by the bottom of
        the board, or by another block. Basically, this means that moving the
        block down once more will mark it as dropped.
        """

        return any(
            (x, y+1) in board or y+1 == board.height
            for (x, y) in self
        )

    def move(self, direction, board, count=1):
        """
        Moves block count steps on on the board in the given direction. Returns
        true if this action caused the block to be dropped, false otherwise.
        """

        old_cells = self.cells

        if direction == Direction.Right:
            self.cells = {(x+count, y) for (x, y) in self}
            if self.right >= board.width or self.collides(board):
                # We hit something by moving; undo.
                self.cells = old_cells
            else:
                self.center = self.center[0]+count, self.center[1]
            return False

        elif direction == Direction.Left:
            self.cells = {(x-count, y) for (x, y) in self}
            if self.left < 0 or self.collides(board):
                # We hit something by moving; undo.
                self.cells = old_cells
            else:
                self.center = self.center[0]-count, self.center[1]
            return False

        elif direction == Direction.Down:
            if self.supported(board):
                # There is already something directly below the block; mark it
                # as dropped and do not move it.
                return True

            self.cells = {(x, y+count) for (x, y) in self}
            # Score a point for every row a block drops.
            board.score += count
            self.center = self.center[0], self.center[1]+count
            return False

        elif direction == Direction.Drop:
            while not self.supported(board):
                self.move(Direction.Down, board)
            return True

    def rotate(self, rotation, board):
        """
        Rotates block in the given direction on the board. Returns true if this
        action caused the block to be dropped, false otherwise.
        """

        # Save cells so we can cancel later.
        old_cells = self.cells
        old_center = self.center

        # Rotate around the center, which remains in place.
        cx, cy = self.center
        if rotation == Rotation.Clockwise:
            self.cells = {(int(-(y-cy)+cx), int(x-cx+cy)) for (x, y) in self}
        elif rotation == Rotation.Anticlockwise:
            self.cells = {(int(y-cy+cx), int(-(x-cx)+cy)) for (x, y) in self}

        try:
            # If block has hit left boundary, back off.
            left = self.left
            if left < 0:
                self.move(Direction.Right, board, -left)
                # We could not correct; abort the move.
                if self.left < 0:
                    raise MoveFailedException

            # Same for the right boundary.
            right = self.right
            if right >= board.width:
                self.move(Direction.Left, board, right-board.width+1)
                # We could not correct; abort moving.
                if self.right >= board.width:
                    raise MoveFailedException

            # Do not move beyond the top boundary either.
            top = self.top
            if top < 0:
                self.move(Direction.Down, board, -top)
                # We could not correct; abort moving.
                if self.top < 0:
                    raise MoveFailedException

            # If we rotated beyond the bottom, there is no way to correct.
            if self.bottom >= board.height:
                raise MoveFailedException

            # Also abort if the new position overlaps an existing block.
            if self.collides(board):
                raise MoveFailedException

        except MoveFailedException:
            # Go back to the old position if the rotation failed.
            self.cells = old_cells
            self.center = old_center

    def clone(self):
        block = Block(self.shape)
        block.cells = set(self)
        block.center = self.center
        return block


class Board(Bitmap):
    """
    Class that keeps track of occupied cells and the current falling block,
    as well as the score of the player. Can be used to duplicate the current
    state and explore possible future moves.
    """

    width = None
    height = None
    score = None
    lock = None

    falling = None
    next = None

    players_turn = None
    bombs_remaining = None
    discards_remaining = None

    def __init__(self, width, height, score=0,
                 discards_remaining=10, bombs_remaining=5):
        self.width = width
        self.height = height
        self.score = score
        self.cells = set()
        self.cellcolor = {}
        self.lock = Lock()
        self.bombs_remaining = bombs_remaining
        self.discards_remaining = discards_remaining

    def __str__(self):
        s = ("--------")
        for y in range(24):
            s += "\n"
            for x in range(10):
                if (x,y) in self.cells:
                    s += "#"
                else:
                    s += "."
        return s

    def line_full(self, line):
        """
        Checks if the given line is fully occupied by cells.
        """

        return all((x, line) in self for x in range(0, self.width))

    def remove_line(self, line):
        """
        Removes all blocks on a given line and moves down all blocks above.
        """

        self.cellcolor = {
            (x, y) if y > line else (x, y+1): c
            for (x, y), c in self.cellcolor.items() if y != line
        }

        self.cells = {
            (x, y) if y > line else (x, y+1)
            for (x, y) in self if y != line
        }

    def clean(self):
        """
        Cleans all fully occupied lines from the bottom down, and moves lines
        above the cleaned lines down as well.
        """

        scores = [0, 25, 100, 400, 1600]
        removed = 0

        line = self.height-1
        while line > 0:
            while self.line_full(line):
                self.remove_line(line)
                removed += 1
            line -= 1

        return scores[removed]

    def explode(self, pos):
        bx,by = next(iter(pos))

        # remove the cells exploded by the bomb
        self.cellcolor = {
            (x, y): c for (x, y), c in self.cellcolor.items() if (abs(bx - x) > 1 or abs(by - y) > 1)
        }
        # populate cells from cellcolor
        self.cells = {
            (x, y) for (x, y), c in self.cellcolor.items()
        }

        # shift anything above downwards
        for xi in range(bx-1,bx+2):
            lowest = 24
            for yi in range(by, 24):
                if (xi, yi) in self:
                    lowest = yi
                    break
            lowest -= 1
            for yi in range(by, -1, -1):
                if (xi,yi) in self:
                    c = self.cellcolor[(xi,yi)]
                    self.cells.remove((xi,yi))
                    self.cellcolor.pop((xi,yi))
                    self.cells.add((xi,lowest))
                    self.cellcolor[(xi,lowest)] = c
                    lowest -= 1
        
        #self.cellcolor[bx,by] = 'yellow'
        #self.cells.add((bx,by))
                          

        #self.cells = {
        #    (x, y) for (x, y) in self if (abs(bx - x) > 1 and abs(by - y) > 1) or (bx == x and by == y)
        #}

    @property
    def alive(self):
        """
        Checks if the falling block has collided with another existing block.
        If this is true, then the game is over.
        """

        with self.lock:
            return self.falling is None or not self.falling.collides(self)

    def place_next_block(self):
        assert(False)
        # The next block is now falling
        self.falling = self.next

        # Place the next block, if it exists.
        if self.falling is not None:
            self.falling.initialize(self)

        self.next = None

    def run_adversary(self, adversary):
        """
        Asks the adversary for a new block and places it on the board. Returns
        the shape of the newly placed block.
        """

        # Ask the adversary for a new next block.
        self.next = Block(adversary.choose_block(self))
        return self.next.shape

    def do_action(self, fn, clone, action=None):
        # if choose_action yielded a generator, we'll need to perform
        # the action on the clone as well as this board.  Otherwise
        # only apply it on this board.
        if clone:
            fn(clone, action)
        return fn(self,action)

    def run_player(self, player):
        """
        Asks the player for the next action and executes that on the board.
        Returns a tuple of a boolean and the move made, where the boolean
        indicates whether or not the current block has dropped.
        """

        while True:
            clone = self.clone()
            actions = player.choose_action(clone)

            try:
                actions = iter(actions)
            except TypeError:
                # We were given a single move.
                actions = [actions]


            if not isinstance(actions, GeneratorType):
                # save some work if choose_action didn't return a generator
                clone = None

            landed = False
            for action in actions:
                if action is None:
                    fn = Board.skip
                elif action is Action.Bomb:
                    fn = Board.bomb
                elif action is Action.Discard:
                    fn = Board.discard
                elif isinstance(action, Direction):
                    fn = Board.move
                elif isinstance(action, Rotation):
                    fn = Board.rotate
                landed = self.do_action(fn, clone, action)

                yield action

                if landed:
                    return

    def run(self, player, adversary):
        """
        Run the game with the given adversary and player. Will yield control
        back to the calling function every time a move has been made. Yields
        shapes (of new blocks) and moves (directions/rotations) as produced
        by the adversary or the player respectively.
        """

        # Initialize by choosing the "next" block first.
        yield self.run_adversary(adversary)

        # Place this block on the board
        self.place_next_block()

        while True:
            # The adversary can now choose a new next block.
            yield self.run_adversary(adversary)

            # The block may have caused the end of the game.
            if not self.alive:
                return

            # Ask the player for the next move(s) to make.
            yield from self.run_player(player)

    def land_block(self):
        # A bomb landed
        if self.falling.shape == Shape.B:
            self.explode(self.falling.cells)
        else:
            # A fallen block becomes part of the cells on the board.
            self.cells |= self.falling.cells
            for pos in self.falling.cells:
                self.cellcolor[pos] = self.falling.color
        self.falling = None

        # Clean up any completed rows and adjust score.
        self.score += self.clean()

        self.place_next_block()

    def move(self, direction):
        """
        Moves the current block in the direction given, and applies the
        implicit move down as well. Returns True if either this move or the
        subsequent move down caused the block to be dropped, False otherwise.
        """

        if self.falling is None:
            raise NoBlockException

        with self.lock:
            if self.falling.move(direction, self):
                self.land_block()
                return True

            # Block has not fallen yet; apply the implicit move down.
            if self.falling.move(Direction.Down, self):
                self.land_block()
                return True
            else:
                return False

    def rotate(self, rotation):
        """
        Rotates the current block as requested, and applies the implicit move
        down as well. Returns True if the subsequent move down caused the block
        to be dropped, False otherwise.
        """

        if self.falling is None:
            raise NoBlockException

        with self.lock:
            self.falling.rotate(rotation, self)

            # Apply the implicit move down.
            if self.falling.move(Direction.Down, self):
                self.land_block()
                return True
            else:
                return False

    def bomb(self, action=None):
        """
        Skips the current turn, applies the implicit move down, and
        switches the next block to be a Bomb. Returns True if this
        move caused the block to be dropped, False otherwise.
        """
        if self.bombs_remaining > 0 \
           and self.next is not None \
           and self.next.shape is not Shape.B:
            self.next = Block(Shape.B)
            self.bombs_remaining -= 1
        return self.skip()

    def discard(self, action=None):
        """
        Discards the current block, switching to the next block. Returns
        True if this move caused the block to be dropped, False
        otherwise.  Will raise NoBlockException if there is no next
        block, so don't call this twice while testing possible moves.
        Returns True if successful to be consistent with other moves,
        as the falling block did change to the next block.
        """
        if self.falling is None:
            raise NoBlockException

        with self.lock:
            if self.discards_remaining > 0:
                self.discards_remaining -= 1
                self.place_next_block()
                return True
            return False

    def skip(self, action=None):
        """
        Skips the current turn, and applies the implicit move down. Returns
        True if this move caused the block to be dropped, False otherwise.
        """
        if self.falling is None:
            raise NoBlockException

        with self.lock:
            res = self.falling.move(Direction.Down, self)
            if res:
                self.land_block()
            return res

    def clone(self):
        """
        Creates a copy of the board; can be used to simulate possible moves.
        """

        board = Board(self.width, self.height, self.score,
                      self.discards_remaining, self.bombs_remaining)
        board.cells = set(self)

        # Copy the falling block, if any.
        if self.falling is not None:
            board.falling = self.falling.clone()

        # Copy the next block, if any.
        if self.next is not None:
            board.next = self.next.clone()

        return board
