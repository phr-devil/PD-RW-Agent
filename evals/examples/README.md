# Synthetic-only fixtures

- `synthetic_case.json` hashes the fake `synthetic_snapshot.md` file; it contains no real research.
- `synthetic_decision.json` demonstrates a self-declared research premise, multiple hypotheses, and prechecks deliberately marked UNKNOWN / NOT_CHECKED.
- Actual A/B/C responses, unpublished papers, personal information, private author permissions, SEALED files and unblinding keys MUST NOT be committed to this public repository.

```powershell
python -m pdrw_agent.science.cli decision --packet evals/examples/synthetic_decision.json
python -m pdrw_agent.science.cli replay-check --root evals/examples --manifest evals/examples/synthetic_case.json
```
