# The change request

**Important:** the real GigSim "platform policy update" (2 Nov) was not part of the materials I had, so I **simulated** one: Connects cost x1.5, cover letter must be 200-1500 characters (previously unlimited-ish, 3000 max). 

What changed (commit `b8a7d71`, `git show --stat b8a7d71`): `agent/config.yaml` (3 lines: `connects_multiplier`, `min/max_cover_letter_chars`), `data/gigsim_seed/policy.json` (simulator side, 4 lines) and 2 test fixture strings that used 60-character letters (now rejected by the new minimum). **9 lines, 3 files, no Python logic.** Elapsed time: a few minutes including the test run. Pricing already reads the *current* Connects cost from the marketplace tool at run time; Compliance reads length bounds from config; the Writer prompt's word limits stayed inside the new bounds.

What this says about the design: rules in config + a read-the-policy tool absorb numeric policy changes cheaply. What it would *not* absorb: a new *kind* of rule (e.g. "no more than 3 proposals per client per week") needs a new check node/logic; the Compliance Guard only knows banned phrases, contact patterns and length.
