# Security and environment

Load this when changing settings, telemetry, URLs, or archives.

- Never log full settings JSON (`nexusModsApiKey`). Strip new secret fields from verbose logs.
- Never log secret values.
- URL allow-list: `https://`, `http://`, `mailto:` only.
- Archive extract through `PathHelper.TryGetZipSafeArchiveEntryExtractPath`.
- SFX: `ArchiveHelper.IsPotentialSevenZipSFX` (MZ header) before running an `.exe`.
- Telemetry: both `IsEnabled` and `UserConsented`. Signing: `KOTORMODSYNC_SIGNING_SECRET`, then `telemetry.key`, then embedded key only with `OFFICIAL_BUILD`.
- Unix `settings.json` must be `chmod 600`.
- Relay fallback `admin:adminadmin` is local Docker only.

`OFFICIAL_BUILD` is release-pipeline only. Never for dev/PR.
