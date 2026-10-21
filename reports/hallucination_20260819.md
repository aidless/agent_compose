# Hallucination scan report (MLR-Bench four types)

Target: `paper_tmlr`

## (E) Nonexistent Citations / incomplete bib entries
- none

## (E) Hallucinated Methodology: named method files missing
- scripts/generate.py@main.tex
- scripts/run_all.py@README_TMLR.md

## (W) Mathematical Errors: inline arithmetic contradictions
- none

## (I) Faked Results surface: strong-claim count for LLM judge
- 1 strong-assertion phrases found; LLM judge must verify each against evidence

## (I) Numbers without ledger coverage
- 210 numeric literals not covered by CLAIM_LEDGER.md values
-0.070, -0.085, -0.115, -0.135, -0.27, -0.31, -0.4, -0.452, -0.65, -0.725, -0.745, -0.78, -1.0, -2.44, -2.5, 0, 0.0, 0.00, 0.000, 0.0008, 0.001, 0.005, 0.010, 0.015, 0.02, 0.020, 0.025, 0.04, 0.040, 0.05, 0.055, 0.057, 0.06, 0.060, 0.062, 0.065, 0.07, 0.070, 0.075, 0.08, 0.080, 0.083, 0.088, 0.090, 0.097, 0.1, 0.10, 0.104, 0.105, 0.107, 0.11, 0.110, 0.112, 0.115, 0.117, 0.125, 0.133, 0.135, 0.14, 0.145, 0.148, 0.15, 0.155, 0.16, 0.160, 0.162, 0.165, 0.168, 0.17, 0.173, 0.175, 0.178, 0.18, 0.180, 0.184, 0.190, 0.1946, 0.1949, 0.196, 0.20

## Summary: 0 cite errors, 2 missing method files, 0 arithmetic warnings, 1 strong claims