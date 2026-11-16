# Discord account attribution

Social episode mining is intentionally disabled until a private account
attestation names the requesting user's stable Discord account IDs. Display
names, handles, message wording and folder names are not identity evidence.

Create an ignored file such as `private/identity.json` only when the ID is
known from authenticated export metadata or the user has directly verified it:

```json
{
  "schema": "interaction-foundry/private-identity/v1",
  "verification_basis": "user_verified",
  "discord_account_ids": ["12345678901234567"]
}
```

The number in the example is synthetic. The file is not a dataset artifact and
does not by itself prove positive reception; reply linkage, dates and semantic
review remain required.
