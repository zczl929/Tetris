from adversary import RandomAdversary
from arguments import parser
from board import Board, Direction, Rotation, Action, Shape
from constants import BOARD_WIDTH, BOARD_HEIGHT, DEFAULT_SEED, INTERVAL, \
    BLOCK_LIMIT
from exceptions import BlockLimitException
from player import Player, SelectedPlayer

import pygame

BLACK = (0, 0, 0)
GREY = (30, 30, 30)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)

CELL_WIDTH = 20
CELL_HEIGHT = 20

EVENT_FORCE_DOWN = pygame.USEREVENT + 1
FRAMES_PER_SECOND = 60


class Block(pygame.sprite.Sprite):
    def __init__(self, color, x, y, shape):
        super().__init__()

        self.image = pygame.Surface([CELL_WIDTH, CELL_HEIGHT])
        if shape is Shape.B:
            pygame.draw.circle(self.image, WHITE, [CELL_WIDTH//2, CELL_HEIGHT//2],
                               CELL_WIDTH/2)
        else:
            self.image.fill(color)
            pygame.draw.rect(self.image, WHITE, [0, 0, CELL_WIDTH, CELL_HEIGHT], width=1)

        self.rect = self.image.get_rect()
        self.rect.x = x * CELL_WIDTH
        self.rect.y = y * CELL_HEIGHT

class Discard(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()

        self.image = pygame.Surface([CELL_WIDTH, CELL_HEIGHT])
        pygame.draw.line(self.image, RED, (0, 0), (CELL_WIDTH, CELL_HEIGHT), width=3)
        pygame.draw.line(self.image, RED, (0, CELL_HEIGHT), (CELL_WIDTH, 0), width=3)

        self.rect = self.image.get_rect()
        self.rect.x = x * CELL_WIDTH
        self.rect.y = y * CELL_HEIGHT

txt = []
def init_text(screen):
    global txt, scorefont
    font = pygame.font.SysFont(None, 24)
    img = font.render('SCORE', True, WHITE)
    txt.append((img, ((BOARD_WIDTH + 3)*CELL_WIDTH - img.get_rect().width//2, 0)))
    img = font.render('NEXT', True, WHITE)
    txt.append((img, ((BOARD_WIDTH + 3)*CELL_WIDTH - img.get_rect().width//2, CELL_HEIGHT*3)))
    img = font.render('BOMBS', True, WHITE)
    txt.append((img, ((BOARD_WIDTH + 3)*CELL_WIDTH - img.get_rect().width//2, CELL_HEIGHT*9)))
    img = font.render('DISCARDS', True, WHITE)
    txt.append((img, ((BOARD_WIDTH + 3)*CELL_WIDTH - img.get_rect().width//2, CELL_HEIGHT*12)))

    scorefont = pygame.font.Font("Segment7-4Gml.otf", 40)

def render(screen, board):
    global scorefont, txt
    screen.fill(BLACK)
    for t,pos in txt:
        screen.blit(t, pos)    

    for i in range(0,10,2):
        pygame.draw.rect(screen, GREY,
                         [i * CELL_WIDTH, 0,
                          CELL_WIDTH, board.height * CELL_HEIGHT])

    img = scorefont.render(str(board.score), True, WHITE)
    screen.blit(img, ((BOARD_WIDTH + 3)*CELL_WIDTH - img.get_rect().width//2, CELL_HEIGHT))

    sprites = pygame.sprite.Group()

    # Add the cells already on the board for drawing.
    for (x, y) in board:
        sprites.add(Block(pygame.Color(board.cellcolor[x, y]), x, y, Shape.O))

    if board.falling is not None:
        # Add the cells of the falling block for drawing.
        for (x, y) in board.falling:
            sprites.add(Block(pygame.Color(board.falling.color), x, y, board.falling.shape))

    if board.next is not None:
        # Add the cells of the next block for drawing.
        width = board.next.right - board.next.left
        for (x, y) in board.next:
            sprites.add(
                Block(pygame.Color(board.next.color),
                      x + board.width + 2.5 - width/2, y+4,
                      board.next.shape))

    for i in range(board.bombs_remaining):
        sprites.add(Block(pygame.Color(WHITE),board.width + 0.4 + i*1.1,10, Shape.B))

    for i in range(board.discards_remaining):
        sprites.add(Discard(board.width + 0.4 + (i%5)*1.1,13+(i//5)*1.1))
        
    sprites.draw(screen)

    pygame.draw.line(
        screen,
        BLUE,
        (board.width * CELL_WIDTH + 2, 0),
        (board.width * CELL_WIDTH + 2, board.height * CELL_HEIGHT)
    )

    # Update window title with score.
    pygame.display.set_caption(f'Score: {board.score}')


class UserPlayer(Player):
    """
    A simple user player that reads moves from the command line.
    """

    key_to_move = {
        pygame.K_RIGHT: Direction.Right,
        pygame.K_LEFT: Direction.Left,
        pygame.K_DOWN: Direction.Down,
        pygame.K_SPACE: Direction.Drop,
        pygame.K_UP: Rotation.Clockwise,
        pygame.K_z: Rotation.Anticlockwise,
        pygame.K_x: Rotation.Clockwise,
        pygame.K_b: Action.Bomb,
        pygame.K_d: Action.Discard
    }

    def choose_action(self, board):
        while True:
            event = pygame.event.wait()
            if event.type == pygame.QUIT:
                raise SystemExit
            elif event.type == pygame.KEYUP:
                if event.key in self.key_to_move:
                    return self.key_to_move[event.key]
                elif event.key == pygame.K_ESCAPE or event.key == pygame.K_q:
                    raise SystemExit
            elif event.type == EVENT_FORCE_DOWN:
                return None


def check_stop():
    for event in pygame.event.get():
        if event.type == pygame.KEYUP and event.key == pygame.K_ESCAPE:
            raise SystemExit
        elif event.type == pygame.QUIT:
            raise SystemExit


def run():
    board = Board(BOARD_WIDTH, BOARD_HEIGHT)
    adversary = RandomAdversary(DEFAULT_SEED, BLOCK_LIMIT)

    args = parser.parse_args()
    if args.manual:
        player = UserPlayer()
    else:
        player = SelectedPlayer()

    pygame.init()

    screen = pygame.display.set_mode([
        (BOARD_WIDTH + 6) * CELL_WIDTH,
        BOARD_HEIGHT * CELL_HEIGHT
    ])

    clock = pygame.time.Clock()

    init_text(screen)

    # Set timer to force block down when no input is given.
    pygame.time.set_timer(EVENT_FORCE_DOWN, INTERVAL)

    try:
        for move in board.run(player, adversary):
            render(screen, board)
            pygame.display.flip()

            # If we are not playing manually, clear the events.
            if not args.manual:
                check_stop()

                clock.tick(FRAMES_PER_SECOND)

        print("Score=", board.score)
        print("Press ESC in game window to exit")
        while True:
            check_stop()
    except BlockLimitException:
        print("Out of blocks")
        print("Score=", board.score)
        print("Press ESC in game window to exit")
        while True:
            check_stop()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    run()
