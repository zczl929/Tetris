from adversary import RandomAdversary
from arguments import parser
from board import Board, Direction, Rotation, Action
from constants import BOARD_WIDTH, BOARD_HEIGHT, DEFAULT_SEED, INTERVAL,\
    BLOCK_LIMIT
from exceptions import BlockLimitException
from player import SelectedPlayer, Player
from time import sleep

import curses
import curses.ascii


COLOR_WALL = 1
COLOR_BLOCK = 2
COLOR_CELL = 3
COLOR_NOTHING = 4
COLOR_RED = 5
COLOR_ORANGE = 6
COLOR_YELLOW = 7
COLOR_GREEN = 8
COLOR_CYAN = 9
COLOR_BLUE = 10
COLOR_MAGENTA = 11
COLOR_BOMB = 12
COLOR_DISCARD = 13
COLOR_NAMES = {
    "red": COLOR_RED,
    "orange": COLOR_ORANGE,
    "yellow": COLOR_YELLOW,
    "green": COLOR_GREEN,
    "cyan": COLOR_CYAN,
    "blue": COLOR_BLUE,
    "magenta": COLOR_MAGENTA,
    "white": COLOR_BOMB
}

def paint(window, x, y, color, count=1):
    if color == COLOR_BOMB:
        window.addstr(y, x*2, '<>' * count, curses.color_pair(color))
    else:
        window.addstr(y, x*2, '  ' * count, curses.color_pair(color))

def render(window, board):
    """
    Write a depiction of the board to standard output.
    """

    for y in range(board.height):
        # Draw each individual row
        for x in range(board.width):
            if board.falling is not None and (x, y) in board.falling:
                # Location is occupied by falling block
                color = COLOR_NAMES[board.falling.color]
            elif (x, y) in board:
                # Location is occupied by fallen block
                color = COLOR_NAMES[board.cellcolor[(x, y)]]
            else:
                # There is nothing here.
                color = COLOR_NOTHING
            paint(window, x+1, y, color)

    # Draw the score
    window.addstr(
        0,
        (board.width*2)+5,
        f'SCORE: {board.score} ',
        curses.color_pair(COLOR_NOTHING)
    )

    # Draw the next piece
    window.addstr(2, (board.width*2)+5, 'NEXT',
                  curses.color_pair(COLOR_NOTHING))
    if board.next is not None:
        for y in range(6):
            for x in range(4):
                if (x, y) in board.next:
                    color = COLOR_NAMES[board.next.color]
                else:
                    color = COLOR_NOTHING

                paint(window, board.width+x+3, y+3, color)

    # Draw the bombs
    window.addstr(7, (board.width*2)+5, 'BOMBS',
                  curses.color_pair(COLOR_NOTHING))
    for bomb in range(1,6):
        if board.bombs_remaining >= bomb:
            s = '<>'
            color = COLOR_BOMB
        else:
            s = '  '
            color = COLOR_NOTHING
        window.addstr(8, (board.width*2)+5+(bomb-1)*3, s,
                      curses.color_pair(color))
        

    # Draw the Discards
    window.addstr(10, (board.width*2)+5, 'DISCARDS',
                  curses.color_pair(COLOR_NOTHING))
    discards = board.discards_remaining
    if discards >= 5:
        s1 = "X X X X X"
        s2 = (discards - 5)*" X" + (10-discards)*"  "
    else:
        s1 = discards*"X " + (5-discards)*"  "
        s2 = "          "
    window.addstr(11, (board.width*2)+5, s1,
                  curses.color_pair(COLOR_DISCARD))
    window.addstr(12, (board.width*2)+5, s2,
                  curses.color_pair(COLOR_DISCARD))
    
    

    # Draw the board frame
    window.move(0, 0)
    window.vline(curses.ACS_VLINE, board.height+2)
    window.move(0, 1)
    window.vline(curses.ACS_VLINE, board.height+1)
    window.addch(0, 0, curses.ACS_ULCORNER)
    window.addch(0, 1, curses.ACS_URCORNER)
    window.move(0, board.width*2+2)
    window.vline(curses.ACS_VLINE, board.height+1)
    window.move(0, board.width*2+3)
    window.vline(curses.ACS_VLINE, board.height+2)
    window.addch(0, board.width*2+2, curses.ACS_ULCORNER)
    window.addch(0, board.width*2+3, curses.ACS_URCORNER)
    window.move(board.height+1, 0)
    window.hline(curses.ACS_HLINE, board.width*2+3)
    window.move(board.height, 1)
    window.hline(curses.ACS_HLINE, board.width*2+1)
    window.addch(board.height+1, 0, curses.ACS_LLCORNER)
    window.addch(board.height, 1, curses.ACS_LLCORNER)
    window.addch(board.height+1, board.width*2+3, curses.ACS_LRCORNER)
    window.addch(board.height, board.width*2+2, curses.ACS_LRCORNER)
    window.move(board.height+2, 0)

    window.refresh()


