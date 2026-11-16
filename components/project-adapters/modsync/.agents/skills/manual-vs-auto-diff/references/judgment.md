# How to judge a diff

Load this after `diff_manual_vs_auto.sh` finishes.

- Compare file/resource **content**, not patch counts.
- Packing-only ERF/TLK byte diffs can be acceptable when content matches.
- Mid-run extras that are `.tpc` with a `.tga` in the finished manual are step-181 class on K1 until that step runs.
- Generator extras (files the guide never asked for) are not a Holo-vs-Bio difference.
- Do not write `K1_manual` or `K2_manual`.
