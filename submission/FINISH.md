# Finish before 25 October, 09:00 IST

Deadline supplied by the participant. Aim to finish submission by 08:00 IST to leave an upload buffer.

## Completed in the project

- Seven Lean-backed puzzle levels, rotations, and user-defined helpers.
- Fix for editing while verification is pending, with stale-response regression tests.
- Completion keys tied to the level definition; legacy badges no longer certify redesigned puzzles.
- Guided helper builder and tile-match feedback.
- Submission description, demo script, standalone proof, and reproducible benchmark.

## Required before the actual submission

1. Confirm the organizer's current submission fields and rules in the dashboard/announcements. The public website has not published its judging rubric.
2. Verify judges can access the source at https://github.com/bshah123/Proof-Puzzle. Preserve the real history and disclose assistance if the event asks; do not backdate or manufacture commits.
3. Record and upload the short demo. Verify that its sharing permissions let judges watch it.
4. Run `python3 -m unittest -v test_game.py` and `node --test test_ui.cjs` before the final freeze.
5. Have one person unfamiliar with the game try level 1 without coaching. If they cannot start within a minute, improve the instructions rather than adding features.
6. Paste the submission description, repository link, and recording link into the required form. Verify that the submission is accepted and save its confirmation.

## What to avoid tonight

Do not add arbitrary Lean execution, accounts, multiplayer, leaderboards, or a new hosting architecture before the recording works. If public hosting is required, treat the isolated Lean runner as a separate deployment task; a static frontend alone is not a verified public demo.

## Claims to keep precise

- “Lean checks the solution,” not “our JavaScript proves it.”
- “Designed to teach proof concepts,” not “proven to improve learning.”
- “20,310 short-sequence comparisons across three configurations,” not “all possible games tested.”
- “Local uncached checks measured 148–257 ms,” not a universal latency promise.
- “Built from the organizer's Proof Puzzle challenge,” not an invented-from-scratch game concept.
