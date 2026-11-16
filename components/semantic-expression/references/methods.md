# Preserve meaning before improving presentation

[Maynez et al., ACL 2020](https://aclanthology.org/2020.acl-main.173/)
distinguishes source faithfulness from factuality; fluency alone is not fidelity.
[LaMP](https://aclanthology.org/2024.acl-long.399/) supports task-relevant personal
example retrieval, not a fixed persona or proven full intention reconstruction.

Retrieve examples from the owner's relevant conversations rather than using
a fixed demonstration as the model of every request. Recover the distinction
the owner was expressing before choosing terminology. A familiar category can
misrepresent a new mechanism. Preserve multiple plausible interpretations until
the surrounding context resolves them.

[AI Chains](https://www.cs.cmu.edu/~sherryw/assets/pubs/2022-chain.pdf)
motivates distinct extraction, writing and checking responsibilities in studied
tasks. Keep source-backed meaning available to the checker. This is a practical
adaptation, not a claim that this prompt or its number of stages is optimal.
