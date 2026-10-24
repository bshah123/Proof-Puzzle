import Std

namespace ProofPuzzle
inductive Color where
  | coral | blue | mint | gold
  deriving BEq, DecidableEq, Repr
inductive Move where
  | swap (a b : Nat)
  | paint (cell : Nat) (color : Color)
  deriving Repr
abbrev Board := List Color
structure State where
  board : Board
  paints : Nat
  deriving DecidableEq, Repr

def adjacent (a b : Nat) : Bool :=
  (a / 2 == b / 2 && (a + 1 == b || b + 1 == a)) ||
  (a % 2 == b % 2 && (a + 2 == b || b + 2 == a))

def step (locked : List Nat) (s : State) : Move → Option State
  | .swap a b => do
    if locked.contains a || locked.contains b || !adjacent a b then none else do
      let ca ← s.board[a]?
      let cb ← s.board[b]?
      some { s with board := (s.board.set a cb).set b ca }
  | .paint cell color => do
    if locked.contains cell || s.paints == 0 then none else do
      let _ ← s.board[cell]?
      some { board := s.board.set cell color, paints := s.paints - 1 }

def run (locked : List Nat) : State → List Move → Option State
  | s, [] => some s
  | s, m :: ms => (step locked s m).bind (fun next => run locked next ms)

def Solves (start target : Board) (locked : List Nat) (paints limit : Nat)
    (moves : List Move) : Prop :=
  moves.length ≤ limit ∧
  ((run locked ⟨start, paints⟩ moves).map State.board = some target)

instance (start target : Board) (locked : List Nat) (paints limit : Nat)
    (moves : List Move) : Decidable (Solves start target locked paints limit moves) :=
  inferInstanceAs (Decidable (_ ∧ _))
end ProofPuzzle
