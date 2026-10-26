# Security Model

This document summarizes the security properties and limitations of the
currently implemented Desktop-2FA application. It is not an independent audit,
certification, or guarantee that every deployment is secure.

## What the application does

- Stores TOTP entries in a local encrypted vault; there is no cloud vault or
  server-side password verifier.
- Derives a 32-byte key using Argon2id (time cost 4, memory cost 128 MiB,
  parallelism 2, 16-byte salt) and encrypts vault data using AES-256-GCM
  (12-byte random nonce and 16-byte authentication tag).
- Accepts regular vault files up to 10 MiB. Saves are written to a temporary
  file and then replace the selected vault path.
- Requires a password when a CLI operation loads an existing vault. The
  `d2fa vault unlock` command checks the password and reports success; it does
  not create a persistent unlocked session or bypass password entry for later
  commands.

For the exact binary layout, see [crypto.md](./crypto.md).

## Threat model

### Protection provided

If an attacker obtains only a copy of the encrypted vault, AES-GCM protects its
contents from direct reading and detects changes to the encrypted payload.
Argon2id increases the cost of each offline password guess. The random salt
prevents precomputed password tables from being reused directly across vaults.

These controls depend on the user's password, the cryptographic libraries, and
the integrity of the machine on which the application runs. They do not make
weak passwords unguessable or eliminate the risk of offline guessing.

### Not protected against

- Malware, a compromised operating system, keyloggers, or an attacker with
  access to the machine while the vault is open.
- Theft of a password from command-line arguments, a password file, shell
  history, process inspection, or other system tooling. Prefer the interactive
  prompt where available; protect password files with operating-system
  permissions.
- Recovery of passwords or erasure of secrets from Python process memory.
- Clipboard history or other software that observes copied TOTP codes.
- Rollback to an older valid vault file. There is no freshness or
  anti-rollback mechanism.
- Online rate limiting: password checks are local, and the application does
  not impose a failed-attempt lockout.
- Automatic migration of vaults without the current versioned header.

## Password handling

The CLI rejects empty passwords. For interactive creation and password
changes, it evaluates the proposed password with `zxcvbn` and treats scores
below 3 as weak. By default, a weak password triggers a warning and
confirmation; setting `security.reject_weak_passwords = true` in
`~/.config/d2fa/config.toml` rejects it instead.

This strength check is limited to the interactive new-password flow.
Passwords provided through `--password` or `--password-file` are not checked
by `zxcvbn`. The check estimates guessability; it is not an entropy guarantee
or proof that a password will resist attack. The `--allow-weak-passwords` flag
and `D2FA_ALLOW_WEAK_PASSWORDS=1` environment variable bypass the interactive
strength check.

The password is not stored in the vault. `d2fa vault unlock` only verifies it
for that command; later commands still need a password or interactive prompt.
Avoid `--password` where command-line arguments may be visible to other users
or recorded by tooling.

## Files and backups

The application rejects non-regular vault paths and files larger than 10 MiB.
When saving, it writes a unique temporary file in the destination directory,
flushes the file, and replaces the destination. This reduces the chance of a
partially written vault but does not protect against filesystem failure,
malicious replacement, or rollback to an older copy.

The `d2fa backup` command loads and decrypts the source vault, then saves a
separately encrypted backup using the same password. A backup therefore
contains the same secrets and should be protected like the original. Keep
backups in a location protected by operating-system permissions and, where
appropriate, full-disk encryption. Test recovery before relying on a backup.

The application does not explicitly set vault or directory permissions in a
portable way. Review and configure access permissions using the facilities of
your operating system. On Unix-like systems, restrict the vault directory and
file to the account that needs access.

## Cryptographic details

The current vault format has a `D2FA` magic value, one-byte format version
(`0x01`), a 16-byte salt, and an AES-GCM blob containing a 12-byte nonce,
ciphertext, and 16-byte tag. The key derivation and encryption parameters are
described in [crypto.md](./crypto.md).

The format does not use AES-GCM associated data for the header. The parser
checks the magic and version, while the salt is used to derive the key. There
is no separate authenticated-header mechanism, rollback protection, key
ratchet, or forward secrecy.

Cryptographic operations use `argon2-cffi` and `cryptography`; randomness is
obtained through Python's `os.urandom()`. Derivation time depends on the
hardware and system load. This documentation makes no fixed timing or
password-cracking cost claims.

## Standards references

The implementation uses algorithms specified by RFC 9106 (Argon2), NIST
SP 800-38D (GCM), FIPS 197 (AES), and RFC 6238 (TOTP). These references
describe standards; they do not imply that Desktop-2FA has been independently
audited, validated, or certified as compliant.

## Security reporting

Before publishing a suspected vulnerability, check the
[GitHub repository's Security tab](https://github.com/wrogistefan/desktop-2fa/security)
for current reporting instructions. Do not include real vault files, passwords,
or TOTP secrets in a report.

---

This document describes the implementation at Desktop-2FA 0.8.3. Review it
alongside the source code for the exact behavior of a particular release.
