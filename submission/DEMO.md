# Proof Puzzle: 2–3 minute demo draft

This is a suggested recording length, not an organizer requirement. Check the actual submission form.

## Before recording

1. Start `python3 server.py` from the repository and open http://127.0.0.1:8765/.
2. Keep the app and terminal readable. Choose level 1 and replace its draft with the two-move example below. Do not erase unrelated browser storage.
3. Prepare level 6 helper definitions, then remove them before recording if demonstrating the builder live.
4. Have `submission/proofs/Level7.lean` and a terminal ready for the independent check.
5. Rehearse once. Keep the real error, the real correction, and the real verification visible.

## 0:00–0:20 — The pitch

“Proof assistants are powerful, but the first proof can feel abstract. Proof Puzzle makes it tangible: every line moves a block, every mistake has a visible consequence, and every win is checked by Lean.”

## 0:20–0:55 — One mistake, one proof

On level 1 enter `swap 0 3`. Show the red cells and the diagonal-swap explanation. Click Check proof to show Lean rejects the move.

Replace it with:

```lean
swap 0 1
swap 2 3
```

“Typing gives us an instant preview. Matching colors alone does not award a win. Check proof asks Lean to verify legality and the target.”

Click Check proof. Let the success message appear.

## 0:55–1:15 — State means more than color

Switch to level 4 and enter:

```lean
swap 1 3
rotate 3
rotate 3
```

“Blocks have direction as well as color. Rotation and paint have explicit rules, and locked cells cannot change.”

Step backward and forward once to show the orientation moving with the block.

## 1:15–1:55 — Abstraction you can see

Open level 6. Use the helper builder to name `shift` with the moves:

```lean
swap 0 1
swap 1 2
```

Show the generated editable Lean macro. Add a second helper `halfTurn` containing two `rotate 4` moves. The proof is:

```lean
shift
shift
halfTurn
```

“The three-line limit makes abstraction useful. A helper names a pattern, and later helpers can compose earlier ones. This is ordinary Lean macro syntax, checked through the same rules.”

Click Check proof.

## 1:55–2:25 — Trust you can inspect

Open the proof inspector and show the theorem and its axioms. Then show the standalone level-seven file being checked:

```sh
~/.elan/bin/lean submission/proofs/Level7.lean
```

“The proof works outside our UI. Our browser preview also matches Lean on over twenty thousand generated short move sequences. Local uncached checks measured roughly 0.15 to 0.26 seconds.”

## 2:25–2:40 — Close

“Seven levels take the player from concrete moves to reusable proofs. Proof Puzzle makes formal reasoning something you can see, try, and verify.”

## Likely questions

**Is the browser the verifier?** No. It previews. Lean must accept the generated theorem before the app marks the level complete.

**Is this arbitrary Lean?** No. The player uses a restricted set of real Lean tactics and helper macros. That keeps the teaching scope clear and avoids running arbitrary submitted code.

**Why functional programming?** The board is immutable state, moves are pure functions returning a new state or failure, and solutions compose those transitions. The Lean proof establishes reachability through legal transitions.

**Are you claiming no axioms?** No. Reference proofs use Lean's standard `propext` and `Quot.sound`; the verifier rejects `sorryAx` and unapproved axioms.

**Is learning effectiveness proven?** No user study yet. The game is designed to make proof concepts concrete; that educational claim still needs user testing.

**Does it run online?** The current demo runs locally. A public service needs an isolated Lean worker. Don't give judges a localhost URL as a public demo link.
