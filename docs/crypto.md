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

### Save and load

On save, the application generates a 16-byte salt, derives a key, serializes
the vault to JSON, encrypts it with AES-GCM using a random 12-byte nonce, and
writes the header and encrypted blob to a temporary file before replacing the
destination.

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
