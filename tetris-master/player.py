import time
from random import Random

from board import Action, Direction, Shape, Rotation


class Player:
    def choose_action(self, board):
        raise NotImplementedError

class myPlayer(Player):
    def __init__(self, seed=None):
        self.random = Random(seed)

    def choose_action(self, board):
        bestscore = -100000000
        bestmoves = []
        #check all the possible rotations and the positions of the block
        for tx in range(board.width):
            for rt in range(4):
                clonedBoard = board.clone()
                initScore = board.score
                initFalling = board.falling

                sandbox = testBoard(clonedBoard, initScore, initFalling)
                score, moveList = sandbox.move_to_target(rt, tx)
                # holes = sandbox.get_holes()

                if (score> bestscore):
                    bestscore = score
                    bestmoves = moveList

                    # if hole is made
                    
                    # print("bestscore", bestscore)
                    # if (bestscore < -10000000):
                    #     countdiscards = self.discards_remaining
                    #     if (countdiscards > 0):
                    #         bestmoves = [Action.Discard]
                    #         countdiscards -= 1

                for tx in range(board.width):
                    for rt in range(4):
                        clonedBoard = board.clone()
                        initScore = board.score
                        initFalling = board.falling

                        sandbox2 = testBoard(clonedBoard, initScore, initFalling)
                        score2, moveList2 = sandbox2.move_to_target(rt, tx)
                        holes2 = sandbox2.get_holes()

                        if (score2> bestscore):
                            bestscore = score2
                            bestmoves = moveList2

                            
                            
                            # discards_remaining = 10
                            # print("bestscore", bestscore)
                            # print("holes2", holes2)
                            
                            # if (holes2 > 3):
                            #     if (discards_remaining > 0):
                            #         bestmoves = [Action.Discard]
                            #         discards_remaining -= 1
                            


        return bestmoves

    

class testBoard():
    def __init__(self, board, initScore, initFalling):
        self.board = board # board.clone()
        self.cells = board.cells
        self.initScore = initScore
        self.initFalling = initFalling
    
    def move_to_target(self, rt, tx):
        moveList = []
        score = 0

        for i in range(rt):
            landed = self.board.rotate(Rotation.Clockwise)
            moveList.append(Rotation.Clockwise)
            if landed:
                score = self.scoreBoard(tx)
                break

        while True:
            # mostleft = self.board.falling.left
            if tx < self.board.falling.left:
                landed = self.board.move(Direction.Left)
                moveList.append(Direction.Left)   
            elif tx > self.board.falling.left:
                landed = self.board.move(Direction.Right)
                moveList.append(Direction.Right)
            else:
                landed = self.board.move(Direction.Drop)
                moveList.append(Direction.Drop)
            if landed:
                score = self.scoreBoard(tx)
                break
        return score, moveList
    
    def get_heights(self):
        heightList = []
        maxY = 24
        for x in range(self.board.width):    
            for y in range(self.board.height):
                if (x,y) in self.board.cells:
                    maxY = y
                    break
            heightList.append(24-maxY)
        return heightList

    # count the number of holes
    def get_holes(self):
        countholes = set(())
        heightList = self.get_heights()
        for x in range(0,self.board.width):
            for y in (range(24-heightList[x], 24)):
                if (x, y) not in self.board.cells:
                    countholes.add((x,y))
                # print("countholes", countholes)
        holes = len(countholes)
        return holes

    
    # above the holes
    def get_blocks(self):
        blocks = 0
        heightList = self.get_heights()
        for x in range(self.board.width):
            for y in reversed(range(len(heightList))):
                if (x, y) in self.board.cells:
                    blocks += 1
        return blocks
    
     #Bumpiness/ smaller the difference in height get higher score
    def get_bumpiness(self):
        bumpiness = 0
        heightList = self.get_heights()
        for i in range(self.board.width -1):
            bumpiness += abs(heightList[i]-heightList[i+1])
        return bumpiness
    
    def remove_FourRows(self):
        if (self.board.score - self.initScore >= 1600):
            #  print("self.board.score - self.prevScore", self.board.score - self.prevScore)
            return 1
        else:
            return 0
        
    def fill_FourRows(self):
        fourRows= set([])
        for i in range(0, 10):
            for j in range(1, 4):
                if (i, 24-j) in self.cells:
                    fourRows.add((i, 24-j))
        getfourRows = len(fourRows)
        return getfourRows
    
    def scoreBoard(self, tx):
        # tx = 0-8, higher score
        xscore = 0
        if tx in range(9):
            xscore = 1

        #lowest height get beeter score, bigger y get higher score
        heightList = self.get_heights()
        holes = self.get_holes()
        blocks = self.get_blocks()
        bumpiness = self.get_bumpiness()
        getfourRows = self.fill_FourRows()

        # #least number of holes, weighing more on holes get higher score
        score = 0
        score -= holes * 1000
        # score -= sum(heightList) 
        score -= bumpiness *100
        score += getfourRows 
        # score += xscore
        if (self.initFalling.shape == Shape.I):
             score += 90000 * self.remove_FourRows()
        return score
    
SelectedPlayer = myPlayer















