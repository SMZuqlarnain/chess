# chessengine.py
# Game state, move generation, execution/undo, castling, en-passant, promotion, check detection.
# isSquareAttacked implemented without toggling turns to avoid recursion.

class Move:
    ranksToRows = {"1":7, "2":6, "3":5, "4":4, "5":3, "6":2, "7":1, "8":0}
    rowsToRanks = {v:k for k,v in ranksToRows.items()}
    filesToCols = {"a":0, "b":1, "c":2, "d":3, "e":4, "f":5, "g":6, "h":7}
    colsToFiles = {v:k for k,v in filesToCols.items()}

    def __init__(self, startSq, endSq, board, pieceMoved=None, pieceCaptured=None,
                 isEnpassantMove=False, isCastleMove=False, promotionChoice=None):
        self.startRow = startSq[0]
        self.startCol = startSq[1]
        self.endRow = endSq[0]
        self.endCol = endSq[1]
        self.pieceMoved = pieceMoved if pieceMoved else board[self.startRow][self.startCol]
        self.pieceCaptured = pieceCaptured if pieceCaptured else board[self.endRow][self.endCol]
        self.isPawnPromotion = (self.pieceMoved[1] == 'p' and (self.endRow == 0 or self.endRow == 7))
        self.isEnpassantMove = isEnpassantMove
        if self.isEnpassantMove:
            self.pieceCaptured = 'bp' if self.pieceMoved[0] == 'w' else 'wp'
        self.isCastleMove = isCastleMove
        self.promotionChoice = promotionChoice

    def getChessNotation(self):
        return self.getRankFile(self.startRow, self.startCol) + self.getRankFile(self.endRow, self.endCol)

    def getRankFile(self, r, c):
        return self.colsToFiles[c] + self.rowsToRanks[r]

class CastlingRights:
    def __init__(self, wks, bks, wqs, bqs):
        self.wks = wks
        self.bks = bks
        self.wqs = wqs
        self.bqs = bqs

