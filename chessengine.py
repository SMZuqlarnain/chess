# chessengine.py
# Correct and integrated chess engine core:
# - Legal move generation by simulation (no king capture)
# - En-passant, castling, pawn promotion (promotionChoice stored in Move)
# - makeMove / undoMove restore full state
# - Threefold repetition detection (positionCounts)
# - Non-recursive attack detection isSquareAttacked()

from copy import deepcopy

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
        self.isEnpassantMove = isEnpassantMove
        if isEnpassantMove:
            # captured pawn isn't on end square; notation stores it anyway
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
    def __init__(self, wks=True, bks=True, wqs=True, bqs=True):
        self.wks = wks
        self.bks = bks
        self.wqs = wqs
        self.bqs = bqs

class GameState:
    def __init__(self):
        # initial board
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
        # en passant target square (row, col) where a capture is allowed, or ()
        self.enPassantPossible = ()
        # castling rights & history for undo
        self.currentCastlingRights = CastlingRights(True, True, True, True)
        self.castleRightsLog = [CastlingRights(self.currentCastlingRights.wks,
                                               self.currentCastlingRights.bks,
                                               self.currentCastlingRights.wqs,
                                               self.currentCastlingRights.bqs)]
        # repetition tracking: map position-key -> count
        self.positionCounts = {}
        # record initial position
        key = self._positionKey()
        self.positionCounts[key] = 1

    # -------------------------
    # Make / undo and state ops
    # -------------------------
    def makeMove(self, move):
        """
        Execute a move and update all state (board, king locations, enPassantPossible,
        castling rights, positionCounts).
        """
        # move piece from start to end
        self.board[move.startRow][move.startCol] = "--"

        # en passant capture: remove pawn behind destination
        if move.isEnpassantMove:
            if move.pieceMoved[0] == 'w':
                # white captures black pawn below end square
                self.board[move.endRow + 1][move.endCol] = "--"
            else:
                self.board[move.endRow - 1][move.endCol] = "--"

        # normal capture or empty destination - place mover
        self.board[move.endRow][move.endCol] = move.pieceMoved

        # append to move log
        self.moveLog.append(move)

        # update king location if moved
        if move.pieceMoved == 'wK':
            self.whiteKingLocation = (move.endRow, move.endCol)
        elif move.pieceMoved == 'bK':
            self.blackKingLocation = (move.endRow, move.endCol)

        # pawn promotion: if promotionChoice set by caller, apply, else default to Q
        if move.isPawnPromotion:
            promo = move.promotionChoice if move.promotionChoice else 'Q'
            self.board[move.endRow][move.endCol] = move.pieceMoved[0] + promo

        # update enPassantPossible: only when pawn moves two squares
        if move.pieceMoved[1] == 'p' and abs(move.endRow - move.startRow) == 2:
            self.enPassantPossible = ((move.startRow + move.endRow)//2, move.startCol)
        else:
            self.enPassantPossible = ()

        # handle castling rook move
        if move.isCastleMove:
            if move.endCol - move.startCol == 2:
                # kingside: move rook from h to f
                self.board[move.endRow][move.endCol - 1] = self.board[move.endRow][move.endCol + 1]
                self.board[move.endRow][move.endCol + 1] = "--"
            else:
                # queenside: move rook from a to d
                self.board[move.endRow][move.endCol + 1] = self.board[move.endRow][move.endCol - 2]
                self.board[move.endRow][move.endCol - 2] = "--"

        # update castling rights based on move and push copy to log for undo
        self.updateCastleRights(move)
        self.castleRightsLog.append(CastlingRights(self.currentCastlingRights.wks,
                                                   self.currentCastlingRights.bks,
                                                   self.currentCastlingRights.wqs,
                                                   self.currentCastlingRights.bqs))

        # toggle side to move
        self.whiteToMove = not self.whiteToMove

        # update repetition map
        key = self._positionKey()
        self.positionCounts[key] = self.positionCounts.get(key, 0) + 1

    def undoMove(self):
        """
        Undo last move and restore all state (including positionCounts).
        """
        if not self.moveLog:
            return
        move = self.moveLog.pop()

        # move piece back
        self.board[move.startRow][move.startCol] = move.pieceMoved

        # handle en-passant undo: restore captured pawn behind destination
        if move.isEnpassantMove:
            # end square was empty; restore it to "--"
            self.board[move.endRow][move.endCol] = "--"
            if move.pieceMoved[0] == 'w':
                self.board[move.endRow + 1][move.endCol] = 'bp'
            else:
                self.board[move.endRow - 1][move.endCol] = 'wp'
        else:
            # restore captured piece (could be "--" if none)
            self.board[move.endRow][move.endCol] = move.pieceCaptured

        # restore king location if king moved
        if move.pieceMoved == 'wK':
            self.whiteKingLocation = (move.startRow, move.startCol)
        elif move.pieceMoved == 'bK':
            self.blackKingLocation = (move.startRow, move.startCol)

        # undo castling rook move if applicable
        if move.isCastleMove:
            if move.endCol - move.startCol == 2:
                # kingside: move rook back from f to h
                self.board[move.endRow][move.endCol + 1] = self.board[move.endRow][move.endCol - 1]
                self.board[move.endRow][move.endCol - 1] = "--"
            else:
                # queenside
                self.board[move.endRow][move.endCol - 2] = self.board[move.endRow][move.endCol + 1]
                self.board[move.endRow][move.endCol + 1] = "--"

        # undo pawn promotion: revert pawn on start square (note: piece at start already restored)
        if move.isPawnPromotion:
            self.board[move.startRow][move.startCol] = move.pieceMoved[0] + 'p'
            # captured piece already restored in end square above

        # pop castling rights log & restore
        self.castleRightsLog.pop()
        last = self.castleRightsLog[-1]
        self.currentCastlingRights = CastlingRights(last.wks, last.bks, last.wqs, last.bqs)

        # restore enPassantPossible from previous move if exists
        if self.moveLog:
            lastMove = self.moveLog[-1]
            if lastMove.pieceMoved[1] == 'p' and abs(lastMove.endRow - lastMove.startRow) == 2:
                self.enPassantPossible = ((lastMove.startRow + lastMove.endRow)//2, lastMove.startCol)
            else:
                self.enPassantPossible = ()
        else:
            self.enPassantPossible = ()

        # toggle turn back
        self.whiteToMove = not self.whiteToMove

        # decrement repetition count for restored position
        key = self._positionKey()
        if key in self.positionCounts:
            # decrement and delete if zero (keeps map tidy)
            self.positionCounts[key] -= 1
            if self.positionCounts[key] <= 0:
                del self.positionCounts[key]

    # -------------------------
    # Castling rights handling
    # -------------------------
    def updateCastleRights(self, move):
        """
        Update currentCastlingRights depending on what piece moved or was captured.
        """
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

        # if rook is captured, update rights
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

    # -------------------------
    # Attack detection (non-recursive)
    # -------------------------
    def isSquareAttacked(self, r, c, byColor):
        """
        Check whether square (r,c) is attacked by side byColor ('w' or 'b').
        Inspects board directly; does NOT call move generation (avoids recursion).
        """
        # Pawn attacks
        if byColor == 'w':
            for dr, dc in [(-1, -1), (-1, 1)]:
                rr, cc = r + dr, c + dc
                if 0 <= rr < 8 and 0 <= cc < 8 and self.board[rr][cc] == 'wp':
                    return True
        else:
            for dr, dc in [(1, -1), (1, 1)]:
                rr, cc = r + dr, c + dc
                if 0 <= rr < 8 and 0 <= cc < 8 and self.board[rr][cc] == 'bp':
                    return True

        # Knight attacks
        knightOffsets = [(-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)]
        for dr, dc in knightOffsets:
            rr, cc = r + dr, c + dc
            if 0 <= rr < 8 and 0 <= cc < 8:
                piece = self.board[rr][cc]
                if piece[0] == byColor and piece[1] == 'N':
                    return True

        # Sliding orthogonal - rook/queen
        for dr, dc in [(-1,0),(0,1),(1,0),(0,-1)]:
            for i in range(1,8):
                rr, cc = r + dr*i, c + dc*i
                if not (0 <= rr < 8 and 0 <= cc < 8):
                    break
                piece = self.board[rr][cc]
                if piece != "--":
                    if piece[0] == byColor and (piece[1] == 'R' or piece[1] == 'Q'):
                        return True
                    else:
                        break

        # Sliding diagonal - bishop/queen
        for dr, dc in [(-1,-1),(-1,1),(1,1),(1,-1)]:
            for i in range(1,8):
                rr, cc = r + dr*i, c + dc*i
                if not (0 <= rr < 8 and 0 <= cc < 8):
                    break
                piece = self.board[rr][cc]
                if piece != "--":
                    if piece[0] == byColor and (piece[1] == 'B' or piece[1] == 'Q'):
                        return True
                    else:
                        break

        # King adjacent
        for dr, dc in [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]:
            rr, cc = r + dr, c + dc
            if 0 <= rr < 8 and 0 <= cc < 8:
                piece = self.board[rr][cc]
                if piece[0] == byColor and piece[1] == 'K':
                    return True

        return False

    # -------------------------
    # Pseudo-legal move generation
    # -------------------------
    def getAllPossibleMoves(self):
        """
        Generate all pseudo-legal moves (ignoring checks). getValidMoves() will filter illegal ones.
        """
        moves = []
        for r in range(8):
            for c in range(8):
                piece = self.board[r][c]
                if piece == "--":
                    continue
                color = piece[0]
                if (color == 'w' and self.whiteToMove) or (color == 'b' and not self.whiteToMove):
                    pt = piece[1]
                    if pt == 'p':
                        self.getPawnMoves(r, c, moves)
                    elif pt == 'R':
                        self.getRookMoves(r, c, moves)
                    elif pt == 'N':
                        self.getKnightMoves(r, c, moves)
                    elif pt == 'B':
                        self.getBishopMoves(r, c, moves)
                    elif pt == 'Q':
                        self.getQueenMoves(r, c, moves)
                    elif pt == 'K':
                        self.getKingMoves(r, c, moves)
        return moves

    def getValidMoves(self):
        """
        Filter pseudo-legal moves by simulation: a move is legal only if the moving side's king is not attacked after the move.
        This guarantees the king is never capturable.
        """
        moves = self.getAllPossibleMoves()
        legal = []
        for m in moves:
            self.makeMove(m)
            # identify moving side's king (after makeMove whiteToMove toggled)
            movingSideIsWhite = not self.whiteToMove
            if movingSideIsWhite:
                kingPos = self.whiteKingLocation
                attacker = 'b'
            else:
                kingPos = self.blackKingLocation
                attacker = 'w'
            attacked = self.isSquareAttacked(kingPos[0], kingPos[1], attacker)
            if not attacked:
                legal.append(m)
            self.undoMove()
        return legal

    # -------------------------
    # Piece move generators (pseudo-legal)
    # -------------------------
    def getPawnMoves(self, r, c, moves):
        color = self.board[r][c][0]
        if color == 'w':
            # forward 1
            if r-1 >= 0 and self.board[r-1][c] == "--":
                moves.append(Move((r,c),(r-1,c), self.board))
                # forward 2
                if r == 6 and self.board[r-2][c] == "--":
                    moves.append(Move((r,c),(r-2,c), self.board))
            # captures
            for dc in (-1, 1):
                cc = c + dc
                rr = r - 1
                if 0 <= cc < 8 and rr >= 0:
                    if self.board[rr][cc][0] == 'b':
                        moves.append(Move((r,c),(rr,cc), self.board))
                    if (rr, cc) == self.enPassantPossible:
                        moves.append(Move((r,c),(rr,cc), self.board, isEnpassantMove=True))
        else:
            # black pawn
            if r+1 <= 7 and self.board[r+1][c] == "--":
                moves.append(Move((r,c),(r+1,c), self.board))
                if r == 1 and self.board[r+2][c] == "--":
                    moves.append(Move((r,c),(r+2,c), self.board))
            for dc in (-1, 1):
                cc = c + dc
                rr = r + 1
                if 0 <= cc < 8 and rr <= 7:
                    if self.board[rr][cc][0] == 'w':
                        moves.append(Move((r,c),(rr,cc), self.board))
                    if (rr, cc) == self.enPassantPossible:
                        moves.append(Move((r,c),(rr,cc), self.board, isEnpassantMove=True))

    def getRookMoves(self, r, c, moves):
        directions = [(-1,0),(0,1),(1,0),(0,-1)]
        ally = 'w' if self.whiteToMove else 'b'
        enemy = 'b' if self.whiteToMove else 'w'
        for dr, dc in directions:
            for i in range(1,8):
                rr, cc = r + dr*i, c + dc*i
                if not (0 <= rr < 8 and 0 <= cc < 8):
                    break
                end = self.board[rr][cc]
                if end == "--":
                    moves.append(Move((r,c),(rr,cc), self.board))
                elif end[0] == enemy:
                    moves.append(Move((r,c),(rr,cc), self.board))
                    break
                else:
                    break

    def getKnightMoves(self, r, c, moves):
        knightOffsets = [(-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)]
        ally = 'w' if self.whiteToMove else 'b'
        for dr, dc in knightOffsets:
            rr, cc = r + dr, c + dc
            if 0 <= rr < 8 and 0 <= cc < 8:
                end = self.board[rr][cc]
                if end == "--" or end[0] != ally:
                    moves.append(Move((r,c),(rr,cc), self.board))

    def getBishopMoves(self, r, c, moves):
        directions = [(-1,-1),(-1,1),(1,1),(1,-1)]
        ally = 'w' if self.whiteToMove else 'b'
        enemy = 'b' if self.whiteToMove else 'w'
        for dr, dc in directions:
            for i in range(1,8):
                rr, cc = r + dr*i, c + dc*i
                if not (0 <= rr < 8 and 0 <= cc < 8):
                    break
                end = self.board[rr][cc]
                if end == "--":
                    moves.append(Move((r,c),(rr,cc), self.board))
                elif end[0] == enemy:
                    moves.append(Move((r,c),(rr,cc), self.board))
                    break
                else:
                    break

    def getQueenMoves(self, r, c, moves):
        self.getRookMoves(r, c, moves)
        self.getBishopMoves(r, c, moves)

    def getKingMoves(self, r, c, moves):
        kingOffsets = [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]
        ally = 'w' if self.whiteToMove else 'b'
        for dr, dc in kingOffsets:
            rr, cc = r + dr, c + dc
            if 0 <= rr < 8 and 0 <= cc < 8:
                end = self.board[rr][cc]
                if end == "--" or end[0] != ally:
                    moves.append(Move((r,c),(rr,cc), self.board))
        # castling (checks safety using isSquareAttacked)
        self.getCastleMoves(r, c, moves)

    def getCastleMoves(self, r, c, moves):
        inCheck, _, _ = self.checkForPinsAndChecks()
        if inCheck:
            return
        if self.whiteToMove:
            attacker = 'b'
            if self.currentCastlingRights.wks:
                if self.board[r][c+1] == "--" and self.board[r][c+2] == "--":
                    if not self.isSquareAttacked(r, c+1, attacker) and not self.isSquareAttacked(r, c+2, attacker):
                        moves.append(Move((r,c),(r,c+2), self.board, isCastleMove=True))
            if self.currentCastlingRights.wqs:
                if self.board[r][c-1] == "--" and self.board[r][c-2] == "--" and self.board[r][c-3] == "--":
                    if not self.isSquareAttacked(r, c-1, attacker) and not self.isSquareAttacked(r, c-2, attacker):
                        moves.append(Move((r,c),(r,c-2), self.board, isCastleMove=True))
        else:
            attacker = 'w'
            if self.currentCastlingRights.bks:
                if self.board[r][c+1] == "--" and self.board[r][c+2] == "--":
                    if not self.isSquareAttacked(r, c+1, attacker) and not self.isSquareAttacked(r, c+2, attacker):
                        moves.append(Move((r,c),(r,c+2), self.board, isCastleMove=True))
            if self.currentCastlingRights.bqs:
                if self.board[r][c-1] == "--" and self.board[r][c-2] == "--" and self.board[r][c-3] == "--":
                    if not self.isSquareAttacked(r, c-1, attacker) and not self.isSquareAttacked(r, c-2, attacker):
                        moves.append(Move((r,c),(r,c-2), self.board, isCastleMove=True))

    # -------------------------
    # Check/pins detection (helper)
    # -------------------------
    def checkForPinsAndChecks(self):
        """
        Return (inCheck, pins, checks) for side to move.
        Pins & checks info can be used by advanced move gen; we keep for UI and evaluation.
        """
        inCheck = False
        pins = []
        checks = []
        if self.whiteToMove:
            ally = 'w'; enemy = 'b'
            kingRow, kingCol = self.whiteKingLocation
        else:
            ally = 'b'; enemy = 'w'
            kingRow, kingCol = self.blackKingLocation

        directions = [(-1,0),(-1,1),(0,1),(1,1),(1,0),(1,-1),(0,-1),(-1,-1)]
        for dr, dc in directions:
            possiblePin = ()
            for i in range(1,8):
                rr, cc = kingRow + dr*i, kingCol + dc*i
                if not (0 <= rr < 8 and 0 <= cc < 8):
                    break
                piece = self.board[rr][cc]
                if piece[0] == ally and piece[1] != 'K':
                    if possiblePin == ():
                        possiblePin = (rr, cc, dr, dc, piece)
                    else:
                        break
                elif piece[0] == enemy:
                    pType = piece[1]
                    if (pType == 'R' and (dr == 0 or dc == 0)) or (pType == 'B' and (dr != 0 and dc != 0)) or (pType == 'Q'):
                        if possiblePin == ():
                            inCheck = True
                            checks.append((rr, cc, dr, dc))
                            break
                        else:
                            pins.append(possiblePin)
                            break
                    else:
                        break

        # knight checks
        knights = [(-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)]
        for dr, dc in knights:
            rr, cc = kingRow + dr, kingCol + dc
            if 0 <= rr < 8 and 0 <= cc < 8:
                piece = self.board[rr][cc]
                if piece[0] == enemy and piece[1] == 'N':
                    inCheck = True
                    checks.append((rr, cc, dr, dc))

        # pawn checks
        if ally == 'w':
            pawnDirs = [(-1,-1), (-1,1)]
        else:
            pawnDirs = [(1,-1), (1,1)]
        for dr, dc in pawnDirs:
            rr, cc = kingRow + dr, kingCol + dc
            if 0 <= rr < 8 and 0 <= cc < 8:
                piece = self.board[rr][cc]
                if piece[0] == enemy and piece[1] == 'p':
                    inCheck = True
                    checks.append((rr, cc, dr, dc))

        return inCheck, pins, checks

    # -------------------------
    # Draw detection: threefold repetition
    # -------------------------
    def _positionKey(self):
        """
        Return a hashable key representing the current position for repetition detection.
        Includes:
          - board squares (flattened)
          - side to move
          - castling rights
          - enPassantPossible square
        (Does NOT include move clocks; this suffices for threefold detection.)
        """
        flat = tuple(item for row in self.board for item in row)
        side = 'w' if self.whiteToMove else 'b'
        castle = (self.currentCastlingRights.wks, self.currentCastlingRights.wqs,
                  self.currentCastlingRights.bks, self.currentCastlingRights.bqs)
        ep = self.enPassantPossible if self.enPassantPossible else ()
        return (flat, side, castle, ep)

    def isThreefoldRepetition(self):
        """
        Return True if current position has occurred at least 3 times.
        """
        key = self._positionKey()
        return self.positionCounts.get(key, 0) >= 3

    # -------------------------
    # Convenience checks
    # -------------------------
    def isCheckmate(self):
        inCheck, _, _ = self.checkForPinsAndChecks()
        if inCheck and len(self.getValidMoves()) == 0:
            return True
        return False

    def isStalemate(self):
        inCheck, _, _ = self.checkForPinsAndChecks()
        if (not inCheck) and len(self.getValidMoves()) == 0:
            return True
        return False
