# Implementation reference

The original engine selected DietrichGebert/ponytail as an implementation reference. Its recorded inspection used commit `e3ba2aa6f1e6f0bc4d69eb09c9f0d0a93af56156` from v4.10.0. This component adapts organizational patterns and retains its own reconstruction workflow.

The reused patterns include one canonical workflow, thin command adapters, standard-library processing, native static controls, source-linked artifacts, explicit limits and separately evaluated correctness and efficiency.

The existing Python modules remain the engine. The plugin adds dispatch and portable configuration around them. Source attribution, quote integrity, recoverable output and behavior through the actual entry point remain requirements.

The original evaluation harness, synthetic fixtures and historical result receipts remain in the source checkout. They are excluded from this runtime inclusion. Prior results require their original scope and do not establish current bundled-runtime acceptance.

[Original reference project](https://github.com/DietrichGebert/ponytail)
