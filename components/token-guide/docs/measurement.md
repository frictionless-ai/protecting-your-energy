# Measure the relevant cost

When work feels slow, first examine where elapsed time went. Model processing, tool execution, waiting, setup and owner interaction can create different bottlenecks.

The audit command reads an explicitly selected Claude-style JSONL session and adjacent subagent files. It groups records by assistant message identity, reads available usage fields and estimates repeated-context costs under the configured coefficients.

```sh
python3 tools/audit.py /path/to/selected-session.jsonl
```

Its findings identify an observed pattern, a possible cost mechanism and an alternative workflow. Whether calls were independent, reviews redundant or a wait avoidable still needs contextual examination. Counterfactual cost estimates can overlap and should not be summed as verified savings.

Timestamp gaps are interpreted heuristically. Long gaps may be classified as time away, while notifications and tool records help estimate waits. The tool does not observe the person's actual activity or infer a mental state.

Set `TG_READ`, `TG_WRITE_1H`, `TG_WRITE_5M` and `TG_OUT` for the intended accounting model. The defaults preserve the source tool's historical ratios, and current billing may use different prices, cache policy or model routing.

Choose an intervention that changes the actual bottleneck, then compare the relevant outcome. Preserve complete task coverage, data safety and acceptance requirements during that comparison. More concise output or fewer calls can still leave the requested work unfinished.

All transcript and audit material remains private input/output. The bundle contains reusable code and guidance, while the original session measurements remain outside the distributed documentation.
