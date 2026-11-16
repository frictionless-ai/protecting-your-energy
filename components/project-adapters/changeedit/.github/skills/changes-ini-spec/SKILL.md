---
name: changes-ini-spec
description: Generate and review ChangeEdit-supported TSLPatcher changes.ini entries using the section and key grammar exercised by UMainForm.pas and TST_IniFile. Use when writing or checking Settings, TLKList, InstallList, 2DAList, GFFList, CompileList, or SSFList content in this repository.
disable-model-invocation: true
---

This optional adapter uses the external checkout selected by `PYE_CHANGEEDIT_ROOT`. Read the [bundle index](../../../../INDEX.md) and that checkout’s current instructions. Product paths resolve there.

# ChangeEdit `changes.ini` Spec

Use this skill when an agent needs to write or review `changes.ini` content for ChangeEdit.

## Scope

This skill covers the `changes.ini` surface that ChangeEdit itself reads and writes. If a request depends on a TSLPatcher feature that is not visible in `UMainForm.pas`, `UST_IniFile.pas`, or the form units that edit a section, stop and verify the source instead of guessing.

Before generating INI content:
- Read [reference.md](reference.md).
- Cross-check any nontrivial section against `UMainForm.pas` and `UST_IniFile.pas`.
- If `reference.md` or the referenced source files cannot be read, stop and report which file is missing rather than generating content from memory.

## Rules

1. Preserve parser-visible section names and key families exactly.
2. When code writes the file, use `TST_IniFile`; it owns the newline escape behavior.
3. For file-backed sections, emit both the list entry and the referenced file or modifier section.
4. Reuse the real key families from the repo: `StrRefN`, `AddRowN`, `ChangeRowN`, `CopyRowN`, `AddColumnN`, `FieldType`, `Path`, `Label`, `Value`, `StrRef`, `langN`, `!Destination`, `!ReplaceFile`, `FileN`, `ReplaceN`, and `install_folderN` where applicable.
5. Keep the generated examples aligned with the ChangeEdit UI surfaces: Settings, TLK, 2DA, GFF, Install, Script, and SSF.
6. If the user requests a section or key not enumerated here and not found in `UMainForm.pas` or `UST_IniFile.pas`, refuse to emit it and ask for source confirmation.

## Guardrails

- Do not rename sections or normalize keys to a different style.
- Do not change `<#LF#>` or `<#CR#>` escaping rules.
- Do not treat `namespaces.ini` as if it were part of the main `changes.ini`; it is related but separate.
- If a value format is ambiguous, emit only the verified portion of the snippet and add a follow-up note with bullet points for each unverified key or value format and the source file that must confirm it.

## Deliverables

- A syntactically shaped INI snippet that matches ChangeEdit's supported grammar
- Include a short note about which section or code path the snippet matches whenever the snippet spans more than one section, references a file-backed modifier, or uses keys outside `Settings`
- For review requests, return a list of findings keyed by section or line with a verdict (`valid`, `needs-source-check`, or `invalid`) and the rule violated
