# Synthetic external-format fixtures (S14 / #45)

All identities, notes and keys here are synthetic. Keys are public RFC 6238
test-vector bytes, never real exported credentials. Do not use them for accounts.
These files are authored schema examples, not captures from a user's apps.

- `aegis_plain.json`: plaintext envelope/database shape checked against
  [Aegis vault documentation](https://github.com/beemdevelopment/Aegis/blob/d6f4e5925a97e4e91593f1542085eae03432a759/docs/vault.md)
  and its [upstream plaintext fixture](https://github.com/beemdevelopment/Aegis/blob/d6f4e5925a97e4e91593f1542085eae03432a759/app/src/test/resources/com/beemdevelopment/aegis/importers/aegis_plain.json).
  Synthetic entries exercise `info.algo`, non-default parameters and Unicode.
- `bitwarden.csv`: the 11-column schema from the producer's
  [example CSV](https://bitwarden.com/help/authenticator-import-export/#example-exports),
  including `login_totp`. Values were replaced with synthetic RFC keys, a URI,
  quoted multiline names/notes and records without tokens. CSV line endings
  are preserved by the fixture-scoped `.gitattributes`, including embedded CRLF.
- `onepassword_legacy.csv`: the existing helper's custom `title` /
  `one-time password` variant, exercising a provisioning URI. This is **not**
  evidence that the helper supports all native 1Password exports.
- `onepassword_native_subset.csv`: a negative schema projection using native
  CSV field names independently checked against Bitwarden's
  [1Password Windows CSV fixture](https://github.com/bitwarden/clients/blob/96f157b3e73f71b966505f15e6b236ab1298fc73/libs/importer/src/importers/spec-data/onepassword-csv/multiple-items.windows.csv.ts).
  The projection has no supported OTP column and must fail explicitly.
- `freeotp_legacy.xml`: the existing custom `tokens/token` variant, with
  default SHA1/6/30 parameters. It is not a native FreeOTP backup.
- `freeotp_native.xml`: a negative Android shared-preferences XML envelope
  projection with synthetic opaque data. Native FreeOTP 2.x backups are
  [encrypted](https://github.com/freeotp/freeotp-android/blob/master/BACKUP.md)
  and are deliberately unsupported; this fixture is not a decryptable backup.

References inspected on 2026-10-30. Schema provenance is independent of the
adapter implementation; no real vaults or historical D2FA fixtures were used
or regenerated. Unsupported variants are refused rather than inferred from
these minimal examples. Broader native 1Password/FreeOTP support needs new
producer evidence and fixtures first.
