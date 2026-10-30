# External TOTP adapter contract

`desktop_2fa.cli.importers` contains Python helpers, not additional CLI import
modes. `d2fa import` still accepts encrypted D2FA vaults only. Helpers read a
selected UTF-8 export (an optional UTF-8 BOM is accepted), return validated
entry dictionaries, and never persist data or access the default vault.

| Helper | Supported input | Limits |
| --- | --- | --- |
| Aegis | Plaintext envelope v1, `db.entries`, database versions 1/2/3 with known TOTP shape | Requires `info.secret/algo/digits/period`; encrypted inputs and non-TOTP types are refused |
| Bitwarden | CSV with `name` and `login_totp`; optional `login_username` and `type` | Tokens on non-login rows are refused; legacy fabricated `name,totp` is unsupported |
| 1Password | Existing custom CSV variants: `title` and exactly one of `otp` / `one-time password` | No general native-export claim; 1PUX, arbitrary custom columns and other OTP column names are not supported |
| otpauth | TOTP provisioning URI | Uses the shared CLI URI/Base32 policy; HOTP, Steam and unsupported parameters are refused |
| FreeOTP | Existing custom `<tokens><token>` XML with `issuer`, `label`, `secret` | SHA1/6/30 only; extra/nested parameter fields and native encrypted backups are refused |

CSV headers are compared without surrounding whitespace or letter case;
duplicate/ambiguous headers and mismatched row lengths are rejected. Quoted
commas and embedded newlines remain part of the original field values. CSV
rows with no OTP cell are the only records skipped. If no TOTP entries remain,
the helper raises `ImportFormatError`, rather than returning a misleading empty
success. An unsupported or malformed OTP record aborts the entire conversion;
no partial result is returned. Error messages do not echo keys, URIs, passwords
or notes. XML DTD/entity declarations are rejected.

Bare keys are canonicalized with the shared Base32 decoder without changing
their decoded bytes and use SHA1/6/30 defaults. Bare CSV keys use the service
name/title and username (or name/title fallback). URI-valued cells use the
shared URI labels and all specified algorithm/digits/period values; absent
issuer fallback follows that same shared policy. Only SHA1/SHA256/SHA512,
6/7/8 digits and positive periods supported by `TotpEntry` are accepted.

This is TOTP-only conversion: passwords, notes, icons, groups and other export
metadata are not imported. It is distinct from lossless supported D2FA vault
round trips. Existing helper callers that relied on silent skips, invalid raw
keys or empty lists must now handle `ImportFormatError` (a `ValueError`). No
network requests, source-file rewrites, password prompts or decryption of
foreign encrypted backups are added.

The [fixture provenance](../tests/fixtures/imports/README.md) records producer
references, supported and rejected variants, and synthetic test data. The
[1Password export guide](https://support.1password.com/export/) describes
provider variants; their full native support is not inferred from these custom
helper formats. FreeOTP native encryption likewise requires a separate design.
