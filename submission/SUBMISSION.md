# Proof Puzzle

**Tagline:** Every move is a proof. Every win is checked by Lean.

**Event:** SDSLabs Syntax Error 2026 · FP Launchpad Functional Programming Track

**Deadline:** 25 October 2026, 09:00 IST, as supplied by the participant. Confirm the exact submission cutoff in the organizer announcements.

## Short description

Proof Puzzle turns formal verification into a visual game. Players swap, paint, and rotate colored blocks by writing short Lean tactics. The board reacts as they type, illegal moves highlight the affected tiles, and a level clears only when Lean checks the proof. Seven levels progress from two simple moves to reusable, player-defined helpers on a 3×3 board. Players can download a standalone Lean file and verify their solution independently.

## The problem it solves

For a beginner, a proof assistant can feel abstract: unfamiliar syntax, changing goals, and errors without an obvious physical meaning. Proof Puzzle gives those ideas a concrete setting. A state is a board, a tactic is a move, a failed obligation is an illegal action, and a reusable macro is a named pattern. It is designed as an approachable first encounter with formal reasoning; learning benefits have not yet been measured in a user study.

## What we built

- Seven puzzles covering composition, resources, invariants, orientation, and abstraction.
- Live previews, cursor-following playback, line-level diagnostics, and two-stage hints.
- Actual Lean tactics for swapping, painting, and rotating; each checks legality.
- Player-defined helper macros, including helpers that call earlier helpers.
- A guided helper builder that produces visible, editable Lean code.
- Kernel verification of the target, move budget, paint budget, bounds, and locked tiles.
- A standalone proof download, so the result can be checked outside the app.

## Technical approach

The rules are pure Lean state-transition functions. `Reaches puzzle start` means there exists a legal move sequence reaching the target. Each player tactic applies a proved transition lemma, establishes legality using `decide`, and leaves the next state's reachability as the remaining goal. A final equality check closes the proof only when the board matches the target, including orientation.

The browser runs a fast JavaScript preview. A small Python server accepts a restricted tactic grammar, generates a Lean file, invokes Lean, and maps diagnostics back to the player's lines. A successful visual preview never counts as a verified win. Rules are precompiled, and repeated verification results are cached.

## Evidence

- All 9 Python/Lean tests and 4 UI-state regression tests passed on 24 October.
- The preview and Lean agree on 20,310 generated one- and two-move sequences across three configurations. This is broad regression coverage, not a proof of equivalence for every possible input.
- All seven reference solutions pass Lean verification; illegal moves and unfinished boards are rejected.
- A standalone level-seven proof is included in `submission/proofs/Level7.lean`.
- One local measurement per level gave 148–257 ms for uncached checks after precompiling the rules. Cache hits took under 1 ms through the Python API. These are local measurements, not end-to-end web latency or a production benchmark. See `benchmark.json` and `scripts/benchmark.py`.

## Why it fits the track

It implements the supplied Proof Puzzle challenge directly: a board beside a target, one tactic per proof line, swaps/paints/rotations, immediate visual feedback, illegal-move highlighting, proof-checked completion, and later levels with reusable helpers. Its technical substance is in pure state transitions, immutable data, compositional tactics, and machine-checked reasoning.

## Scope and limitations

The editor intentionally accepts a constrained Lean tactic language, not arbitrary Lean programs. The helper-level proof-line limit is enforced by the editor/server; move and paint budgets are enforced by Lean. The verifier allows standard Lean axioms; the reference solutions use `propext` and `Quot.sound`, not `sorryAx`. The game currently runs locally. Public hosting needs a separately isolated Lean execution service. Saved badges are convenience state, not a secure leaderboard.

## Submission fields to complete

- Repository URL: https://github.com/bshah123/Proof-Puzzle.
- Demo video URL: **not recorded/uploaded yet**.
- Live hosted URL: **none; localhost is not accessible to judges remotely**.
- Team: solo entrant; add your registered name and details in the submission form.
- Check organizer announcements for exact form fields, video limits, and any AI-assistance disclosure requirement. The public event site does not currently provide a judging rubric.

## Accurate assistance statement, if requested

AI coding assistants supported implementation, debugging, and test generation. The submission includes the source, runnable tests, standalone Lean proofs, and reproducible measurements. Do not claim the project was built without AI assistance.

## Event references

- https://hackathon.sdslabs.co/
- https://syntax-error-6.devfolio.co/overview
- https://syntax-error-6.devfolio.co/prizes?partner=FP+Launchpad

The concept is based on the organizer-provided Proof Puzzle brief. The original contribution is this implementation and its learning experience, not the invention of proof games.
