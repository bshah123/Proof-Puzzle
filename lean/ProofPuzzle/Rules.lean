/-
Proof Puzzle rules. A level is solved by a proof of `Reaches puzzle start`.
Every player line is a tactic (`swap`, `paint`, `rotate`, or a named helper)
that plays one legal move; `exact Reaches.finish (by decide)` closes the goal
only when the board equals the target. No `sorry`, axioms, or `native_decide`.
-/
namespace ProofPuzzle

inductive Color where
  | coral | blue | mint | gold
  deriving DecidableEq, Repr

/-- A block has a color and a facing: quarter turns clockwise from north (0–3). -/
structure Block where
  color : Color
  facing : Nat
  deriving DecidableEq, Repr

/-- Cells in row-major order; cell `i` sits at row `i / width`, column `i % width`. -/
abbrev Board := List Block

inductive Move where
  | swap (a b : Nat)
  | paint (cell : Nat) (color : Color)
  | rotate (cell : Nat)
  deriving DecidableEq, Repr

structure Level where
  width : Nat
  locked : List Nat
  target : Board

/-- The board plus the paint and moves still available. -/
structure State where
  board : Board
  paints : Nat
  moves : Nat
  deriving DecidableEq, Repr

/-- Cells `a` and `b` share an edge on a grid `w` cells wide. -/
def adjacent (w a b : Nat) : Bool :=
  (a / w == b / w && (a + 1 == b || b + 1 == a)) || a + w == b || b + w == a

/-- One move. `none` means illegal: no moves left, a locked cell, cells that do
not share an edge, no paint left, or a cell off the board. -/
def step (L : Level) (s : State) : Move → Option State
  | .swap a b =>
    if s.moves == 0 || L.locked.contains a || L.locked.contains b || !adjacent L.width a b then none
    else do
      let x ← s.board[a]?
      let y ← s.board[b]?
      some { s with board := (s.board.set a y).set b x, moves := s.moves - 1 }
  | .paint c col =>
    if s.moves == 0 || s.paints == 0 || L.locked.contains c then none
    else do
      let x ← s.board[c]?
      some { board := s.board.set c { x with color := col }, paints := s.paints - 1,
             moves := s.moves - 1 }
  | .rotate c =>
    if s.moves == 0 || L.locked.contains c then none
    else do
      let x ← s.board[c]?
      some { s with board := s.board.set c { x with facing := (x.facing + 1) % 4 },
                    moves := s.moves - 1 }

def run (L : Level) : State → List Move → Option State
  | s, [] => some s
  | s, m :: ms => (step L s m).bind (run L · ms)

/-- Whether `m` is a legal move in state `s`. -/
def legal (L : Level) (s : State) (m : Move) : Bool := (step L s m).isSome

/-- The state after `m`. Proofs only use it after `legal` holds. Keeping it a
named function keeps goals linear in the number of moves. -/
def next (L : Level) (s : State) (m : Move) : State := (step L s m).getD s

/-- Some sequence of legal moves takes `s` to the target board. -/
def Reaches (L : Level) (s : State) : Prop :=
  ∃ ms : List Move, (run L s ms).map State.board = some L.target

theorem Reaches.finish {L : Level} {s : State} (h : s.board = L.target) : Reaches L s :=
  ⟨[], by simp [run, h]⟩

theorem Reaches.move {L : Level} {s : State} (m : Move) (h : legal L s m = true)
    (rest : Reaches L (next L s m)) : Reaches L s := by
  obtain ⟨ms, hms⟩ := rest
  refine ⟨m :: ms, ?_⟩
  cases hs : step L s m with
  | none => simp [legal, hs] at h
  | some s' => simpa [run, next, hs] using hms

/-! Player tactics: each one plays a single move, checked by the kernel. -/

syntax "swap " num ppSpace num : tactic
syntax "paint " num ppSpace ident : tactic
syntax "rotate " num : tactic

macro_rules
  | `(tactic| swap $a $b) => `(tactic| refine Reaches.move (.swap $a $b) (by decide) ?_)
  | `(tactic| rotate $c) => `(tactic| refine Reaches.move (.rotate $c) (by decide) ?_)
  | `(tactic| paint $c $col) => do
    let col := Lean.mkIdent (`ProofPuzzle.Color ++ col.getId)
    `(tactic| refine Reaches.move (.paint $c $col) (by decide) ?_)

end ProofPuzzle
