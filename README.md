Chess Engine with Pygame
A simple chess engine built using Python with Pygame 2.6.1, featuring a graphical interface, AI opponent with negamax and alpha-beta pruning, and various chess rules.
Features

Gameplay: Play as White or Black (toggleable via Black variable).
AI: AI opponent using negamax with alpha-beta pruning for move selection.
Rules Implemented:
Checkmate and stalemate detection.
En passant.
Castling.
Pawn promotion (always to Queen).


Graphics: Uses custom chess piece images stored in the images folder.
User Control: Switch between user mode (Black = True) and AI mode (Black = False) by editing the code.

Requirements

Python 3.x
Pygame 2.6.1 (pip install pygame==2.6.1)
Images for chess pieces (provided in the images folder: bb.png, bk.png, etc.)

Installation

Clone the repository:git clone (https://github.com/SMZuqlarnain/chess.git)
cd chess-engine


Install the required package:pip install pygame==2.6.1


Ensure the images folder with chess piece PNGs is in the project directory.

Usage

Run the game:python main.py


Controls:
Click a piece to select it.
Click the destination square to move.
The game alternates turns; AI moves automatically if Black = False and it's Black's turn.


Modify Black in main.py to switch between user and AI control:
Black = True: User controls Black pieces.
Black = False: AI controls Black pieces.



File Structure

chessengine.py: Core game logic and move handling.
movefinder.py: Move generation and AI evaluation.
main.py: Main game loop and Pygame interface.
images/: Folder containing chess piece images (e.g., wp.png, br.png).

Development

Developed on Windows using VS Code.
Compatible with Pygame 2.6.1 in a browser environment via Pyodide (no local file I/O).

Contributing
Feel free to fork this repository, make improvements (e.g., better AI depth, additional rules), and submit pull requests!
License
MIT License (or specify your preferred license if different).