class UserPlayer(Player):
    """
    A simple user player that reads moves from the command line.
    """

    screen = None

    def __init__(self, window):
        self.window = window

    def choose_action(self, board):
        key = self.window.getch()

        if key == -1:
            return None
        elif key == curses.KEY_RIGHT:
            return Direction.Right
        elif key == curses.KEY_LEFT:
            return Direction.Left
        elif key == curses.KEY_DOWN:
            return Direction.Down
        elif key == ord(' '):
            return Direction.Drop
        elif key == curses.KEY_UP:
            return Rotation.Clockwise
        elif key == ord('z'):
            return Rotation.Anticlockwise
        elif key == ord('x'):
            return Rotation.Clockwise
        elif key == ord('b'):
            return Action.Bomb
        elif key == ord('d'):
            return Action.Discard
        elif key == curses.ascii.ESC or key == ord('q'):
            raise SystemExit


def run(window):
    board = Board(BOARD_WIDTH, BOARD_HEIGHT)
    adversary = RandomAdversary(DEFAULT_SEED, BLOCK_LIMIT)

    args = parser.parse_args()
    if args.manual:
        window.timeout(INTERVAL)
        player = UserPlayer(window)
    else:
        window.timeout(0)
        player = SelectedPlayer()

    try:
        for move in board.run(player, adversary):
            render(window, board)

            if not args.manual:
                while True:
                    key = window.getch()
                    if key == -1:
                        break
                    elif key == curses.ascii.ESC:
                        raise SystemExit
            sleep(0.1)
    except BlockLimitException:
        window.addstr(BOARD_HEIGHT//2, 2,
                      "Out of blocks", curses.color_pair(COLOR_NOTHING))
    window.addstr(BOARD_HEIGHT//2+1, 2,
                  "Score="+ str(board.score), curses.color_pair(COLOR_NOTHING))
    window.addstr(BOARD_HEIGHT//2+2, 2,
                  "Press a key to exit", curses.color_pair(COLOR_NOTHING))
    window.timeout(-1)
    window.getch()


if __name__ == '__main__':
    try:
        # Initialize terminal settings
        curses.initscr()
        curses.start_color()
        curses.noecho()
        curses.cbreak()

        window = curses.newwin(
            BOARD_HEIGHT + 3,
            (BOARD_WIDTH + 2 + 7)*2 + 1
        )
        window.keypad(True)

        # Prepare some colors to use for drawing.
        curses.init_pair(COLOR_WALL, curses.COLOR_WHITE, curses.COLOR_CYAN)
        curses.init_pair(COLOR_BLOCK, curses.COLOR_WHITE, curses.COLOR_RED)
        curses.init_pair(COLOR_CELL, curses.COLOR_WHITE, curses.COLOR_WHITE)
        curses.init_pair(COLOR_NOTHING, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(COLOR_DISCARD, curses.COLOR_RED, curses.COLOR_BLACK)

        # Orange is not supported.
        curses.init_pair(COLOR_ORANGE, curses.COLOR_WHITE, curses.COLOR_WHITE)
        curses.init_pair(COLOR_RED, curses.COLOR_WHITE, curses.COLOR_RED)
        curses.init_pair(COLOR_YELLOW, curses.COLOR_WHITE, curses.COLOR_YELLOW)
        curses.init_pair(COLOR_GREEN, curses.COLOR_WHITE, curses.COLOR_GREEN)
        curses.init_pair(COLOR_CYAN, curses.COLOR_WHITE, curses.COLOR_CYAN)
        curses.init_pair(COLOR_BLUE, curses.COLOR_WHITE, curses.COLOR_BLUE)
        curses.init_pair(
            COLOR_MAGENTA,
            curses.COLOR_WHITE,
            curses.COLOR_MAGENTA
        )
        curses.init_pair(COLOR_BOMB, curses.COLOR_BLACK, curses.COLOR_WHITE)

        run(window)
    finally:
        # Clean up terminal settings once we are done
        window.keypad(False)

        curses.nocbreak()
        curses.echo()
        curses.endwin()
