# Wizard pages and controls

Load this when driving the GUI by control name.

## Page order

1. `LoadInstructionPage`
2. `WelcomePage`
3. optional `PreamblePage`
4. `ModDirectoryPage`
5. `GameDirectoryPage`
6. optional `AspyrNoticePage`
7. `ModSelectionPage`
8. `DownloadsExplainPage`
9. `ValidatePage`
10. `InstallStartPage`
11. `InstallingPage`
12. `BaseInstallCompletePage`
13. `FinishedPage`

Widescreen pages are injected later if needed.

## High-signal flow

1. Launch with preload args.
2. `ModSelectionPage` → `SelectAllButton` for full-build stress.
3. Downloads → Fetch Downloads.
4. `ValidatePage` → Run Validation; expand the log; capture the summary.
5. Install only if validation is acceptable for the task.

## Control names

`ModSelectionPage`: `SelectAllButton`, `DeselectAllButton`, `SelectByTierButton`, `SelectByCategoryButton`, `SearchTextBox`, `CategoryFilterComboBox`, `TierFilterComboBox`, `SpoilerFreeToggle`, `ExpandCollapseAllButton`.

`ValidatePage`: `ValidateButton`, `ValidationProgress`, `LogExpander`, `LogText`, `SummaryText`, `SummaryDetails`, `ErrorCountBadge`, `WarningCountBadge`, `PassedCountBadge`.
