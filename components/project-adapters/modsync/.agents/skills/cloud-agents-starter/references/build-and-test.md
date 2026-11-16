# Build and test (headless)

Load this when running Cloud-style build/test.

```bash
git submodule update --init --recursive
dotnet build ModSync.sln --configuration Debug
./scripts/agents/run_headless_tests.sh
```

CLI: `dotnet run --project src/ModSync.Core/ModSync.Core.csproj -f net10.0 -- validate -i path/to/instructions.toml`

Single-test duration classify: see `.cursorrules` PowerShell wrapper (120s / 600s). Do not time-limit multiple tests at once.

| Filter | Use |
|---|---|
| `FullyQualifiedName!~LongRunning` | Default |
| `FullyQualifiedName~GuiSmokeHeadlessTests` | Avalonia smoke |
| `FullyQualifiedName~Headless\|FullyQualifiedName~GuiSmoke` | Combined wrapper |

CI runs named subsets, not the whole project. See `docs/knowledgebase/ci-test-matrix.md`.
