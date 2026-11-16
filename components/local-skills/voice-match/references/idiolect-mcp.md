# Optional Idiolect integration

Use an already configured, authenticated Idiolect service when the active task authorizes it. Resolve the actual available tools from the host.

The retained local workflow can use tools such as `get_my_voice`, `score_voice`, `rewrite_in_voice` and `draft_in_voice` when the installed service exposes them. Read the current tool contract and source-use requirements before invoking it.

An external profile is optional. Authorized local writing samples and the current task remain available for source-based drafting. Keep private samples, identifiers and profile configuration outside the plugin.

Creating a remote profile or uploading samples requires authorization for those source materials and that provider. A similarity score measures the service's stated criterion and needs interpretation alongside meaning, attribution and audience checks.
