# ChangeEdit Modal Dialog Reference

This reference is for new top-level modal dialogs that join the startup-created form list in `ChangEd.dpr`.

## Defaults

- Unit name: `U<Name>Form`
- Form class: `T<Name>Form`
- Global form instance: `<Name>Form`
- DFM root object: `<Name>Form: T<Name>Form`

## Checklist

1. Create `U<Name>Form.pas` and `U<Name>Form.dfm`.
2. Add a getter-backed property for the dialog result.
3. Add `FormShow` and focus the primary input there.
4. Set the OK/Cancel buttons to close the dialog with `mrOk` and `mrCancel`.
5. Add the unit and `Application.CreateForm` call in `ChangEd.dpr`.
6. Call the dialog from `UMainForm` with `ShowModal = mrOk`.
7. Use `ShowAlertBox` when the dialog needs input validation.

## Pascal Template

```pascal
unit UExampleForm;

interface

uses
  Windows, Messages, SysUtils, Classes, Graphics, Controls, Forms, Dialogs,
  StdCtrls, ExtCtrls;

type
  TExampleForm = class(TForm)
    Panel1: TPanel;
    lblTitle: TLabel;
    edValue: TEdit;
    btnOK: TButton;
    btnCancel: TButton;
    procedure FormShow(Sender: TObject);
  private
    function GetValue() : string;
  public
    property Value : string read GetValue;
  end;

var
  ExampleForm: TExampleForm;

implementation

{$R *.DFM}

function TExampleForm.GetValue() : string;
begin
    result := edValue.Text;
end;

procedure TExampleForm.FormShow(Sender: TObject);
begin
    edValue.Clear();
    edValue.SetFocus();
end;

end.
```

## DFM Template

```pascal
object ExampleForm: TExampleForm
  Left = 240
  Top = 180
  BorderStyle = bsDialog
  Caption = 'Example'
  ClientHeight = 120
  ClientWidth = 360
  Position = poScreenCenter
  OnShow = FormShow
  object Panel1: TPanel
    Align = alClient
    BevelOuter = bvNone
    TabOrder = 0
    object lblTitle: TLabel
      Left = 16
      Top = 16
      Caption = 'Enter value'
    end
    object edValue: TEdit
      Left = 16
      Top = 40
      Width = 329
      TabOrder = 0
    end
    object btnOK: TButton
      Left = 189
      Top = 80
      Width = 75
      Caption = 'OK'
      Default = True
      ModalResult = 1
      TabOrder = 1
    end
    object btnCancel: TButton
      Left = 270
      Top = 80
      Width = 75
      Caption = 'Cancel'
      Cancel = True
      ModalResult = 2
      TabOrder = 2
    end
  end
end
```

## `ChangEd.dpr` Registration Snippet

```pascal
uses
  Forms,
  UMainForm in 'UMainForm.pas' {MainForm},
  UExampleForm in 'UExampleForm.pas' {ExampleForm};

begin
  Application.Initialize;
  Application.CreateForm(TMainForm, MainForm);
  Application.CreateForm(TExampleForm, ExampleForm);
  Application.Run;
end.
```

## `UMainForm` Call-Site Snippet

```pascal
ExampleForm.Caption := 'Specify value';

if (ExampleForm.ShowModal = mrOk) then begin
    sValue := ExampleForm.Value;
end;
```

## Existing Anchors

- `UFormFilename.pas` for a simple getter-backed dialog with `FormShow`
- `UModLabelForm.pas` for a minimal input dialog with `SetFocus`
- `ChangEd.dpr` for the startup-created form list
- `UMainForm.pas` for `ShowModal = mrOk` call sites
