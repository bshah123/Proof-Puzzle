# Proof Puzzle

A local web game for Syntax Error 2026's Functional Programming track. A grid of colored blocks sits next to a target picture. You solve a level by writing a short Lean proof in which every line is a move: swap two blocks, paint one, or rotate one. The board updates after every line; an illegal move turns its blocks red. The level clears only when Lean accepts the proof, which requires the final board to equal the target. Seven levels go from two-move proofs to helpers you name yourself and build from other helpers.

## Run

Install Lean through the official elan installer at https://lean-lang.org/install/manual/. This project pins Lean 4.19.0 in `lean-toolchain`. Python 3.9+ is the only server dependency; Node is needed only for the tests.

```sh
cd /Users/bshah/ProofPuzzle
~/.elan/bin/lean --version  # installs the pinned toolchain on a new machine
python3 server.py        # precompiles lean/ProofPuzzle/Rules.lean into build/ on first start
```

Open http://127.0.0.1:8765. Run the tests with `python3 -m unittest -v test_game.py` and `node --test test_ui.cjs`.

## What a proof looks like

```lean
macro "shift" : tactic => `(tactic| (swap 0 1; swap 1 2))     -- a helper (levels 6–7)

theorem level_6_solved : Reaches puzzle start := by
  shift                                                         -- each line plays legal moves
  shift
  rotate 4
  rotate 4
  exact Reaches.finish (by decide)                              -- added for you: board = goal
```

`Reaches puzzle start` says that some sequence of legal moves turns the starting board into the target. `swap`, `paint`, and `rotate` are Lean tactics defined in `Rules.lean`. Each one applies `Reaches.move` and discharges the move's legality with `decide`, so Lean reports an illegal move at the line that played it, including moves inside a helper. Helpers are ordinary Lean `macro`s and can call earlier helpers.

## What is actually verified

- `Rules.lean` defines the transition function: neighbours that share an edge on a grid of any width, board bounds, locked cells, paint, rotation, and the move budget. The budget lives in the state, so Lean enforces it, not just the server.
- The win condition is that the Lean process succeeds with no errors and `#print axioms` lists only standard axioms (`propext`, `Quot.sound`). `sorry`, `native_decide`, and arbitrary Lean never reach the compiler: the server accepts only an allowlisted grammar of moves, helper definitions, and helper calls.
- The browser preview (`web/rules.js`) is a convenience. A differential test runs it and Lean's own `run` on every one- and two-move sequence for three board setups (about 20,000 cases) and requires identical results. A second test checks that the Python and browser parsers accept and reject the same inputs.
- The proof inspector shows the full standalone file, with the rules included, which checks with plain `lean`.
- Proof-line limits (levels 6–7) are a property of the text, so the editor and server enforce them, not Lean.

## Implementation

- `lean/ProofPuzzle/Rules.lean`: the state, transitions, `Reaches`, its two lemmas, and the player tactics.
- `server.py`: level data, the allowlist parser, Lean file generation with a map from Lean's line numbers back to the player's, a precompiled `.olean` (rebuilt when the rules or toolchain change), and a cache of up to 256 results. Requests must come from localhost (both `Host` and `Origin` are checked).
- `web/`: the live board, line-by-line playback (the board follows your cursor), gutter status for each line, two-tier hints, saved drafts and progress, and the proof inspector.
- `test_game.py`: every level's solution, rejections mapped to the right line, Lean-side budget enforcement, the standalone download, injection attempts, and the two differential tests.

On an M-series Mac a Lean check takes about 0.15–0.2 s with the precompiled rules, and about 0.5 s if precompiling fails and the rules are compiled inline. Removing `import Std` and the `.olean` together make checks roughly 8× faster than the first version.

The server binds only to loopback. It is a local hackathon demo, not a hardened multi-user service; a public deployment needs a separately isolated Lean runner. Completion stored in localStorage is a convenience, not a trusted leaderboard.

## Demo script

1. Level 1: type `swap 0 1` and watch the board move; then `swap 0 3` turns two tiles red and marks the line. Fix it and press Check proof (⌘/Ctrl + Enter).
2. Level 3: the locked cell and the single drop of paint.
3. Level 4: rotation. The pointer travels with the block.
4. Level 6: the three-line limit forces named helpers. Click a line to see the board after it.
5. Level 7: a helper built from a helper. Open "Inspect the actual Lean proof", download it, and run `lean ProofPuzzle-Level7.lean`.

## Next priorities

Helpers that take arguments (`macro "trade" a:num b:num`), a goal panel mirroring Lean's infoview, and more levels on larger boards.

## Submission preparation

The `submission/` directory contains draft submission copy, a timed demo script, a final checklist, a standalone proof, and measured benchmark results. Regenerate measurements with `python3 scripts/benchmark.py`. Local API measurements exclude HTTP/browser latency and are not production guarantees.

The helper button now opens a guided builder that produces editable Lean macros. A board indicator counts tiles matching both color and direction. Async verification ignores stale responses when the proof changes. Completion badges are keyed by the level definition so redesigned levels cannot inherit old wins; legacy browser data is preserved.

The submission deadline supplied by the participant is 25 October 2026 at 09:00 IST. Repository: https://github.com/bshah123/Proof-Puzzle. Demo recording/upload and final form submission are still outstanding.
