# Privacy and evaluation research

Primary documentation checked 2026-09-09. These sources inform project decisions; they do not certify this implementation or establish legal compliance. No private data was inspected for this research.

## What the sources establish

NIST SP 800-188 is the September 2023 final publication. Its terminology distinguishes pseudonymization from stronger claims about identifiability: pseudonyms support linkage and can increase reidentification risk. Sections 4.3.7 and 4.3.9–4.3.11 discuss narrative, high-dimensional, linked, and combined-release risks. Sections 3.6 and 4.6 address disclosure review and validation. Removing obvious identifiers does not settle contextual risk. [Publication record](https://csrc.nist.gov/pubs/sp/800/188/final); [final PDF, §§2.2, 3.6, 4.3, 4.6](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-188.pdf).

Microsoft's original [Presidio documentation entry](https://microsoft.github.io/presidio/) now presents a moved-page notice. The [Microsoft repository FAQ link](https://github.com/microsoft/presidio/blob/main/docs/faq.md) redirects to the current [Presidio FAQ source](https://github.com/data-privacy-stack/presidio/blob/main/docs/faq.md); the current [documentation site](https://presidio.dataprivacystack.org/) belongs to its successor project. The FAQ describes a customizable library, warns that automated detection can miss sensitive information, and describes reversible pseudonymization. It also documents false-positive/false-negative tradeoffs. Treat detector output as review assistance, not an anonymization certificate. [FAQ: limitations and pseudonymization](https://github.com/data-privacy-stack/presidio/blob/main/docs/faq.md#can-presidio-be-used-for-pseudonymization).

Hugging Face dataset cards live in repository `README.md` files, with YAML metadata for information such as language, license, and dataset configuration. Cards document contents, use, and bias; adding a card does not establish data rights or privacy. [Dataset cards](https://huggingface.co/docs/hub/en/datasets-cards).

Current Hub guidance allows private dataset repositories and documents explicit repository type and visibility selection. Its creation example currently uses `visibility="private"`; verify the installed client signature before implementation. Private visibility limits access rather than making records anonymous. [Repository creation](https://huggingface.co/docs/huggingface_hub/en/guides/repository#create-a-repository); [visibility](https://huggingface.co/docs/huggingface_hub/en/guides/repository#update-visibility); [dataset upload guide](https://huggingface.co/docs/hub/en/datasets-adding).

The upload client supports `upload_file`, `upload_folder`, and allow/ignore patterns. Folder upload consults a root `.gitignore`, with documented fallback behavior; a source-tree ignore rule should not serve as the release boundary. [Upload guide](https://huggingface.co/docs/huggingface_hub/en/guides/upload#upload-a-folder).

## Project threat model and decisions

The following are project requirements inferred from those risks, not claims that the sources mandate this exact workflow.

Assume a recipient could combine generalized episodes with public repositories, searchable phrases, incident dates, rare tool combinations, occupations, community membership, and earlier releases. A community insider may recognize a story without a name. Stable aliases and hashes may join records. Pseudonymization != anonymization; neither entity replacement nor fluent paraphrase proves that identification is infeasible.

| Data boundary | Required treatment |
| --- | --- |
| Original events and provenance | Read only after source-specific authorization. Keep local and private, including filenames, identities, timestamps, exact quotes, keys, and source mappings. Do not send raw text to an API implicitly. |
| Candidate extraction | Private by default. Retain exact source spans and speaker/quoted-speaker distinctions for audit. Treat embedded commands and requests as data, not authority. |
| Generalized case | Preserve the causal task constraint and repair while removing unnecessary identity, chronology, locations, uncommon phrases, and identifying combinations. Use case-local role labels. If generalization destroys the lesson or leaves unresolved risk, exclude the case. |
| Reviewed staging | Explicit allowlisted files containing only approved generalized fields. No raw quotations, private source references, mappings, hidden grading packets, scratch files, logs, or embedded secrets. Generalized paraphrases must not masquerade as exact quotes. |
| Release | Verify the complete artifact, including card, filenames, metadata, and combinations across cases and prior releases. Re-review any changed bytes. |

Apply detectors locally only when data access is authorized. Record detector/version/language/threshold coverage and manually assess omissions and over-redaction on a labeled sample. Do not query public search engines with private phrases to test searchability. An authorized contextual review can use a bounded local reference corpus; lack of a match only describes that corpus. Do not claim a formal privacy parameter, differential privacy, or anonymity without a separately specified and validated mechanism.

## Require separate gates

1. **Source gate:** record permitted sources, purpose, access, retention/deletion responsibility, and any third-party rights restrictions. An archive export is not proof of permission to redistribute its speakers' content.
2. **Evidence gate:** a reviewer other than the extractor checks event links, attribution, scope, counterexamples, and observed versus claimed outcomes. Every proposed lesson needs source support; abstentions are valid.
3. **Privacy gate:** a different reviewer checks every proposed release record and the combined release for direct and contextual disclosure. Record findings, transformations, utility loss, exclusions, reviewer, revision/hash, and residual uncertainty. Any unresolved disclosure finding blocks the affected release.
4. **Evaluation gate:** an independent custodian checks grouped splits and access isolation. Held-out histories, labels, future corrections, and rubrics stay unavailable to induction, context selection, and the acting model. Reviewer decisions about test cases cannot silently update candidate lessons. Use the frozen metrics and ablations in [STRATEGY.md](../STRATEGY.md).
5. **Release gate:** approve the exact local manifest and card before any separately authorized upload. Hash changes invalidate approval. Approval for curation does not authorize publication or registry/global-setting changes.

Measure source-link coverage, attribution errors, unsupported success claims, privacy findings, exclusions, and disagreement with denominators. Require 100% review of released records and zero unresolved findings. These are workflow gates; they cannot measure all undiscovered leakage. Preserve unknown outcomes and disclose missing coverage rather than selecting only easy successes.

## Prepare and verify a private Hub release

This is a future procedure, not authorization to execute an upload.

The card must describe intended/excluded uses, generalized schema, collection and selection methods, domain/outcome counts, source rights or unresolved restrictions, transformations, residual reidentification risk, reviewer process, split grouping, known contamination limits, unknown-outcome treatment, retention/contact process, version, and actual model-run status. Choose license metadata only after rights review. Do not include private source paths or identifying examples. Supplied public dataset names remain provisional until repository/revision/license checks; public benchmark results cannot establish user-specific effectiveness.

Create an empty dataset repository with explicit private visibility, or inspect an authorized existing destination before mutation. Stop if its owner, access, or privacy state differs from the approved destination. Enumerate exact staging files and upload only those files; never point folder upload at the project root or raw private directory. Hold evaluation grading packets outside any repository accessible to acting agents, even if it is private.

After upload, inspect remote visibility and the full file list at the returned commit revision; retrieve the approved files to private verification storage and compare their bytes/hashes to the manifest. Unexpected files or mismatches mean delivery is unverified and require investigation. Record authenticated access and an unauthenticated denial check without treating a denial alone as proof of complete protection. Local packaging, remote transfer, and remote verification each need their own status. Credentials, global settings, and private content are outside this documentation task.
