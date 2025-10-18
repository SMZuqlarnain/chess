# movefinder.py
# NegaMax with alpha-beta pruning. Depth passed in by main (default 5).

import random

pieceScore = {"K": 100000, "Q": 900, "R": 500, "B": 330, "N": 320, "p": 100}
CHECKMATE = 1000000
DEFAULT_DEPTH = 5  # default starts at 5 (user-changeable)

def findBestMove(gs, validMoves, depth=DEFAULT_DEPTH):
    """
    Root entry: negamax alpha-beta. depth is number of plies.
    """
    global nextMove, nodes, rootDepth
    nextMove = None
    nodes = 0
    rootDepth = depth
    # shallow randomization and move ordering (captures first)
    moves = sorted(validMoves, key=lambda m: (m.pieceCaptured != "--"), reverse=True)
    turnMultiplier = 1 if gs.whiteToMove else -1
    negamaxAlphaBeta(gs, moves, depth, -CHECKMATE, CHECKMATE, turnMultiplier, rootCall=True)
    # print("nodes:", nodes)
    return nextMove

def negamaxAlphaBeta(gs, moves, depth, alpha, beta, turnMultiplier, rootCall=False):
    global nextMove, nodes, rootDepth
    nodes += 1
    if depth == 0:
        return turnMultiplier * scoreBoard(gs)

    maxScore = -CHECKMATE
    # order moves: captures first (already sorted at root; deeper nodes can sort as well)
    moves = sorted(moves, key=lambda m: (m.pieceCaptured != "--"), reverse=True)
    for m in moves:
        gs.makeMove(m)
        nextMoves = gs.getValidMoves()
        score = -negamaxAlphaBeta(gs, nextMoves, depth-1, -beta, -alpha, -turnMultiplier)
        gs.undoMove()
        if score > maxScore:
            maxScore = score
            if rootCall:
                nextMove = m
        alpha = max(alpha, score)
        if alpha >= beta:
            break
    return maxScore

def scoreBoard(gs):
    # terminal states
    if gs.isCheckmate():
        return -CHECKMATE if gs.whiteToMove else CHECKMATE
    if gs.isStalemate():
        return 0
    score = 0
    for row in gs.board:
        for sq in row:
            if sq != "--":
                sign = 1 if sq[0] == 'w' else -1
                score += sign * pieceScore.get(sq[1], 0)
    return score
