---
name: delphi7-form-scaffold
description: Generate ChangeEdit-style Delphi 7 modal dialog scaffolds, including a U<Name>Form.pas/.dfm pair, ChangEd.dpr registration, and UMainForm ShowModal wiring. Use when adding a new modal dialog, form unit, or startup-registered dialog in this repository.
disable-model-invocation: true
---

This optional adapter uses the external checkout selected by `PYE_CHANGEEDIT_ROOT`. Read the [bundle index](../../../../INDEX.md) and that checkout’s current instructions. Product paths resolve there.

# Delphi 7 Form Scaffold

Use this skill for new top-level modal dialogs in ChangeEdit.

Before drafting code:
- Read `.github/copilot-instructions.md`, `CONVENTIONS.md`, `CONTRIBUTING.md`, `ChangEd.dpr`, and [reference.md](reference.md).
- Mirror an existing simple dialog such as `UFormFilename.pas` or `UModLabelForm.pas` instead of inventing a new pattern.

## Workflow

1. Create both files: `U<Name>Form.pas` and `U<Name>Form.dfm`.
2. Keep the form Delphi 7 and standard VCL only.
3. Expose the result through a getter-backed property.
4. In `FormShow`, clear or preload the primary input and call `SetFocus`.
5. If validation is needed, use `ShowAlertBox` from `UST_Common`, not `ShowMessage`.
6. Register the unit and global form in `ChangEd.dpr` with `Application.CreateForm`.
7. Invoke the dialog from `UMainForm` with `if (<FormInstance>.ShowModal = mrOk) then begin ... end;`.
8. Keep naming, indentation, and variable prefixes aligned with existing Pascal units.

## Guardrails

- Default to the repo's startup-created global form pattern.
- Do not lazy-create new top-level dialogs.
- Do not use modern Delphi features, generics, anonymous methods, or third-party controls.
- Do not mix this pattern with main-form panel toggling; this skill is for modal dialogs only.
- If the request is actually for a nested transient helper form like the recursive subform inside `UFormNewGFF`, inspect that target area before scaffolding.

## Deliverables

- `U<Name>Form.pas`
- `U<Name>Form.dfm`
- `ChangEd.dpr` registration changes
- `UMainForm.pas` call-site snippet when the entry point is part of the request
