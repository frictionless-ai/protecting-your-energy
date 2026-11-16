# ChangeEdit `changes.ini` Reference

## Observation Boundary

This reference covers the `changes.ini` section and key shapes that ChangeEdit explicitly reads and writes. It is a ChangeEdit-supported surface reference, not a claim to document every external TSLPatcher extension.

## Escaping and Storage

- `TST_IniFile.WriteString` converts line feed to `<#LF#>` and carriage return to `<#CR#>` before writing.
- `TST_IniFile.ReadString` and `ReadSectionValues` convert those tokens back to real control characters when loading.
- Do not rename or reinterpret these tokens.

## Fixed Top-Level Sections

ChangeEdit pre-creates these headings when starting a new file:

```ini
[Settings]

[TLKList]

[InstallList]

[2DAList]

[GFFList]

[CompileList]

[SSFList]
```

## `[Settings]`

Common keys written by `UMainForm.pas`:

| Key | Type | Notes |
| --- | --- | --- |
| `WindowCaption` | string | optional |
| `ConfirmMessage` | string | optional |
| `LogLevel` | integer | index from the UI |
| `InstallerMode` | bool via `WriteBool` | installer mode toggle |
| `BackupFiles` | bool via `WriteBool` | backup toggle |
| `PlaintextLog` | bool via `WriteBool` | fallback log style |
| `Required` | string | optional required-file name |
| `RequiredMsg` | string | optional required-file message |
| `LookupGameFolder` | bool via `WriteBool` | game-folder lookup toggle |
| `LookupGameNumber` | integer | `1` or `2` |
| `SaveProcessedScripts` | bool via `WriteBool` | debug-script toggle |

Use strings and integers directly. For booleans, mirror nearby repo examples or let ChangeEdit serialize them.

## `[TLKList]`

`TLKList` maps symbolic token keys to dialog.tlk string references.

```ini
[TLKList]
StrRef0=12345
StrRef1=67890
```

- Keys follow `StrRefN`.
- Values are dialog.tlk string references.

## `[2DAList]` and 2DA File Sections

Top-level list section:

```ini
[2DAList]
Table0=appearance.2da
Table1=baseitems.2da
```

- Keys follow `TableN`.
- Values are 2DA filenames.

Per-file section:

```ini
[appearance.2da]
AddRow0=appearance_add_row
ChangeRow0=appearance_change_row
CopyRow0=appearance_copy_row
AddColumn0=appearance_add_column
```

- `AddRowN`, `ChangeRowN`, `CopyRowN`, and `AddColumnN` point to modifier sections.

### `AddRow` modifier section

```ini
[appearance_add_row]
ExclusiveColumn=label
label=my_new_row
race=0
```

- Section keys are column labels plus any token assignments.
- `ExclusiveColumn` is optional.
- `2DAMEMORY#` keys may appear when a modifier stores a memory token.
- Row-modifier values may also reference `StrRefN`, `2DAMEMORY#`, or `high()` tokens already available in the file.

### `ChangeRow` modifier section

```ini
[appearance_change_row]
RowIndex=15
modeltype=B
label=my_override
```

- The first identifier key is one of `RowIndex`, `RowLabel`, or `LabelIndex`.
- Remaining keys are changed column labels.
- `ChangeRow` keeps the identifier key first and then writes only the changed column keys.

### `CopyRow` modifier section

```ini
[appearance_copy_row]
RowLabel=commoner
ExclusiveColumn=label
NewRowLabel=commoner_copy
```

- The first identifier key is one of `RowIndex`, `RowLabel`, or `LabelIndex`.
- `ExclusiveColumn` is optional.
- `NewRowLabel` is optional.
- Remaining keys are copied or overridden column values.
- `CopyRow` values may also use helper values such as `high()` and `inc(#)`.

### `AddColumn` modifier section

```ini
[appearance_add_column]
ColumnLabel=NewColumn
DefaultValue=****
I0=value_for_row_0
I1=value_for_row_1
```

- `ColumnLabel` and `DefaultValue` are the header keys.
- Row-specific initial values use `I<row-index>`.
- `****` is the sentinel ChangeEdit preserves for "do not modify this cell".

## `[GFFList]` and GFF File Sections

Top-level list section:

```ini
[GFFList]
File0=example.utc
File1=example.uti
```

- Keys follow `FileN`.
- Values are GFF-family filenames.

Per-file section supports both direct field edits and nested modifier sections:

```ini
[example.utc]
!Destination=my_module.mod
TemplateResRef=my_resref
LocalizedName(strref)=12345
LocalizedName(lang0)=My Name
AddField0=example_new_field
```

- `!Destination` is optional and omitted for `override`.
- `!ReplaceFile` is optional and toggles overwrite-before-modify behavior.
- Direct field edits use path-like keys.
- Localized strings use `(<suffix>)` forms such as `(strref)` and `(langN)`.
- `AddFieldN` points to a nested field-definition section.

Nested field-definition section:

```ini
[example_new_field]
FieldType=ExoString
Path=InventoryList\0
Label=Tag
Value=my_tag
2DAMEMORY1=!FieldPath
```

Structured field sections use these families:

- Always: `FieldType`, `Label`
- Top-level field sections: `Path`
- Scalar fields: `Value`
- Localized string fields: `StrRef`, `langN`
- Struct fields: `TypeId`
- Nested field references in parent sections: `AddFieldN=<child-section>`
- Memory-token helpers: `2DAMEMORY#=ListIndex` or `2DAMEMORY#=!FieldPath`

## `[InstallList]` and Install Folder Sections

Top-level list section:

```ini
[InstallList]
install_folder0=override
install_folder1=modules
```

- Keys follow `install_folderN`.
- Values are destination folders.

Each folder section then lists files:

```ini
[install_folder0]
File0=my_file.tga
Replace1=my_existing.utc
```

- `FileN` copies a file into the target folder.
- `ReplaceN` marks a replace-style install entry.

## `[CompileList]` and Script Sections

Top-level list section:

```ini
[CompileList]
File0=k_ai_master.nss
```

- Keys follow `FileN`.
- Values are source script filenames.

Optional per-script section:

```ini
[k_ai_master.nss]
!Destination=my_module.mod
```

- `!Destination` is optional and omitted for `override`.

## `[SSFList]` and SSF File Sections

Top-level list section:

```ini
[SSFList]
File0=example.ssf
Replace1=example_replace.ssf
```

- Keys follow `FileN` or `ReplaceN`.
- Values are SSF filenames.

Per-file section:

```ini
[example.ssf]
BattleCry1=StrRef0
Select1=2DAMEMORY0
```

- Keys are sound-entry names.
- Values are usually `StrRefN` or `2DAMEMORY#` tokens loaded from earlier sections.

## Related but Separate

- `namespaces.ini` is managed by `UNamespaceForm.pas` and is not part of the main `changes.ini` structure.
- If a request is really about namespace setup files, do not force it into the sections above.
