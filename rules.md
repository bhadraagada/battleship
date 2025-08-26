# **Battleship Game – Rules**
## **Overview**

Battleship is a two-player strategy game where players take turns to guess the locations of the opponent's ships on a grid. The goal is to sink all of the opponent's ships before they sink yours. In this version, you'll be playing against an AI opponent that uses the minimax algorithm with alpha-beta pruning to determine its moves.

## **Game Setup**

The game takes place on a 10x10 grid, where each player has a fleet of ships randomly placed. The fleet consists of the following ships:

- 1 Ship of size 5
- 1 Ship of size 4
- 2 Ships of size 3
- 1 Ship of size 2

Each player will place their ships on their grid, and the positions are hidden from the opponent.

## **Gameplay**

### **Turn Structure**

The game alternates between player turns and AI turns.

### **Player Turn**

You click on the enemy grid to choose a cell to attack.

### **AI Turn**

The AI selects a random valid cell and attempts to hit your ships.

### **Firing**

On each turn, you or the AI will fire a shot at a specific cell on the opponent's grid.

### **A shot can either hit or miss:**

- **Hit**: The shot hits one of the opponent’s ships. The ship's cell turns red.

- **Miss**: The shot misses, and the cell is marked with a black circle.

### **Special Rule – Extra Turn on Hit:**

- **If you or the AI hits an opponent's ship, that player will get another turn to play.**

- **If the shot is a miss, it will switch turns as usual.**
- **If you or the AI hits an opponent's ship, that player will get another turn to play.**
- **If the shot is a miss, it will switch turns as usual.**

### **Game End**

The game ends when either player has sunk all the opponent's ships. The first player to sink all of the opponent's ships wins.

### **AI Behavior**

### **The AI uses the minimax algorithm with alpha-beta pruning to select its shots. It evaluates different possible moves and chooses the one that maximizes its chance of winning. The AI uses a simple heuristic based on the remaining ships and makes its best move based on the search depth.**

Winning the Game

### **Victory**: The player who sinks all of the opponent’s ships first wins the game.

### **Defeat**: If all your ships are sunk by the opponent, you lose.

### **Controls**  

### **Player Move**: Click on the grid to attack the enemy.

### **AI Move**: The AI will automatically make a move after your turn.
