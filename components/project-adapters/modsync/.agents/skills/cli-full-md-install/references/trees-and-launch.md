# Trees and launch

Load this when you are about to start or resume a CLI install.

## Default trees

Set `MODSYNC_HOT_ROOT` and `MODSYNC_ARCHIVE_ROOT` to explicitly selected private locations before using these examples. These variables have no bundled default. Preserve existing live-tree ownership and keep the oracle paths read-only.

| Role | Path |
|---|---|
| K1 Holo live | `$MODSYNC_HOT_ROOT/K1_auto` |
| K1 Holo oracle | `$MODSYNC_HOT_ROOT/K1_manual` — do not write |
| K1 Bio live | `$MODSYNC_HOT_ROOT/K1_ody` |
| K2 Holo live | `$MODSYNC_HOT_ROOT/K2_auto/steamassets` |
| K2 Holo oracle | `$MODSYNC_HOT_ROOT/K2_manual` — do not write |
| K2 Bio live | `$MODSYNC_HOT_ROOT/K2_ody/steamassets` |
| Archives | `$MODSYNC_ARCHIVE_ROOT` |

## Holo launch

```bash
export TMPDIR=$MODSYNC_HOT_ROOT/work/tmp
unset DOTNET_CLI_HOME
dotnet exec <ModSync.Core.dll> install \
  --plaintext -v \
  -i <repo>/mod-builds/content/k1/full.md \
  -g $MODSYNC_HOT_ROOT/K1_auto \
  -s $MODSYNC_ARCHIVE_ROOT \
  --direct-markdown -y --no-managed --non-interactive
```

K2 uses `-g …/K2_auto/steamassets` and `content/k2/full.md`.

## Bio launch

Same argv plus `--patcher-engine=BioPatcher --odypatcher-path vendor/bin/biopatcher`.
