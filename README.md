# ♟️ Chess Engine with Pygame

A simple yet powerful **Chess Engine** built in **Python** using **Pygame 2.6.1**.  
It features a clean graphical interface, an AI opponent powered by **Negamax with Alpha-Beta Pruning**, and a full implementation of core chess rules.

---

## 📚 Table of Contents
1. [Features](#-features)
2. [Requirements](#-requirements)
3. [Installation](#-installation)
4. [Usage](#-usage)
5. [File Structure](#-file-structure)
6. [Development](#-development)
7. [Contributing](#-contributing)


---

## 🚀 Features

### 🎮 Gameplay
- Play as **White** or **Black** (toggle via `Black` variable).
- Smooth GUI built with **Pygame**.

### 🧠 Artificial Intelligence
- AI opponent uses **Negamax algorithm** with **Alpha-Beta pruning** for efficient move selection.

### ⚖️ Rules Implemented
- ✅ Checkmate and stalemate detection  
- ✅ En passant  
- ✅ Castling  
- ✅ Pawn promotion (to **Queen** by default)

### 🖼️ Graphics
- Uses **custom chess piece images** stored in the `/images` folder.

### 👤 User Control
- Switch between **user** and **AI** control by editing the `Black` variable in `main.py`:
  ```python
  # Change control
  Black = True   # User controls Black
  Black = False  # AI controls Black
  ```
### 🧩 Requirements

- Python 3.x

- Pygame 2.6.1
```python

pip install pygame==2.6.1

```

Chess piece images (included in the /images folder):
```python
bb.png, bk.png, bp.png, br.png, wb.png, wk.png, wp.png, wr.png, etc. 
```
### ⚙️ Installation

- Clone the repository
```python

git clone https://github.com/SMZuqlarnain/chess.git
cd chess-engine

```

- Install dependencies
```python

pip install pygame==2.6.1

```
- Ensure image assets are present

- Make sure the /images folder (with all chess piece PNGs) is inside the project directory.

### 🕹️ Usage

- Run the game:
```python

python main.py
```
### 🎯 Controls

- When Black = False, the AI controls Black.
```python
WhiteHuman = True
BlackHuman = False

```
- 🖱 Click a piece to select it.
- 🖱 Click a highlighted square to move it.
- 🎯 Blue squares = legal moves.
- 🔴 Red square = king in check.
- ⏪ Press Z → Undo last move.
- 🔁 Press Y → Redo move.
- 👑 Pawn Promotion Popup appears when a pawn reaches last rank (choose R/N/B/Q).
- ♟ En passant, castling, stalemate, and checkmate are fully implemented.
- ♻ Threefold repetition = automatic draw.
- 🧠 depth press d to change the debth of AI thinking

### 📁 File Structure
- File / Folder	Description
- main.py	Main game loop and Pygame interface
- chessengine.py	Core chess logic and move handling
- movefinder.py	Move generation and AI evaluation
- images/	Folder containing chess piece sprites (e.g., wp.png, br.png)
###🧑‍💻 Development

- - Developed on Windows using VS Code

- Compatible with Pygame 2.6.1

- Tested in browser environments via Pyodide (no local file I/O)

### 🤝 Contributing

Contributions are welcome!
Feel free to fork this repository, improve the AI, add new features, or optimize performance.
