# main.py
# Pygame UI + tkinter popups for promotion choice and move history (undo/redo)
# Highlights legal moves and turns the king's square reddish when in check.
# Default AI_DEPTH = 5 (user-changeable with 'd' key).

import pygame as p
import sys, random
from chessengine import GameState, Move
import movefinder
import tkinter as tk
from tkinter import simpledialog

# Player control flags (change these variables)
White = True    # True => human controls white; False => AI controls white
Black = False   # True => human controls black; False => AI controls black

AI_DEPTH = 1  # default depth (plies)

# UI constants
WIDTH = HEIGHT = 640
DIMENSION = 8
SQ_SIZE = HEIGHT // DIMENSION
MAX_FPS = 30
IMAGES = {}

redo_stack = []

def loadImages():
    pieces = ['wp','wR','wN','wB','wQ','wK','bp','bR','bN','bB','bQ','bK']
    for piece in pieces:
        IMAGES[piece] = p.transform.scale(p.image.load("images/" + piece + ".png"), (SQ_SIZE, SQ_SIZE))

def askPromotionChoice():
    root = tk.Tk()
    root.withdraw()
    dlg = tk.Toplevel(root)
    dlg.title("Promote pawn to...")
    dlg.resizable(False, False)
    choice = {'val': None}
    def set_choice(ch):
        choice['val'] = ch
        dlg.destroy()
        root.quit()
    btnQ = tk.Button(dlg, text="Queen (Q)", width=12, command=lambda: set_choice('Q'))
    btnR = tk.Button(dlg, text="Rook (R)", width=12, command=lambda: set_choice('R'))
    btnB = tk.Button(dlg, text="Bishop (B)", width=12, command=lambda: set_choice('B'))
    btnN = tk.Button(dlg, text="Knight (N)", width=12, command=lambda: set_choice('N'))
    btnQ.grid(row=0, column=0, padx=8, pady=8)
    btnR.grid(row=0, column=1, padx=8, pady=8)
    btnB.grid(row=1, column=0, padx=8, pady=8)
    btnN.grid(row=1, column=1, padx=8, pady=8)
    dlg.update_idletasks()
    w = dlg.winfo_width(); h = dlg.winfo_height()
    x = (dlg.winfo_screenwidth()//2)-(w//2); y = (dlg.winfo_screenheight()//2)-(h//2)
    dlg.geometry(f"+{x}+{y}")
    root.mainloop()
    root.destroy()
    return choice['val']

def showMoveHistoryPopup(gs, apply_undo, apply_redo):
    root = tk.Tk()
    root.title("Move History")
    root.geometry("360x420")
    root.resizable(False, False)
    listbox = tk.Listbox(root, width=48, height=18)
    listbox.pack(padx=8, pady=8, expand=False)
    for idx, move in enumerate(gs.moveLog):
        listbox.insert(tk.END, f"{idx+1}. {move.getChessNotation()}")
    btnFrame = tk.Frame(root)
    btnFrame.pack(pady=6)
    def undo_action():
        apply_undo()
        listbox.delete(0, tk.END)
        for idx, move in enumerate(gs.moveLog):
            listbox.insert(tk.END, f"{idx+1}. {move.getChessNotation()}")
    def redo_action():
        apply_redo()
        listbox.delete(0, tk.END)
        for idx, move in enumerate(gs.moveLog):
            listbox.insert(tk.END, f"{idx+1}. {move.getChessNotation()}")
    btnUndo = tk.Button(btnFrame, text="Undo", width=10, command=undo_action)
    btnRedo = tk.Button(btnFrame, text="Redo", width=10, command=redo_action)
    btnClose = tk.Button(root, text="Close", width=10, command=root.destroy)
    btnUndo.grid(row=0, column=0, padx=6)
    btnRedo.grid(row=0, column=1, padx=6)
    btnClose.pack(pady=6)
    root.update_idletasks()
    w = root.winfo_width(); h = root.winfo_height()
    x = (root.winfo_screenwidth()//2)-(w//2); y = (root.winfo_screenheight()//2)-(h//2)
    root.geometry(f"+{x}+{y}")
    root.mainloop()
    root.destroy()

def main():
    global AI_DEPTH, redo_stack
    p.init()
    screen = p.display.set_mode((WIDTH, HEIGHT))
    p.display.set_caption("Chess - NegaMax + AlphaBeta (Depth adjustable)")
    clock = p.time.Clock()
    gs = GameState()
    validMoves = gs.getValidMoves()
    loadImages()
    sqSelected = ()
    playerClicks = []
    moveMade = False
    redo_stack = []

    while True:
        humanTurn = (gs.whiteToMove and White) or (not gs.whiteToMove and Black)
        for e in p.event.get():
            if e.type == p.QUIT:
                p.quit(); sys.exit()
            elif e.type == p.MOUSEBUTTONDOWN:
                if humanTurn:
                    location = p.mouse.get_pos()
                    col = location[0] // SQ_SIZE
                    row = location[1] // SQ_SIZE
                    if sqSelected == (row, col):
                        sqSelected = (); playerClicks = []
                    else:
                        sqSelected = (row, col)
                        playerClicks.append(sqSelected)
                    if len(playerClicks) == 2:
                        attempt = Move(playerClicks[0], playerClicks[1], gs.board)
                        moveFound = None
                        for mv in validMoves:
                            if attempt.getChessNotation() == mv.getChessNotation():
                                moveFound = mv; break
                        if moveFound:
                            # promotion UI if needed
                            if moveFound.isPawnPromotion:
                                promo = askPromotionChoice()
                                moveFound.promotionChoice = promo if promo else 'Q'
                            gs.makeMove(moveFound)
                            moveMade = True
                            redo_stack.clear()
                            sqSelected = (); playerClicks = []
                        else:
                            playerClicks = [sqSelected]
            elif e.type == p.KEYDOWN:
                if e.key == p.K_z:
                    if gs.moveLog:
                        last = gs.moveLog[-1]
                        gs.undoMove()
                        redo_stack.append(last)
                        moveMade = True
                elif e.key == p.K_y:
                    if redo_stack:
                        mv = redo_stack.pop()
                        # create a fresh Move object to reapply
                        mv2 = Move((mv.startRow, mv.startCol), (mv.endRow, mv.endCol), gs.board,
                                   pieceMoved=mv.pieceMoved, pieceCaptured=mv.pieceCaptured,
                                   isEnpassantMove=mv.isEnpassantMove, isCastleMove=mv.isCastleMove,
                                   promotionChoice=mv.promotionChoice)
                        gs.makeMove(mv2)
                        moveMade = True
                elif e.key == p.K_r:
                    gs = GameState()
                    validMoves = gs.getValidMoves()
                    sqSelected = (); playerClicks = []
                    redo_stack.clear()
                    moveMade = False
                elif e.key == p.K_h:
                    def apply_undo():
                        nonlocal gs, validMoves, moveMade
                        if gs.moveLog:
                            last = gs.moveLog[-1]
                            gs.undoMove()
                            redo_stack.append(last)
                            validMoves = gs.getValidMoves()
                    def apply_redo():
                        nonlocal gs, validMoves, moveMade
                        if redo_stack:
                            mv = redo_stack.pop()
                            mv2 = Move((mv.startRow, mv.startCol), (mv.endRow, mv.endCol), gs.board,
                                       pieceMoved=mv.pieceMoved, pieceCaptured=mv.pieceCaptured,
                                       isEnpassantMove=mv.isEnpassantMove, isCastleMove=mv.isCastleMove,
                                       promotionChoice=mv.promotionChoice)
                            gs.makeMove(mv2)
                            validMoves = gs.getValidMoves()
                    showMoveHistoryPopup(gs, apply_undo, apply_redo)
                    moveMade = True
                elif e.key == p.K_d:
                    root = tk.Tk(); root.withdraw()
                    newd = simpledialog.askinteger("AI Depth", "Enter AI depth (ply):", initialvalue=AI_DEPTH, minvalue=1, maxvalue=8)
                    root.destroy()
                    if newd:
                        AI_DEPTH = int(newd)
                elif e.key == p.K_ESCAPE:
                    p.quit(); sys.exit()

        # AI turn
        if not humanTurn and not gs.isCheckmate() and not gs.isStalemate():
            validMoves = gs.getValidMoves()
            if validMoves:
                aiMove = movefinder.findBestMove(gs, validMoves, depth=AI_DEPTH)
                if aiMove is None:
                    aiMove = random.choice(validMoves)
                if aiMove.isPawnPromotion and not aiMove.promotionChoice:
                    aiMove.promotionChoice = 'Q'
                gs.makeMove(aiMove)
                redo_stack.clear()
                moveMade = True

        if moveMade:
            validMoves = gs.getValidMoves()
            moveMade = False

        # draw everything
        drawGameState(screen, gs, sqSelected, validMoves)
        # status
        if gs.isCheckmate():
            drawEndText(screen, "Checkmate")
        elif gs.isStalemate():
            drawEndText(screen, "Stalemate")
        else:
            drawStatus(screen, AI_DEPTH, White, Black, gs.whiteToMove)

        clock.tick(MAX_FPS)
        p.display.flip()

def drawGameState(screen, gs, sqSelected, validMoves):
    drawBoard(screen)
    # highlight moves for selected square
    highlightMoves(screen, gs, sqSelected, validMoves)
    # highlight king in check (red)
    gs.inCheck, _, _ = gs.checkForPinsAndChecks()
    if gs.inCheck:
        if gs.whiteToMove:
            kr = gs.whiteKingLocation
        else:
            kr = gs.blackKingLocation
        s = p.Surface((SQ_SIZE, SQ_SIZE)); s.set_alpha(160); s.fill(p.Color(200,50,50))
        screen.blit(s, (kr[1]*SQ_SIZE, kr[0]*SQ_SIZE))
    drawPieces(screen, gs.board)

def drawBoard(screen):
    colors = [p.Color(240,217,181), p.Color(181,136,99)]
    for r in range(DIMENSION):
        for c in range(DIMENSION):
            color = colors[(r+c) % 2]
            p.draw.rect(screen, color, p.Rect(c*SQ_SIZE, r*SQ_SIZE, SQ_SIZE, SQ_SIZE))

def highlightMoves(screen, gs, sqSelected, validMoves):
    if sqSelected == ():
        return
    r,c = sqSelected
    piece = gs.board[r][c]
    if piece == "--":
        return
    # show only moves from that square (legal moves)
    dests = [ (m.endRow, m.endCol) for m in validMoves if m.startRow==r and m.startCol==c ]
    s = p.Surface((SQ_SIZE, SQ_SIZE)); s.set_alpha(140); s.fill(p.Color(100,180,255))
    for (rr,cc) in dests:
        screen.blit(s, (cc*SQ_SIZE, rr*SQ_SIZE))

def drawPieces(screen, board):
    for r in range(DIMENSION):
        for c in range(DIMENSION):
            piece = board[r][c]
            if piece != "--":
                try:
                    screen.blit(IMAGES[piece], p.Rect(c*SQ_SIZE, r*SQ_SIZE, SQ_SIZE, SQ_SIZE))
                except Exception as e:
                    font = p.font.SysFont('arial', 20)
                    label = font.render(piece, True, p.Color('black'))
                    screen.blit(label, (c*SQ_SIZE+6, r*SQ_SIZE+6))

def drawEndText(screen, text):
    font = p.font.SysFont('Helvetica', 36, True, False)
    txt = font.render(text, True, p.Color('black'))
    screen.blit(txt, (WIDTH//2 - txt.get_width()//2, HEIGHT//2 - txt.get_height()//2))

def drawStatus(screen, depth, whiteFlag, blackFlag, whiteToMove):
    font = p.font.SysFont('Arial', 16)
    status = "White to move" if whiteToMove else "Black to move"
    t = f"{status} | AI depth: {depth} | White human: {whiteFlag} | Black human: {blackFlag}"
    text = font.render(t, True, p.Color('black'))
    screen.blit(text, (6, HEIGHT - 22))

if __name__ == "__main__":
    main()
