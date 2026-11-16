# Operate a configured private library

The library uses explicit configuration and read-only sources. Keep output, reviews and hosted receipts outside the raw archive and plugin package. The [component README](../README.md) describes configuration and optional dependencies.

## Library and review

A build publishes a versioned run with source hashes, normalized fragments, candidate thought objects, metadata, canvas files and task briefs. It changes the current-run reference only after validation. Failed builds retain the previous usable run.

The static canvas is generated under the configured output. Its reviewed collection, candidates, search and private Markdown task briefs use generated local data. Task briefs can contain private quotations.

Reviews select exact fragment keys and preserve reviewer attribution, interpretation, unresolved questions and proposed actions. Candidate model output remains distinguishable from a review. Evolution and endorsement records require their supporting evidence.

Supported source kinds include curated DM Markdown, thought-stream captures, structured catalogs, self-attributed JSONL and explicitly selected normalized conversation partitions. Configure identity for exports whose attribution depends on owner IDs or Markdown aliases. Unknown speakers and derived paraphrases remain distinct from verbatim owner evidence.

## Semantic processing

Offline processing is available. A `semantic` configuration with provider `claude` enables the bounded hosted adapter. It requires a receipt-cache directory outside the archive and a fragment cap between 1 and 300. Batches are bounded by the configuration and adapter.

Cached request/response receipts allow reuse. A build without `--spend` refuses a cache miss. Explicitly enabling a provider-capable run requires the current user's authorization for the selected transmission.

Optional `semantic.merge` configuration supports cross-batch joining, project scope, a bounded verification-call budget, inspection marks and rejected fragment pairs. `merge-plan` previews required cached and uncached work. A malformed response leaves the last usable library in place.

Optional `semantic.flag` configuration provides bounded context-assisted readings of short or dependent fragments. It preserves original evidence and separates model interpretations from owner text and reviews. `flag-report` writes a local keys-only sample beside the private configuration.

The accepted fields and limits are checked by `tr_engine.library.read_config`. Configure the capabilities your run needs.

## Research and recovery

Configured repository research performs bounded local `rg` and `git` queries. Related source is a discovery lead that requires behavior verification.

`reclaim TEXT` prepares a bounded evidence packet from the configured archive route, saved library and explicit supported inputs. It preserves source identities, role qualifications, unresolved versions and retrieval limitations. The active agent reads and interprets the relevant source context.

Shared retrieval has its own private configuration, index generation and source coverage. If a required backend is unavailable, inspect the packet's error and coverage. Configure a supported route and preserve unresolved source work.

## Verification boundaries

Private archives, reviews, generated canvas data, provider receipts and machine-specific configuration remain outside this package. The original source checkout retains its evaluation assets and history.

Syntax, package structure, source correspondence and live library outcomes require separate evidence. This inclusion operation performs static packaging checks. Inspect the configured installation before claiming a working source library, provider or complete reconstruction.
