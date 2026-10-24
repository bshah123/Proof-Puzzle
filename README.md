# Proof Puzzle

A local web game for Syntax Error 2026's Functional Programming track. Five levels teach composition, resource constraints, invariants, and a reusable Lean helper through a 2×2 colored board.

## Run

Install Lean through the official elan installer at https://lean-lang.org/install/manual/. This project pins Lean 4.19.0 in `lean-toolchain`. Python 3.9+ is the only web-server dependency.

```sh
cd /Users/bshah/ProofPuzzle
~/.elan/bin/lean --version
python3 server.py
```

Open http://127.0.0.1:8765. Run the proof and rejection tests with `python3 -m unittest -v test_game.py`.

## What is actually verified

The move builder accepts `.swap 0 1`, `.paint 3 .blue`, and the `flipTop` helper on level five. This is a constrained editor for Lean expressions, not a general-purpose Lean IDE. The server constructs a full standalone Lean file from allowlisted expressions. Its theorem establishes both the move budget and successful execution to the target. The transition function enforces adjacency, board bounds, locked tiles, and paint allowance. Lean's `by decide` checks the concrete theorem in the kernel; no `sorry`, axioms, or `native_decide` are used.

Python provides quick previews, but only a successful Lean process earns a win. Inspect or download the entire proof from the UI. The helper level generates real list composition using a named Lean definition.

## Implementation

- `lean/Rules.lean`: pure state transitions and the Solves proposition.
- `server.py`: level data, constrained parser, preview simulator, and bounded compiler invocation.
- `web/`: responsive interface, editor, playback, hints, proof inspector, and locally saved completion.
- `test_game.py`: all five positive proofs, negative kernel checks, and input validation.

The server binds only to loopback. It is a local hackathon demo, not a hardened multi-user execution service. A public deployment needs a separately isolated Lean runner; Cloudflare Workers cannot launch this compiler. The frontend uses optional Google Fonts with system fallbacks. Completion stored in localStorage is a convenience, not a trusted leaderboard.

## Demo script

1. Level 1: insert Swap, step forward, then Check proof. Show the verified result.
2. Change it to `.swap 0 3`: show why a diagonal swap fails.
3. Level 3: show locked tiles and the one-paint constraint.
4. Level 5: use `flipTop`, `.swap 1 3`, `flipTop`; inspect the generated helper and theorem.
5. Download the standalone `.lean` file and verify it independently.

## Next priorities

User-authored helpers, richer guided proof writing, orientation/rotation puzzles, and more levels. The present milestone deliberately uses a constrained move builder and automatic `decide` proof instead of asking beginners to write arbitrary Lean tactics.
