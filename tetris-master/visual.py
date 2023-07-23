from threading import Condition, Thread
from time import sleep
from tkinter import Tk, Canvas, Frame, BOTH, TclError, font

from adversary import RandomAdversary
from arguments import parser
from board import Board, Direction, Rotation, Action, Shape
from constants import BOARD_HEIGHT, BOARD_WIDTH, DEFAULT_SEED, INTERVAL, \
    BLOCK_LIMIT
from exceptions import BlockLimitException
from player import SelectedPlayer, Player

DRAW_INTERVAL = 100


class Visual(Frame):
    board = None
    canvas = None
    discards = None
    bombs = None
    score = None

    CELL_SIZE = 20

    def __init__(self, board):
        super().__init__()

        self.board = board

        self.master.geometry(
            f'{(BOARD_WIDTH+6)*self.CELL_SIZE}x' +
            f'{BOARD_HEIGHT*self.CELL_SIZE}'
        )

        self.pack(fill=BOTH, expand=1)
        self.canvas = Canvas(self, bg="black")
        self.canvas.pack(fill=BOTH, expand=1)

        self.after(DRAW_INTERVAL, self.draw)

        self.focus_set()
        self.bind("<Escape>", self.quit)
        self.bind("q", self.quit)
        self.bind("Control-c", self.quit)

        GREY = '#1e1e1e'
        for i in range(0,10,2):
           self.canvas.create_rectangle(i * self.CELL_SIZE, 0, (i+1)*self.CELL_SIZE,
                                         BOARD_HEIGHT * self.CELL_SIZE, fill=GREY) 

        try:
            self.font = font.nametofont("Helvetica")
        except:
            self.font = font.nametofont("TkDefaultFont")

        # No easy way to predict what font we'll get - it differs
        # depending on the environment, so we'll just scale it until
        # it's large enough.  This is ugly.
        size = 10
        width = 0
        while width < 90:
            size += 1
            self.font.configure(size=size)
            testtxt = self.canvas.create_text(0,-100, text="DISCARDS", font = self.font)
            bounds = self.canvas.bbox(testtxt)
            width = bounds[2] - bounds[0]
            self.canvas.delete(testtxt)

        self.scorefont = font.nametofont("TkFixedFont")
        size = 10
        width = 0
        while width < 100:
            size += 1
            self.scorefont.configure(size=size)
            testtxt = self.canvas.create_text(0,-100, text="88888", font = self.scorefont)
            bounds = self.canvas.bbox(testtxt)
            width = bounds[2] - bounds[0]
            self.canvas.delete(testtxt)

        self.text = self.canvas.create_text((BOARD_WIDTH + 3)*self.CELL_SIZE, 0,
                                            text="SCORE", font=self.font, anchor="n",
                                            fill="white")

        self.scoretext = self.canvas.create_text((BOARD_WIDTH + 3)*self.CELL_SIZE,
                                            self.CELL_SIZE-5,
                                            text=str(self.board.score),
                                            font=self.scorefont, anchor="n",
                                            fill="white", tag="score")

        self.text = self.canvas.create_text((BOARD_WIDTH + 3)*self.CELL_SIZE,
                                            self.CELL_SIZE*3,
                                            text="NEXT", font=self.font, anchor="n",
                                            fill="white")

        self.text = self.canvas.create_text((BOARD_WIDTH + 3)*self.CELL_SIZE,
                                            self.CELL_SIZE*9,
                                            text="BOMBS", font=self.font, anchor="n",
                                            fill="white")

        self.text = self.canvas.create_text((BOARD_WIDTH + 3)*self.CELL_SIZE,
                                            self.CELL_SIZE*12,
                                            text="DISCARDS", font=self.font, anchor="n",
                                            fill="white")

    def update_score(self):
        if self.board.score == self.score:
            return
        self.score = self.board.score
        self.canvas.itemconfig(self.scoretext, text=str(self.board.score))
        self.master.title(f'Score: {self.board.score}')
        
    def quit(self, event):
        raise SystemExit

    def draw_cell(self, x, y, color, shape):
        if shape is Shape.B:
            self.canvas.create_oval(
                x * self.CELL_SIZE, y * self.CELL_SIZE,
                (x+1) * self.CELL_SIZE, (y+1) * self.CELL_SIZE,
                fill="white", tag="block")
        else:
            # tkinter's idea of green is rather dark
            if color == 'green':
                color = 'green2'
            self.canvas.create_rectangle(
                x * self.CELL_SIZE, y * self.CELL_SIZE,
                (x+1) * self.CELL_SIZE, (y+1) * self.CELL_SIZE,
                fill=color, outline="white", tag="block")

    def draw_discard(self, x, y):
        x = x * self.CELL_SIZE
        y = y * self.CELL_SIZE
        self.canvas.create_line(x, y, x+self.CELL_SIZE, y+self.CELL_SIZE,
                                fill="red", width=3, tag="discard")
        self.canvas.create_line(x, y+self.CELL_SIZE, x+self.CELL_SIZE, y,
                                fill="red", width=3, tag="discard")

    def update_discards(self):
        if self.board.discards_remaining == self.discards:
            # don't redraw if the discards are unchanged
            return
        self.discards = self.board.discards_remaining
        self.canvas.delete("discard")
        for i in range(self.board.discards_remaining):
            self.draw_discard(BOARD_WIDTH + 0.25 + (i%5)*1.1,13+(i//5)*1.1)

    def draw(self):
        with self.board.lock:
            self.canvas.delete("block")
            self.update_score()
            self.update_discards()
            
            # Add the cells already on the board for drawing. 
            for (x, y) in self.board:
                self.draw_cell(x, y, self.board.cellcolor[x, y], Shape.O)

            if self.board.falling is not None:
                # Add the cells of the falling block for drawing. 
                for (x, y) in self.board.falling:
                    self.draw_cell(x, y, self.board.falling.color,
                                   self.board.falling.shape)

            if self.board.next is not None:
                # Add the cells of the next block for drawing.
                width = self.board.next.right - self.board.next.left
                for (x, y) in self.board.next:
                    self.draw_cell(x + BOARD_WIDTH + 2.5 - width/2, y+4,
                                   self.board.next.color,
                                   self.board.next.shape)

            for i in range(self.board.bombs_remaining):
                self.draw_cell(BOARD_WIDTH + 0.25 + i*1.1,10, "white", Shape.B)

            x = BOARD_WIDTH * self.CELL_SIZE + 1
            y = BOARD_HEIGHT * self.CELL_SIZE
            self.canvas.create_line(x, 0, x, y, fill='blue')

            self.after(DRAW_INTERVAL, self.draw)


class UserPlayer(Player):
    has_move = None
    target = None
    next_move = None

    def __init__(self, target):
        self.has_move = Condition()
        self.target = target

        target.focus_set()
        target.bind("<Up>", self.key)
        target.bind("<Right>", self.key)
        target.bind("<Down>", self.key)
        target.bind("<Left>", self.key)
        target.bind("<space>", self.key)
        target.bind("z", self.key)
        target.bind("x", self.key)
        target.bind("b", self.key)
        target.bind("d", self.key)

        target.after(INTERVAL, self.drop)

    def key(self, event):
        with self.has_move:
            if event.keysym == 'Up':
                self.next_move = Rotation.Clockwise
            elif event.keysym == 'Right':
                self.next_move = Direction.Right
            elif event.keysym == 'Down':
                self.next_move = Direction.Down
            elif event.keysym == 'Left':
                self.next_move = Direction.Left
            elif event.keysym == 'space':
                self.next_move = Direction.Drop
            elif event.keysym == 'z':
                self.next_move = Rotation.Clockwise
            elif event.keysym == 'x':
                self.next_move = Rotation.Anticlockwise
            elif event.keysym == 'b':
                self.next_move = Action.Bomb
            elif event.keysym == 'd':
                self.next_move = Action.Discard
            else:
                return

            self.has_move.notify()

    def drop(self):
        with self.has_move:
            self.next_move = None
            self.has_move.notify()

        self.target.after(INTERVAL, self.drop)

    def choose_action(self, board):
        with self.has_move:
            self.has_move.wait()
            try:
                return self.next_move
            finally:
                self.next_move = None


def run():
    root = Tk()

    # Try making window a dialog if the system allows it.
    try:
        root.attributes('-type', 'dialog')
    except TclError:
        pass

    args = parser.parse_args()
    if args.manual:
        player = UserPlayer(root)
    else:
        player = SelectedPlayer()

    adversary = RandomAdversary(DEFAULT_SEED, BLOCK_LIMIT)
    board = Board(BOARD_WIDTH, BOARD_HEIGHT)

    def runner():
        try:
            for move in board.run(player, adversary):
                # When not playing manually, allow some time to see the move.
                if not args.manual:
                    sleep(0.05)
        except BlockLimitException:
            print("Out of blocks")
        print("Score=", board.score)
        print("Press ESC in game window to exit")

    Visual(board)

    background = Thread(target=runner)
    background.daemon = True
    background.start()

    root.mainloop()
    raise SystemExit


if __name__ == '__main__':
    run()
