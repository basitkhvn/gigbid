# Signature extension: X2 Proposal experiments

Two proposal strategies are run as an A/B test in the simulator on the same jobs (paired), with significance tests:
* **A (shipped)**: evidence-grounded, one retrieval per requirement, cited projects.
* **B**: generic skills list ("passionate ... can start right away").

Runner: `python -m evals.runners.gigsim_outcomes` -> `evals/results/ab_experiment.json` (reply rate, Fisher exact test, paired exact McNemar test). Result and caveats are in docs/RESULTS.md. Important caveat: the simulated client rewards skill mentions and punishes generic phrasing **by construction**, so the experiment demonstrates the A/B *machinery* and the plumbing (strategy -> GigSim -> test); it is not evidence about real clients. A first run with a weaker "top-5 items" version of A *lost* to B (0.19 vs 0.42) because the same project described three ways crowded out other projects and fewer requirements were named (`evals/results/gigsim_outcomes.json`, rows v0-v8); the per-requirement version is what ships.
