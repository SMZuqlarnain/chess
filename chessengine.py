# chessengine.py
# Solid, self-contained chess rules engine.
# Supports: en-passant, castling, promotion, check detection, pins, legal-move filtering.

class Move:
    ranksToRows = {"1":7,"2":6,"3":5,"4":4,"5":3,"6":2,"7":1,"8":0}
    rowsToRanks = {v:k for k,v in ranksToRows.items()}
    filesToCols = {"a":0,"b":1,"c":2,"d":3,"e":4,"f":5,"g":6,"h":7}
    colsToFiles = {v:k for k,v in filesToCols.items()}

    def __init__(self, startSq, endSq, board, pieceMoved=None, pieceCaptured=None,
                 isEnpassantMove=False, isCastleMove=False, promotionChoice=None):
        self.startRow = startSq[0]
        self.startCol = startSq[1]
        self.endRow = endSq[0]
        self.endCol = endSq[1]
        self.pieceMoved = pieceMoved if pieceMoved else board[self.startRow][self.startCol]
        # if capturing en-passant, captured pawn is not on end square
        self.isEnpassantMove = isEnpassantMove
        if isEnpassantMove:
            # pieceCaptured set later when executing move, but for notation set appropriately
            self.pieceCaptured = 'bp' if self.pieceMoved[0] == 'w' else 'wp'
        else:
            self.pieceCaptured = pieceCaptured if pieceCaptured else board[self.endRow][self.endCol]
        self.isPawnPromotion = (self.pieceMoved[1] == 'p' and (self.endRow == 0 or self.endRow == 7))
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
        # Board: 8x8 list of strings, e.g. "wK", "bp", "--"
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
        self.enPassantPossible = ()  # square where en-passant capture is possible (row,col)
        self.currentCastlingRights = CastlingRights(True, True, True, True)
        self.castleRightsLog = [CastlingRights(self.currentCastlingRights.wks,
                                               self.currentCastlingRights.bks,
                                               self.currentCastlingRights.wqs,
                                               self.currentCastlingRights.bqs)]

    #
    # Move execution and undo
    #
    def makeMove(self, move):
        # Save a snapshot of necessary state if needed (castle rights log handles castle rights)
        # Execute the move
        self.board[move.startRow][move.startCol] = "--"
        # If en-passant, captured pawn is behind the destination
        if move.isEnpassantMove:
            if move.pieceMoved[0] == 'w':
                # white captures black pawn that is one row below destination
                captured_row = move.endRow + 1
                self.board[captured_row][move.endCol] = "--"
            else:
                captured_row = move.endRow - 1
                self.board[captured_row][move.endCol] = "--"
        # Normal capture (or empty)
        self.board[move.endRow][move.endCol] = move.pieceMoved

        self.moveLog.append(move)

        # update king location if moved
        if move.pieceMoved == 'wK':
            self.whiteKingLocation = (move.endRow, move.endCol)
        elif move.pieceMoved == 'bK':
            self.blackKingLocation = (move.endRow, move.endCol)

        # pawn promotion: if promotionChoice present, use it; else will be handled by caller or auto to Q
        if move.isPawnPromotion:
            promo = move.promotionChoice if move.promotionChoice else 'Q'
            self.board[move.endRow][move.endCol] = move.pieceMoved[0] + promo

        # update enPassantPossible
        if move.pieceMoved[1] == 'p' and abs(move.startRow - move.endRow) == 2:
            # square behind the pawn (where an opposing pawn could capture en-passant)
            self.enPassantPossible = ((move.startRow + move.endRow)//2, move.startCol)
        else:
            self.enPassantPossible = ()

        # handle castling rook move
        if move.isCastleMove:
            # kingside
            if move.endCol - move.startCol == 2:
                self.board[move.endRow][move.endCol-1] = self.board[move.endRow][move.endCol+1]
                self.board[move.endRow][move.endCol+1] = "--"
            else:  # queenside
                self.board[move.endRow][move.endCol+1] = self.board[move.endRow][move.endCol-2]
                self.board[move.endRow][move.endCol-2] = "--"

        # update castling rights based on move
        self.updateCastleRights(move)
        # push copy of castling rights
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
        # put pieces back
        self.board[move.startRow][move.startCol] = move.pieceMoved
        # if en-passant, restored captured pawn behind destination
        if move.isEnpassantMove:
            self.board[move.endRow][move.endCol] = "--"
            if move.pieceMoved[0] == 'w':
                self.board[move.endRow+1][move.endCol] = 'bp'
            else:
                self.board[move.endRow-1][move.endCol] = 'wp'
        else:
            self.board[move.endRow][move.endCol] = move.pieceCaptured

        # restore king location if moved
        if move.pieceMoved == 'wK':
            self.whiteKingLocation = (move.startRow, move.startCol)
        elif move.pieceMoved == 'bK':
            self.blackKingLocation = (move.startRow, move.startCol)

        # undo castling rook move
        if move.isCastleMove:
            if move.endCol - move.startCol == 2:
                # kingside
                self.board[move.endRow][move.endCol+1] = self.board[move.endRow][move.endCol-1]
                self.board[move.endRow][move.endCol-1] = "--"
            else:
                self.board[move.endRow][move.endCol-2] = self.board[move.endRow][move.endCol+1]
                self.board[move.endRow][move.endCol+1] = "--"

        # undo pawn promotion
        if move.isPawnPromotion:
            # revert promoted piece back to pawn
            self.board[move.startRow][move.startCol] = move.pieceMoved[0] + 'p'
            # captured piece already restored above

        # restore castling rights and enPassantPossible from logs
        self.castleRightsLog.pop()
        last = self.castleRightsLog[-1]
        self.currentCastlingRights = CastlingRights(last.wks, last.bks, last.wqs, last.bqs)

        # restore enPassantPossible from previous move if any
        if self.moveLog:
            lastMove = self.moveLog[-1]
            if lastMove.pieceMoved[1] == 'p' and abs(lastMove.startRow - lastMove.endRow) == 2:
                self.enPassantPossible = ((lastMove.startRow + lastMove.endRow)//2, lastMove.startCol)
            else:
                self.enPassantPossible = ()
        else:
            self.enPassantPossible = ()

        # toggle turn back
        self.whiteToMove = not self.whiteToMove

    def updateCastleRights(self, move):
        # King move removes both rights for that color
        if move.pieceMoved == 'wK':
            self.currentCastlingRights.wks = False
            self.currentCastlingRights.wqs = False
        elif move.pieceMoved == 'bK':
            self.currentCastlingRights.bks = False
            self.currentCastlingRights.bqs = False
        # Rook moves remove corresponding rights
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
        # Rook captured removes corresponding rights
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

    #
    # Move generation and legality checking
    #
    def getValidMoves(self):
        """
        Return list of legal moves (moves that don't leave own king in check).
        Uses checkForPinsAndChecks to compute pins/checks for current side.
        """
        moves = []
        self.inCheck, self.pins, self.checks = self.checkForPinsAndChecks()
        allMoves = self.getAllPossibleMoves()
        # Filter: simulate each move and ensure own king not attacked
        legalMoves = []
        for m in allMoves:
            self.makeMove(m)
            # after making the move, check whether own king is in check
            if self.whiteToMove:
                # if it's now white's turn after toggling, we need to check black's attack on white king? careful:
                # We toggled whiteToMove in makeMove; so to see if the side who moved (previously) is safe,
                # check whether their king is attacked by opponent (which is current side).
                # Simpler: compute checkForPinsAndChecks (it uses whiteToMove) and see if inCheck is True for side to move;
                # but we want to know if the side that just moved (not the current whiteToMove) is left in check.
                inCheckNow, _, _ = self.checkForPinsAndChecks()
                # since whiteToMove has toggled, inCheckNow tells if the player to move (opponent) is in check,
                # not what we want. So instead check isSquareAttacked on the moving side's king.
                movingSideKing = self.whiteKingLocation if not self.whiteToMove else self.blackKingLocation
                attackerColor = 'b' if not self.whiteToMove else 'w'
                attacked = self.isSquareAttacked(movingSideKing[0], movingSideKing[1], attackerColor)
                if not attacked:
                    legalMoves.append(m)
            else:
                movingSideKing = self.whiteKingLocation if not self.whiteToMove else self.blackKingLocation
                attackerColor = 'b' if not self.whiteToMove else 'w'
                attacked = self.isSquareAttacked(movingSideKing[0], movingSideKing[1], attackerColor)
                if not attacked:
                    legalMoves.append(m)
            self.undoMove()
        return legalMoves

    def checkForPinsAndChecks(self):
        """
        Return (inCheck, pins, checks) for the side to move.
        pins: list of pinned piece info tuples (r,c,dir_r,dir_c,piece)
        checks: list of checking piece info tuples (r,c,dir_r,dir_c)
        """
        pins = []
        checks = []
        inCheck = False
        if self.whiteToMove:
            allyColor = 'w'
            enemyColor = 'b'
            startRow, startCol = self.whiteKingLocation
        else:
            allyColor = 'b'
            enemyColor = 'w'
            startRow, startCol = self.blackKingLocation

        # directions to look for sliders
        directions = [(-1,0),(-1,1),(0,1),(1,1),(1,0),(1,-1),(0,-1),(-1,-1)]
        for j, d in enumerate(directions):
            possiblePin = ()
            for i in range(1,8):
                rr = startRow + d[0]*i
                cc = startCol + d[1]*i
                if 0 <= rr < 8 and 0 <= cc < 8:
                    piece = self.board[rr][cc]
                    if piece[0] == allyColor and piece[1] != 'K':
                        if possiblePin == ():
                            possiblePin = (rr, cc, d[0], d[1], piece)
                        else:
                            break
                    elif piece[0] == enemyColor:
                        pType = piece[1]
                        # orthogonal rook/queen or diagonal bishop/queen
                        if (pType == 'R' and (d[0] == 0 or d[1] == 0)) or \
                           (pType == 'B' and (d[0] != 0 and d[1] != 0)) or \
                           (pType == 'Q'):
                            if possiblePin == ():
                                inCheck = True
                                checks.append((rr, cc, d[0], d[1]))
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
            rr = startRow + m[0]
            cc = startCol + m[1]
            if 0 <= rr < 8 and 0 <= cc < 8:
                piece = self.board[rr][cc]
                if piece[0] == enemyColor and piece[1] == 'N':
                    inCheck = True
                    checks.append((rr, cc, m[0], m[1]))

        # pawn checks
        if allyColor == 'w':
            pawnDirs = [(-1,-1), (-1,1)]
        else:
            pawnDirs = [(1,-1), (1,1)]
        for d in pawnDirs:
            rr = startRow + d[0]
            cc = startCol + d[1]
            if 0 <= rr < 8 and 0 <= cc < 8:
                piece = self.board[rr][cc]
                if piece[0] == enemyColor and piece[1] == 'p':
                    inCheck = True
                    checks.append((rr, cc, d[0], d[1]))

        return inCheck, pins, checks

    def isSquareAttacked(self, r, c, byColor):
        """
        Return True if square (r,c) is attacked by color 'w' or 'b'.
        This checks pawn, knight, sliding (rook,bishop,queen), and king attacks directly.
        Does NOT toggle whiteToMove or call move generation (avoids recursion).
        """
        # Pawn attacks
        if byColor == 'w':
            pawnDirs = [(-1,-1), (-1,1)]
            for d in pawnDirs:
                rr = r + d[0]; cc = c + d[1]
                if 0 <= rr < 8 and 0 <= cc < 8 and self.board[rr][cc] == 'wp':
                    return True
        else:
            pawnDirs = [(1,-1), (1,1)]
            for d in pawnDirs:
                rr = r + d[0]; cc = c + d[1]
                if 0 <= rr < 8 and 0 <= cc < 8 and self.board[rr][cc] == 'bp':
                    return True

        # Knight attacks
        knightMoves = [(-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)]
        for m in knightMoves:
            rr = r + m[0]; cc = c + m[1]
            if 0 <= rr < 8 and 0 <= cc < 8:
                piece = self.board[rr][cc]
                if piece[0] == byColor and piece[1] == 'N':
                    return True

        # Sliding pieces: rook/queen (orthogonal)
        directions_rook = [(-1,0),(0,1),(1,0),(0,-1)]
        for d in directions_rook:
            for i in range(1,8):
                rr = r + d[0]*i; cc = c + d[1]*i
                if not (0 <= rr < 8 and 0 <= cc < 8):
                    break
                piece = self.board[rr][cc]
                if piece != "--":
                    if piece[0] == byColor and (piece[1] == 'R' or piece[1] == 'Q'):
                        return True
                    else:
                        break

        # Bishop/queen (diagonals)
        directions_bishop = [(-1,-1),(-1,1),(1,1),(1,-1)]
        for d in directions_bishop:
            for i in range(1,8):
                rr = r + d[0]*i; cc = c + d[1]*i
                if not (0 <= rr < 8 and 0 <= cc < 8):
                    break
                piece = self.board[rr][cc]
                if piece != "--":
                    if piece[0] == byColor and (piece[1] == 'B' or piece[1] == 'Q'):
                        return True
                    else:
                        break

        # King adjacency
        kingMoves = [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]
        for k in kingMoves:
            rr = r + k[0]; cc = c + k[1]
            if 0 <= rr < 8 and 0 <= cc < 8:
                piece = self.board[rr][cc]
                if piece[0] == byColor and piece[1] == 'K':
                    return True

        return False

    #
    # Generate all possible moves without considering checks (used as base)
    #
    def getAllPossibleMoves(self):
        moves = []
        for r in range(8):
            for c in range(8):
                piece = self.board[r][c]
                if piece == "--":
                    continue
                color = piece[0]
                if (color == 'w' and self.whiteToMove) or (color == 'b' and not self.whiteToMove):
                    pType = piece[1]
                    if pType == 'p':
                        self.getPawnMoves(r, c, moves)
                    elif pType == 'R':
                        self.getRookMoves(r, c, moves)
                    elif pType == 'N':
                        self.getKnightMoves(r, c, moves)
                    elif pType == 'B':
                        self.getBishopMoves(r, c, moves)
                    elif pType == 'Q':
                        self.getQueenMoves(r, c, moves)
                    elif pType == 'K':
                        self.getKingMoves(r, c, moves)
        return moves

    def getPawnMoves(self, r, c, moves):
        piece = self.board[r][c]
        color = piece[0]
        if color == 'w':
            # single forward
            if r-1 >= 0 and self.board[r-1][c] == "--":
                moves.append(Move((r,c),(r-1,c), self.board))
                # double
                if r == 6 and self.board[r-2][c] == "--":
                    moves.append(Move((r,c),(r-2,c), self.board))
            # captures
            if c-1 >= 0:
                if self.board[r-1][c-1][0] == 'b':
                    moves.append(Move((r,c),(r-1,c-1), self.board))
                if (r-1,c-1) == self.enPassantPossible:
                    moves.append(Move((r,c),(r-1,c-1), self.board, isEnpassantMove=True))
            if c+1 <= 7:
                if self.board[r-1][c+1][0] == 'b':
                    moves.append(Move((r,c),(r-1,c+1), self.board))
                if (r-1,c+1) == self.enPassantPossible:
                    moves.append(Move((r,c),(r-1,c+1), self.board, isEnpassantMove=True))
        else:  # black pawn
            if r+1 <= 7 and self.board[r+1][c] == "--":
                moves.append(Move((r,c),(r+1,c), self.board))
                if r == 1 and self.board[r+2][c] == "--":
                    moves.append(Move((r,c),(r+2,c), self.board))
            if c-1 >= 0:
                if self.board[r+1][c-1][0] == 'w':
                    moves.append(Move((r,c),(r+1,c-1), self.board))
                if (r+1,c-1) == self.enPassantPossible:
                    moves.append(Move((r,c),(r+1,c-1), self.board, isEnpassantMove=True))
            if c+1 <= 7:
                if self.board[r+1][c+1][0] == 'w':
                    moves.append(Move((r,c),(r+1,c+1), self.board))
                if (r+1,c+1) == self.enPassantPossible:
                    moves.append(Move((r,c),(r+1,c+1), self.board, isEnpassantMove=True))

    def getRookMoves(self, r, c, moves):
        directions = [(-1,0),(0,1),(1,0),(0,-1)]
        allyColor = 'w' if self.whiteToMove else 'b'
        enemyColor = 'b' if self.whiteToMove else 'w'
        for d in directions:
            for i in range(1,8):
                rr = r + d[0]*i
                cc = c + d[1]*i
                if 0 <= rr < 8 and 0 <= cc < 8:
                    endPiece = self.board[rr][cc]
                    if endPiece == "--":
                        moves.append(Move((r,c),(rr,cc), self.board))
                    elif endPiece[0] == enemyColor:
                        moves.append(Move((r,c),(rr,cc), self.board))
                        break
                    else:
                        break
                else:
                    break

    def getKnightMoves(self, r, c, moves):
        knightMoves = [(-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)]
        allyColor = 'w' if self.whiteToMove else 'b'
        for m in knightMoves:
            rr = r + m[0]; cc = c + m[1]
            if 0 <= rr < 8 and 0 <= cc < 8:
                endPiece = self.board[rr][cc]
                if endPiece == "--" or endPiece[0] != allyColor:
                    moves.append(Move((r,c),(rr,cc), self.board))

    def getBishopMoves(self, r, c, moves):
        directions = [(-1,-1),(-1,1),(1,1),(1,-1)]
        allyColor = 'w' if self.whiteToMove else 'b'
        enemyColor = 'b' if self.whiteToMove else 'w'
        for d in directions:
            for i in range(1,8):
                rr = r + d[0]*i; cc = c + d[1]*i
                if 0 <= rr < 8 and 0 <= cc < 8:
                    endPiece = self.board[rr][cc]
                    if endPiece == "--":
                        moves.append(Move((r,c),(rr,cc), self.board))
                    elif endPiece[0] == enemyColor:
                        moves.append(Move((r,c),(rr,cc), self.board))
                        break
                    else:
                        break
                else:
                    break

    def getQueenMoves(self, r, c, moves):
        self.getRookMoves(r, c, moves)
        self.getBishopMoves(r, c, moves)

    def getKingMoves(self, r, c, moves):
        kingMoves = [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]
        allyColor = 'w' if self.whiteToMove else 'b'
        for m in kingMoves:
            rr = r + m[0]; cc = c + m[1]
            if 0 <= rr < 8 and 0 <= cc < 8:
                endPiece = self.board[rr][cc]
                if endPiece == "--" or endPiece[0] != allyColor:
                    moves.append(Move((r,c),(rr,cc), self.board))
        # castling
        self.getCastleMoves(r, c, moves)

    def getCastleMoves(self, r, c, moves):
        if self.inCheck:
            return
        if (self.whiteToMove and self.currentCastlingRights.wks) or (not self.whiteToMove and self.currentCastlingRights.bks):
            self.getKingsideCastleMoves(r, c, moves)
        if (self.whiteToMove and self.currentCastlingRights.wqs) or (not self.whiteToMove and self.currentCastlingRights.bqs):
            self.getQueensideCastleMoves(r, c, moves)

    def getKingsideCastleMoves(self, r, c, moves):
        # ensure squares between king and rook are empty and not attacked
        if self.board[r][c+1] == "--" and self.board[r][c+2] == "--":
            attackerColor = 'b' if self.whiteToMove else 'w'
            if (not self.isSquareAttacked(r, c+1, attackerColor)) and (not self.isSquareAttacked(r, c+2, attackerColor)):
                moves.append(Move((r,c),(r,c+2), self.board, isCastleMove=True))

    def getQueensideCastleMoves(self, r, c, moves):
        if self.board[r][c-1] == "--" and self.board[r][c-2] == "--" and self.board[r][c-3] == "--":
            attackerColor = 'b' if self.whiteToMove else 'w'
            if (not self.isSquareAttacked(r, c-1, attackerColor)) and (not self.isSquareAttacked(r, c-2, attackerColor)):
                moves.append(Move((r,c),(r,c-2), self.board, isCastleMove=True))

    #
    # Convenience checks
    #
    def isCheckmate(self):
        self.inCheck, self.pins, self.checks = self.checkForPinsAndChecks()
        return self.inCheck and len(self.getValidMoves()) == 0

    def isStalemate(self):
        self.inCheck, self.pins, self.checks = self.checkForPinsAndChecks()
        return (not self.inCheck) and len(self.getValidMoves()) == 0
