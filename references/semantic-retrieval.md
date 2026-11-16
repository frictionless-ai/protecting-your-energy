# Local semantic retrieval

`scripts/semantic_retrieve_portable.py` provides configured dense retrieval over
local conversation exports. Model files, indexes and private source catalogs
remain outside the repository and raw archive.

## Commands

Select a Python environment with the backend's dependencies and supply the local
index path.

```sh
python3 scripts/semantic_retrieve_portable.py status --index /path/to/index
python3 scripts/semantic_retrieve_portable.py query 'the idea to recover' \
  --index /path/to/index --role self --limit 8 --json
python3 scripts/semantic_retrieve_portable.py parents \
  --index /path/to/index --unit-id HASH --generation GENERATION
python3 scripts/semantic_retrieve_portable.py hydrate \
  --index /path/to/index --message-id ORIGINAL_ID --version VERSION_HASH --neighbors 5
```

Queries return ranked leads. Inspect the generation's actual source families,
dates and partial-coverage metadata before interpreting a result. Complementary
queries can reveal relevant material missed by the first ranking.

Packed windows retain parent IDs, dates, authors, source pointers and text-version
hashes. Use exact parent lookup and hydration to inspect the original context,
including replies and corrections. A match requires attribution review before
being treated as the owner's statement or adopted idea.

The shared archive helper additionally supports configured generic normalized
archives and original-source resolution. Its guide describes configuration,
provenance checks, input lanes and read boundaries.
[Archive access](archive-access.md)

`scripts/semantic_retrieve.py` retains the source bytes pinned by older index
generations. Use the portable variant for new configuration. Review recorded
source and policy compatibility before migrating an existing generation.
