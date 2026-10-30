# Cryptographic Design

This document describes the vault format and cryptographic operations currently
implemented by Desktop-2FA. It is an implementation description, not a security
certification or a guarantee that future releases will preserve this format.

## Summary

The application derives a 256-bit key from the vault password with Argon2id and
encrypts the serialized vault with AES-256-GCM. The vault is stored locally; the
application has no server-side password verifier or key recovery service.

## Algorithms and parameters

### Key derivation

The implementation calls Argon2id through `argon2-cffi` with:

| Parameter | Value |
|-----------|-------|
| Variant | Argon2id |
| Version | 19 (Argon2 1.3) |
| Time cost | 4 |
| Memory cost | 131,072 KiB (128 MiB) |
| Parallelism | 2 |
| Output length | 32 bytes |
| Salt | 16 random bytes per save |

The password is encoded as UTF-8 before derivation. These parameters make
password guessing more expensive, but do not make a weak or reused password
safe. Derivation time varies by hardware and system load; this project does not
claim a fixed time per attempt or a specific attack cost.

CLI password-file decoding is an input rule, not a KDF or vault-format change:
files must be strict UTF-8 without BOM and may have one final LF or CRLF, which
is removed. Spaces, tabs and Unicode are otherwise preserved without
normalization; API/prompt strings are unchanged. Invalid files fail explicitly,
and failed authentication never triggers a second, trimmed password attempt.
The same intended password therefore reaches Argon2id as the same UTF-8 bytes.
Older locale-dependent `.strip()` input is described in the
[compatibility notes](./user_manual.md#password-file-format-and-compatibility).

### Encryption

Vault data is encrypted with AES-256-GCM using the 32-byte derived key and a
fresh 12-byte nonce generated with `os.urandom()` for each save. The
`cryptography` AES-GCM API appends a 16-byte authentication tag to the
ciphertext. No associated authenticated data (AAD) is supplied.

AES-GCM provides confidentiality and detects modifications to the encrypted
payload, subject to the security of the key and correct nonce use. Random
nonces and salts make accidental reuse unlikely, not mathematically impossible.

## Vault format, version 1

The serialized file is laid out as follows:

| Offset | Size | Content |
|--------|------|---------|
| 0 | 4 bytes | Magic value: ASCII `D2FA` |
| 4 | 1 byte | Format version: `0x01` |
| 5 | 16 bytes | Argon2id salt |
| 21 | 12 bytes | AES-GCM nonce |
| 33 | Variable | Encrypted JSON followed by the 16-byte GCM tag |

The encrypted JSON represents the vault data model, including its entries and
vault data version. The nonce, ciphertext, and tag are produced by the
AES-GCM implementation as one blob after the magic, format version, and salt.

Loading currently accepts only the `D2FA` magic and format version `0x01`.
There is no migration path in the current loader for older files that lack this
header, nor support for other format versions.

### TOTP secret text

TOTP secret decoding is shared across input validation and code generation.
It accepts ASCII Base32 letters in either case, ignores ASCII spaces, and
accepts omitted padding or correct trailing padding. Other whitespace,
non-ASCII characters and incorrect/interior padding are rejected for new
entries and generation. New entries use canonical uppercase padded Base32;
this re-encodes the same decoded bytes without truncating or replacing keys.

Stored-model validation preserves existing secret text, including historical
empty strings and Unicode strings admitted by the old `str.upper()` validator.
That Unicode fallback validates only historical model compatibility; it never
supplies folded bytes to the generator. Empty and non-ASCII keys cannot
generate codes. Such entries can be listed and explicitly replaced through
the CLI without making other valid entries inaccessible. See the
[repair procedure](./user_manual.md#legacy-invalid-totp-secrets).

### Save and load

On save, the application serializes the vault to UTF-8 JSON and validates that
exact snapshot using the loader's model. It rejects output exceeding 10 MiB
(10,485,760 bytes), counting the JSON bytes plus 49 bytes for the header, salt,
nonce and authentication tag. JSON escaping and multibyte UTF-8 characters
are included in that count. Validation happens before key derivation or any
filesystem changes. Invalid or oversized data raises `VaultValidationError`
(a `ValueError` and `VaultError` subclass) without replacing the existing file.
The same model rules preserve supported legacy entries; no migration is needed.

After validation, the application generates a 16-byte salt, derives a key,
encrypts the validated JSON with AES-GCM using a random 12-byte nonce, and
writes the header and encrypted blob to a temporary file before replacing the
destination.

`Vault.save(path, password, *, overwrite=True)` retains the existing replacement
behavior for normal saves. Export uses `overwrite=False` by default: after the
same validation, encryption and temporary-file flush, `os.link` publishes the
complete file only if the destination is absent, then the temporary name is
removed. An existing destination raises `ExportRefused` (a `ValueError` and
`VaultError` subclass). Unsupported hard links raise `VaultIOError`; there is
no unconditional replacement fallback. Explicit `export --force` selects
replacement after refusing source aliases and destination symbolic links.
No binary layout, KDF, password encoding or migration changes are involved.

Instances returned by `Vault.load` remember a SHA-256 digest of the exact
encrypted bytes read. After each successful save, that destination's revision
is remembered too. Before replacement, save acquires a nonblocking OS lock on
the persistent empty `.NAME.lock` sidecar, compares the current encrypted file
with the remembered revision, and only then replaces it. A mismatch or busy
lock raises `VaultConflict` (a `VaultError` and `ValueError`); CLI status is 6.
This optimistic check covers the read-modify-write operation without holding
a lock across password prompts or key derivation. Reload and reapply the
intended change after a conflict; passwords are never retried automatically.

Canonical paths and file-identity checks associate path aliases with the
remembered revision. File symlinks and multiply linked targets are refused
for writes; directory symlinks resolve to the same lock. Read-only loading is
unchanged. A freshly constructed `Vault(data).save(..., overwrite=True)` or a
save to a distinct new destination has no remembered revision: this remains
an explicit full replacement API, serialized under the publication lock.
Callers performing mutations must load the destination first rather than
reconstruct a `Vault` from copied data. CLI initialization/import without
`--force`, add/list creation, backups and ordinary exports use create-only
publication. Explicit forced replacement remains deliberate replacement.
The `create_vault` helper is also create-only; callers that intentionally reset
a vault must use the explicit replacement API instead of this creation helper.

On load, it checks that the path is a regular file and reads at most 10 MiB. It
then checks the magic and format version, derives the key from the supplied
password and stored salt, decrypts the blob, and validates the JSON as vault
data.

The header is not supplied to AES-GCM as AAD. The magic and version are checked
by the parser, and the salt is used for key derivation; the format does not
provide a separate authenticated-header mechanism.

## Security properties and limitations

- **Confidentiality:** A copy of the vault does not reveal its plaintext
  entries without a successful guess of the non-empty password used to save
  it, assuming the cryptographic libraries and the user's system are
  trustworthy. The public `Vault.save()` and `Vault.load()` API now require an
  explicit, non-empty password; omitting it raises `TypeError`, and an empty
  string is rejected.
- **Payload integrity:** AES-GCM detects modifications to the encrypted
  payload. A wrong password or modified encrypted payload fails AES-GCM
  authentication and raises `InvalidPassword`. `CorruptedVault` is raised
  only after successful decryption when the JSON or vault model fails
  validation.
- **No rollback protection:** An attacker able to replace the file can restore
  an older valid copy. There is no monotonic counter or freshness check.
- **No forward secrecy:** Re-encrypting a vault does not use a ratcheting key
  scheme. A later compromise of the password and an available vault copy may
  expose the entries in that copy.
- **No online lockout:** Password verification is performed locally. There is
  no server-side rate limit or failed-attempt lockout, so a stolen vault can
  be attacked offline.
- **Password strength checks are not universal:** The CLI's zxcvbn strength
  enforcement runs for passwords entered through interactive creation or
  change-password prompts. Passwords supplied with `--password` or
  `--password-file` bypass those creation/change checks. An optional warning
  for existing passwords may still evaluate them during `d2fa vault unlock`
  when `security.warn_on_weak_existing_passwords` is enabled.
- **Memory and host protections:** Python does not guarantee that password or
  key material is securely erased from memory. The application does not
  protect against malware, a compromised operating system, or observation of
  decrypted entries and generated codes.

## Dependencies and standards

The implementation uses `argon2-cffi` for Argon2id and `cryptography` for
AES-GCM. These algorithms are specified in RFC 9106 and NIST SP 800-38D
respectively; AES is specified in FIPS 197. TOTP generation is implemented
separately and follows the algorithm described in RFC 6238. Use of these
algorithms does not by itself mean the application is certified or compliant
with a particular security standard.

## Compatibility

The current loader supports vault format version 1 only. The version byte
allows a future implementation to distinguish formats, but does not guarantee
that future releases will support every older format. Back up the vault before
upgrading. Vaults from releases before the versioned `D2FA` format are not
accepted by the current loader; their contents must be recovered from another
backup or re-created from the original TOTP providers.

Earlier versions of the Python API allowed callers to omit the password,
creating a vault encrypted with an empty password. The current API rejects
omitted and empty passwords, so those passwordless API-created vaults cannot
be opened by this release. If such a vault contains data you need, use the
previous release to open and re-save it with a non-empty password before
upgrading.

## Contact

For security vulnerabilities, email
[security@desktop-2fa.org](mailto:security@desktop-2fa.org). For general
questions or support, email
[contact@desktop-2fa.org](mailto:contact@desktop-2fa.org).
