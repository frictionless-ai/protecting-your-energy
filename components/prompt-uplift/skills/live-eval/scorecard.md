# Scorecard

One JSON object per case. Grade this full scorecard in memory. Validate without writing with:

```bash
python3 skills/live-eval/scripts/record.py < scorecard.json
```

Add `--write` to save a private result. The default record replaces contract,
prompt, gaps and failure text with lengths and hashes. This record supports
attribution and outcomes, while semantic re-grading needs the authorized source
scorecard. Add `--include-text` only when retaining that text is authorized.
`PROMPT_UPLIFT_LIVE_RUNS` or `--out-dir` selects the destination, otherwise it
uses `${XDG_STATE_HOME:-~/.local/state}/protecting-your-energy/prompt-uplift/live-runs`.
Existing record IDs are preserved and a repeated write fails.

Required keys:

```
id                  case id
source              must be "live-skill"
executor            self | fork
consulted_skill     true | false
route               uplift | pass
gaps                list of G1–G8, or []
klass               protected | complete | register-only | delegation-self | null
contract            ExecutionContract object (empty fields omitted)
compiled_prompt     string, empty when route is pass
target_model        snapshot or null
isolation           { engineer_saw_conversation: false, engineer_saw_raw_message: false }
pass                true | false
fail_reasons        list of strings
```

Optional: `ab` `{ arm_a, arm_b, winner }`.