class GameState:
    def __init__(self):
        self.board = [
            ["bR","bN","bB","bQ","bK","bB","bN","bR"],
            ["bp","bp","bp","bp","bp","bp","bp","bp"],
            ["--","--","--","--","--","--","--","--"],
            ["--","--","--","--","--","--","--","--"],
            ["--","--","--","--","--","--","--","--"],
            ["--","--","--","--","--","--","--","--"],
            ["wp","wp","wp","wp","wp","wp","wp","wp"],
            ["wR","wN","wB","wQ","wK","wB","wN","wR"]
        ]
        self.whiteToMove = True
        self.moveLog = []
        self.whiteKingLocation = (7,4)
        self.blackKingLocation = (0,4)
        self.inCheck = False
        self.pins = []
        self.checks = []
        self.enPassantPossible = ()  # (row,col) or ()
        self.currentCastlingRights = CastlingRights(True, True, True, True)
        self.castleRightsLog = [CastlingRights(self.currentCastlingRights.wks,
                                               self.currentCastlingRights.bks,
                                               self.currentCastlingRights.wqs,
                                               self.currentCastlingRights.bqs)]

    def makeMove(self, move):
        # execute move
        self.board[move.startRow][move.startCol] = "--"
        self.board[move.endRow][move.endCol] = move.pieceMoved
        self.moveLog.append(move)

        # update king location
        if move.pieceMoved == 'wK':
            self.whiteKingLocation = (move.endRow, move.endCol)
        elif move.pieceMoved == 'bK':
            self.blackKingLocation = (move.endRow, move.endCol)

        # pawn promotion (apply promotionChoice if provided)
        if move.isPawnPromotion:
            promo = move.promotionChoice if move.promotionChoice else 'Q'
            self.board[move.endRow][move.endCol] = move.pieceMoved[0] + promo

        # en passant capture
        if move.isEnpassantMove:
            if move.pieceMoved[0] == 'w':
                self.board[move.endRow+1][move.endCol] = "--"
            else:
                self.board[move.endRow-1][move.endCol] = "--"

        # update enPassantPossible
        if move.pieceMoved[1] == 'p' and abs(move.startRow - move.endRow) == 2:
            self.enPassantPossible = ((move.startRow + move.endRow)//2, move.startCol)
        else:
            self.enPassantPossible = ()

        # castling rook move
        if move.isCastleMove:
            if move.endCol - move.startCol == 2:  # kingside
                self.board[move.endRow][move.endCol-1] = self.board[move.endRow][move.endCol+1]
                self.board[move.endRow][move.endCol+1] = "--"
            else:  # queenside
                self.board[move.endRow][move.endCol+1] = self.board[move.endRow][move.endCol-2]
                self.board[move.endRow][move.endCol-2] = "--"

        # update castling rights
        self.updateCastleRights(move)
        self.castleRightsLog.append(CastlingRights(self.currentCastlingRights.wks,
                                                   self.currentCastlingRights.bks,
                                                   self.currentCastlingRights.wqs,
                                                   self.currentCastlingRights.bqs))

        # toggle turn
        self.whiteToMove = not self.whiteToMove

    def undoMove(self):
        if not self.moveLog:
            return
        move = self.moveLog.pop()
        self.board[move.startRow][move.startCol] = move.pieceMoved
        self.board[move.endRow][move.endCol] = move.pieceCaptured
        self.whiteToMove = not self.whiteToMove

        # update king location back
        if move.pieceMoved == 'wK':
            self.whiteKingLocation = (move.startRow, move.startCol)
        elif move.pieceMoved == 'bK':
            self.blackKingLocation = (move.startRow, move.startCol)

        # undo en passant
        if move.isEnpassantMove:
            if move.pieceMoved[0] == 'w':
                self.board[move.endRow+1][move.endCol] = 'bp'
            else:
                self.board[move.endRow-1][move.endCol] = 'wp'
            self.board[move.endRow][move.endCol] = "--"

        # undo pawn promotion
        if move.isPawnPromotion:
            self.board[move.startRow][move.startCol] = move.pieceMoved[0] + 'p'
            self.board[move.endRow][move.endCol] = move.pieceCaptured

        # undo castling rook
        if move.isCastleMove:
            if move.endCol - move.startCol == 2:
                self.board[move.endRow][move.endCol+1] = self.board[move.endRow][move.endCol-1]
                self.board[move.endRow][move.endCol-1] = "--"
            else:
                self.board[move.endRow][move.endCol-2] = self.board[move.endRow][move.endCol+1]
                self.board[move.endRow][move.endCol+1] = "--"

        # restore castling rights and enPassantPossible
        self.castleRightsLog.pop()
        last = self.castleRightsLog[-1]
        self.currentCastlingRights = CastlingRights(last.wks, last.bks, last.wqs, last.bqs)

        if self.moveLog:
            lastMove = self.moveLog[-1]
            if lastMove.pieceMoved[1] == 'p' and abs(lastMove.startRow - lastMove.endRow) == 2:
                self.enPassantPossible = ((lastMove.startRow + lastMove.endRow)//2, lastMove.startCol)
            else:
                self.enPassantPossible = ()
        else:
            self.enPassantPossible = ()

    def getValidMoves(self):
        moves = []
        self.inCheck, self.pins, self.checks = self.checkForPinsAndChecks()
        moves = self.getAllPossibleMoves()
        legalMoves = []
        for m in moves:
            self.makeMove(m)
            self.inCheck, _, _ = self.checkForPinsAndChecks()
            if not self.inCheck:
                legalMoves.append(m)
            self.undoMove()
        return legalMoves
    


    def checkForPinsAndChecks(self):
        pins = []
        checks = []
        inCheck = False
        if self.whiteToMove:
            enemyColor = 'b'
            allyColor = 'w'
            startRow, startCol = self.whiteKingLocation
        else:
            enemyColor = 'w'
            allyColor = 'b'
            startRow, startCol = self.blackKingLocation

        directions = [(-1,0),(-1,1),(0,1),(1,1),(1,0),(1,-1),(0,-1),(-1,-1)]
        for j, d in enumerate(directions):
            possiblePin = ()
            for i in range(1,8):
                r = startRow + d[0]*i
                c = startCol + d[1]*i
                if 0 <= r < 8 and 0 <= c < 8:
                    piece = self.board[r][c]
                    if piece[0] == allyColor and piece[1] != 'K':
                        if possiblePin == ():
                            possiblePin = (r,c,d[0],d[1], piece)
                        else:
                            break
                    elif piece[0] == enemyColor:
                        pType = piece[1]
                        if (pType == 'R' and (d[0] == 0 or d[1] == 0)) or \
                           (pType == 'B' and (d[0] != 0 and d[1] != 0)) or \
                           (pType == 'Q'):
                            if possiblePin == ():
                                inCheck = True
                                checks.append((r,c,d[0],d[1]))
                                break
                            else:
                                pins.append(possiblePin)
                                break
                        else:
                            break
                else:
                    break

        # knight checks
        knightMoves = [(-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)]
        for m in knightMoves:
            r = startRow + m[0]
            c = startCol + m[1]
            if 0 <= r < 8 and 0 <= c < 8:
                piece = self.board[r][c]
                if piece[0] == enemyColor and piece[1] == 'N':
                    inCheck = True
                    checks.append((r,c,m[0],m[1]))

        # pawn checks
        if allyColor == 'w':
            pawnDirs = [(-1,-1),(-1,1)]
        else:
            pawnDirs = [(1,-1),(1,1)]
        for d in pawnDirs:
            r = startRow + d[0]
            c = startCol + d[1]
            if 0 <= r < 8 and 0 <= c < 8:
                piece = self.board[r][c]
                if piece[0] == enemyColor and piece[1] == 'p':
                    inCheck = True
                    checks.append((r,c,d[0],d[1]))

        return inCheck, pins, checks

    def isSquareAttacked(self, r, c, byColor):
        """
        Return True if square (r,c) is attacked by color 'w' or 'b'.
        This function checks pawn/knight/slider/king threats explicitly WITHOUT toggling turns.
        """
        # pawn attacks
        if byColor == 'w':
            pawnDirs = [(-1,-1), (-1,1)]
            for d in pawnDirs:
                rr = r + d[0]
                cc = c + d[1]
                if 0 <= rr < 8 and 0 <= cc < 8:
                    if self.board[rr][cc] == 'wp':
                        return True
        else:
            pawnDirs = [(1,-1), (1,1)]
            for d in pawnDirs:
                rr = r + d[0]
                cc = c + d[1]
                if 0 <= rr < 8 and 0 <= cc < 8:
                    if self.board[rr][cc] == 'bp':
                        return True

        # knight attacks
        knightMoves = [(-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)]
        for m in knightMoves:
            rr = r + m[0]
            cc = c + m[1]
            if 0 <= rr < 8 and 0 <= cc < 8:
                piece = self.board[rr][cc]
                if piece[0] == byColor and piece[1] == 'N':
                    return True

        # sliding pieces (rook, bishop, queen)
        directions_rook = [(-1,0),(0,1),(1,0),(0,-1)]
        directions_bishop = [(-1,-1),(-1,1),(1,1),(1,-1)]
        # rook/queen
        for d in directions_rook:
            for i in range(1,8):
                rr = r + d[0]*i
                cc = c + d[1]*i
                if 0 <= rr < 8 and 0 <= cc < 8:
                    piece = self.board[rr][cc]
                    if piece != "--":
                        if piece[0] == byColor and (piece[1] == 'R' or piece[1] == 'Q'):
                            return True
                        else:
                            break
                else:
                    break
        # bishop/queen
        for d in directions_bishop:
            for i in range(1,8):
                rr = r + d[0]*i
                cc = c + d[1]*i
                if 0 <= rr < 8 and 0 <= cc < 8:
                    piece = self.board[rr][cc]
                    if piece != "--":
                        if piece[0] == byColor and (piece[1] == 'B' or piece[1] == 'Q'):
                            return True
                        else:
                            break
                else:
                    break

        # king adjacency
        kingMoves = [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]
        for m in kingMoves:
            rr = r + m[0]
            cc = c + m[1]
            if 0 <= rr < 8 and 0 <= cc < 8:
                piece = self.board[rr][cc]
                if piece[0] == byColor and piece[1] == 'K':
                    return True

        return False

    def getAllPossibleMoves(self):
        moves = []
        for r in range(8):
            for c in range(8):
                turn = self.board[r][c][0]
                if (turn == 'w' and self.whiteToMove) or (turn == 'b' and not self.whiteToMove):
                    piece = self.board[r][c][1]
                    if piece == 'p':
                        self.getPawnMoves(r,c,moves)
                    elif piece == 'R':
                        self.getRookMoves(r,c,moves)
                    elif piece == 'N':
                        self.getKnightMoves(r,c,moves)
                    elif piece == 'B':
                        self.getBishopMoves(r,c,moves)
                    elif piece == 'Q':
                        self.getQueenMoves(r,c,moves)
                    elif piece == 'K':
                        self.getKingMoves(r,c,moves)
        return moves

    def getPawnMoves(self, r, c, moves):
        piece = self.board[r][c]
        color = piece[0]
        if color == 'w':
            if r-1 >= 0 and self.board[r-1][c] == "--":
                moves.append(Move((r,c),(r-1,c), self.board))
                if r == 6 and self.board[r-2][c] == "--":
                    moves.append(Move((r,c),(r-2,c), self.board))
            # captures
            if c-1 >= 0:
                if self.board[r-1][c-1][0] == 'b':
                    moves.append(Move((r,c),(r-1,c-1), self.board))
                if (r-1,c-1) == self.enPassantPossible:
                    moves.append(Move((r,c),(r-1,c-1), self.board, isEnpassantMove=True))
            if c+1 <=7:
                if self.board[r-1][c+1][0] == 'b':
                    moves.append(Move((r,c),(r-1,c+1), self.board))
                if (r-1,c+1) == self.enPassantPossible:
                    moves.append(Move((r,c),(r-1,c+1), self.board, isEnpassantMove=True))
        else:
            if r+1 <= 7 and self.board[r+1][c] == "--":
                moves.append(Move((r,c),(r+1,c), self.board))
                if r == 1 and self.board[r+2][c] == "--":
                    moves.append(Move((r,c),(r+2,c), self.board))
            if c-1 >= 0:
                if self.board[r+1][c-1][0] == 'w':
                    moves.append(Move((r,c),(r+1,c-1), self.board))
                if (r+1,c-1) == self.enPassantPossible:
                    moves.append(Move((r,c),(r+1,c-1), self.board, isEnpassantMove=True))
            if c+1 <=7:
                if self.board[r+1][c+1][0] == 'w':
                    moves.append(Move((r,c),(r+1,c+1), self.board))
                if (r+1,c+1) == self.enPassantPossible:
                    moves.append(Move((r,c),(r+1,c+1), self.board, isEnpassantMove=True))

    def getRookMoves(self, r, c, moves):
        directions = [(-1,0),(0,-1),(1,0),(0,1)]
        allyColor = 'w' if self.whiteToMove else 'b'
        enemyColor = 'b' if self.whiteToMove else 'w'
        for d in directions:
            for i in range(1,8):
                endRow = r + d[0]*i
                endCol = c + d[1]*i
                if 0 <= endRow < 8 and 0 <= endCol < 8:
                    endPiece = self.board[endRow][endCol]
                    if endPiece == "--":
                        moves.append(Move((r,c),(endRow,endCol), self.board))
                    elif endPiece[0] == enemyColor:
                        moves.append(Move((r,c),(endRow,endCol), self.board))
                        break
                    else:
                        break
                else:
                    break

    def getKnightMoves(self, r, c, moves):
        knightMoves = [(-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)]
        allyColor = 'w' if self.whiteToMove else 'b'
        for m in knightMoves:
            endRow = r + m[0]
            endCol = c + m[1]
            if 0 <= endRow < 8 and 0 <= endCol < 8:
                endPiece = self.board[endRow][endCol]
                if endPiece[0] != allyColor:
                    moves.append(Move((r,c),(endRow,endCol), self.board))

    def getBishopMoves(self, r, c, moves):
        directions = [(-1,-1),(-1,1),(1,-1),(1,1)]
        allyColor = 'w' if self.whiteToMove else 'b'
        enemyColor = 'b' if self.whiteToMove else 'w'
        for d in directions:
            for i in range(1,8):
                endRow = r + d[0]*i
                endCol = c + d[1]*i
                if 0 <= endRow < 8 and 0 <= endCol < 8:
                    endPiece = self.board[endRow][endCol]
                    if endPiece == "--":
                        moves.append(Move((r,c),(endRow,endCol), self.board))
                    elif endPiece[0] == enemyColor:
                        moves.append(Move((r,c),(endRow,endCol), self.board))
                        break
                    else:
                        break
                else:
                    break

    def getQueenMoves(self, r, c, moves):
        self.getRookMoves(r,c,moves)
        self.getBishopMoves(r,c,moves)

    def getKingMoves(self, r, c, moves):
        kingMoves = [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]
        allyColor = 'w' if self.whiteToMove else 'b'
        for m in kingMoves:
            endRow = r + m[0]
            endCol = c + m[1]
            if 0 <= endRow < 8 and 0 <= endCol < 8:
                endPiece = self.board[endRow][endCol]
                if endPiece[0] != allyColor:
                    moves.append(Move((r,c),(endRow,endCol), self.board))
        # castling using isSquareAttacked to check safety
        self.getCastleMoves(r,c,moves)

    def updateCastleRights(self, move):
        # Update castling rights whenever a king or rook moves
        if move.pieceMoved == 'wK':
            self.currentCastlingRights.wks = False
            self.currentCastlingRights.wqs = False
        elif move.pieceMoved == 'bK':
            self.currentCastlingRights.bks = False
            self.currentCastlingRights.bqs = False
        elif move.pieceMoved == 'wR':
            if move.startRow == 7:
                if move.startCol == 0:
                    self.currentCastlingRights.wqs = False
                elif move.startCol == 7:
                    self.currentCastlingRights.wks = False
        elif move.pieceMoved == 'bR':
            if move.startRow == 0:
                if move.startCol == 0:
                    self.currentCastlingRights.bqs = False
                elif move.startCol == 7:
                    self.currentCastlingRights.bks = False

        # If a rook is captured, update rights too
        if move.pieceCaptured == 'wR':
            if move.endRow == 7:
                if move.endCol == 0:
                    self.currentCastlingRights.wqs = False
                elif move.endCol == 7:
                    self.currentCastlingRights.wks = False
        elif move.pieceCaptured == 'bR':
            if move.endRow == 0:
                if move.endCol == 0:
                    self.currentCastlingRights.bqs = False
                elif move.endCol == 7:
                    self.currentCastlingRights.bks = False
    
    def getCastleMoves(self, r, c, moves):
        if self.inCheck:
            return
        if (self.whiteToMove and self.currentCastlingRights.wks) or (not self.whiteToMove and self.currentCastlingRights.bks):
            self.getKingsideCastleMoves(r,c,moves)
        if (self.whiteToMove and self.currentCastlingRights.wqs) or (not self.whiteToMove and self.currentCastlingRights.bqs):
            self.getQueensideCastleMoves(r,c,moves)

    def getKingsideCastleMoves(self, r, c, moves):
        if self.board[r][c+1] == "--" and self.board[r][c+2] == "--":
            if not self.isSquareAttacked(r, c+1, 'b' if self.whiteToMove else 'w') and not self.isSquareAttacked(r, c+2, 'b' if self.whiteToMove else 'w'):
                moves.append(Move((r,c),(r,c+2), self.board, isCastleMove=True))

    def getQueensideCastleMoves(self, r, c, moves):
        if self.board[r][c-1] == "--" and self.board[r][c-2] == "--" and self.board[r][c-3] == "--":
            if not self.isSquareAttacked(r, c-1, 'b' if self.whiteToMove else 'w') and not self.isSquareAttacked(r, c-2, 'b' if self.whiteToMove else 'w'):
                moves.append(Move((r,c),(r,c-2), self.board, isCastleMove=True))

    def isCheckmate(self):
        self.inCheck, self.pins, self.checks = self.checkForPinsAndChecks()
        return self.inCheck and len(self.getValidMoves()) == 0

    def isStalemate(self):
        self.inCheck, self.pins, self.checks = self.checkForPinsAndChecks()
        return (not self.inCheck) and len(self.getValidMoves()) == 0
