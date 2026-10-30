# Security Model

This document summarizes the security properties and limitations of the
currently implemented Desktop-2FA application. It is not an independent audit,
certification, or guarantee that every deployment is secure.

## What the application does

- Stores TOTP entries in a local encrypted vault; there is no cloud vault or
  server-side password verifier.
- Experimental external adapters parse selected plaintext files locally and
  validate their TOTP outputs. They are not wired into CLI import, do not decrypt
  foreign encrypted backups, and abort on malformed/unsupported OTP records.
  Their error messages exclude export contents. See [adapter limits](import_adapters.md).
- Accepts only encrypted payload schema 1. Unknown schema versions and unknown
  vault/entry fields are refused before mutation or re-save, preventing silent
  metadata loss. Refusal does not alter the original file; no automatic format
  downgrade, metadata stripping or recovery is attempted.
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
by the creation/change enforcement flow. However, if
`security.warn_on_weak_existing_passwords = true`, `d2fa vault unlock` also
evaluates the existing password and warns when its zxcvbn score is below 3,
including passwords supplied with those options. The score estimates
guessability; it is not an entropy guarantee or proof that a password will
resist attack. The `--allow-weak-passwords` flag and
`D2FA_ALLOW_WEAK_PASSWORDS=1` environment variable bypass the interactive
creation/change strength check.

The public `Vault.save()` and `Vault.load()` API require an explicit, non-empty
password. Omitting the argument raises `TypeError`; passing an empty string
raises `ValueError`. Earlier versions allowed the API to create vaults with an
empty password. Such vaults must be opened and re-saved with a non-empty
password using the previous release before upgrading; the current API will not
open them.

Password files use strict UTF-8 without BOM and remove exactly one optional
final LF or CRLF. Other spaces, tabs and Unicode are significant. Empty or
malformed files fail before decryption; diagnostic messages omit file contents.
The file reader never retries a stripped, differently decoded or normalized
password after failed authentication, and the selected vault is not rewritten.
Old files read through locale-dependent `.strip()` may need explicit correction
to represent the actual previous password; see the
[compatibility procedure](./user_manual.md#password-file-format-and-compatibility).
The KDF, encrypted format and existing strength-check scope are unchanged.

The password is not stored in the vault. `d2fa vault unlock` only verifies it
for that command; later commands still need a password or interactive prompt.
Avoid `--password` where command-line arguments may be visible to other users
or recorded by tooling.

## TOTP secret entry

Interactive `add` requests its dedicated secret with hidden input, reducing
exposure through normal terminal echo and scrollback. Name and issuer prompts
remain visible. Add success/validation messages omit the key and the complete
provisioning URI. CLI URI errors use a fixed message, since parser exceptions
may contain input. This does not change validation, stored key bytes, encryption
or TOTP parameters.

Positional secret and URI arguments are still supported and may be exposed by
shell history, process inspection or recordings. A URI pasted at the visible
issuer prompt can also be echoed in full. Use a plain issuer plus the dedicated
hidden secret prompt when avoiding these input exposures. Hidden entry does not
protect against keyloggers, a compromised host or process-memory inspection.

## TOTP input and entry selection

TOTP creation and generation reject invalid Base32 and empty decoded keys.
New-input normalization changes only case, ASCII spaces and Base32 padding,
preserving the decoded key bytes; it never folds Unicode into key material.
Stored models retain legacy empty strings and historically admitted
Unicode-folded strings unchanged so the vault can still be listed and valid
entries used. Generation refuses these invalid entries with an explicit error;
no code is computed or copied from an empty or Unicode-folded key. Repair
requires valid provisioning data from the original provider, not a guessed or
automatically substituted key. See the [user manual](./user_manual.md#legacy-invalid-totp-secrets).

Rename resolves an exact account name before an issuer fallback and refuses
ambiguous names without an explicit selector. It checks destination uniqueness
before changing account name or issuer. Legacy duplicates can be repaired with
the one-based numbers from `list --indices` and `rename OLD NEW --index N`;
the chosen entry must match the old name at the selected lookup tier. Secret
bytes and TOTP parameters are preserved without a format migration.

These indices describe current list positions, not persistent identifiers.
They do not protect against concurrent edits between listing and renaming;
avoid concurrent changes and refresh the list after additions or removals.

## Files and backups

Expected CLI failures are classified by exception type and return non-zero
status without printing raw exception data that may contain secrets. Failed
authentication is never treated as a request to initialize an empty vault;
a detected vault that cannot be loaded is not replaced with an empty one.
CLI helper failures propagate a non-zero status instead of a success sentinel.
This improves automation's ability to detect a failed operation; it does not
add concurrency or filesystem durability guarantees.

The application rejects non-regular vault paths and files larger than 10 MiB.
Before saving, it validates the serialized data using the loader's model and
checks the exact output size, including the 49-byte D2FA v1 overhead. Invalid
mutations (such as a zero TOTP period) and oversized output are rejected before
filesystem changes, preserving the previous file. This protects against saving
data the loader would reject; it adds no concurrency or crash-durability guarantee.
When saving, it writes a unique temporary file in the destination directory,
flushes the file, and replaces the destination. This reduces the chance of a
partially written vault but does not protect against filesystem failure,
malicious replacement, or rollback to an older copy.

Encrypted export is create-only by default. Publication uses a hard link to
the fully written temporary file in the destination directory, so a competing
process that creates the destination first keeps its file. Existing targets
cause refusal (CLI status 6); hard-link support is required and failures do
not trigger a replacement fallback. `export --force` explicitly authorizes
replacement of a distinct destination. Source identity is checked using file
identity (covering hard links and path aliases), and destination symbolic links,
including dangling links, are refused even with `--force`. Ordinary vault saves
continue replacing their selected file.

These checks protect against accidental overwrites and competing destination
creation. They do not lock the source or protect against an attacker replacing
path components or file identities during export. Use directories controlled
by the user. Export adds no power-loss guarantee. Temporary-name cleanup is
best effort; an unlink failure can leave
an additional encrypted copy. Export uses fresh salt and nonce, so its bytes
need not match the source even though the contents and password are retained.

For read-modify-write updates, the loaded encrypted snapshot is hashed in
memory. Publication takes a short nonblocking OS lock, checks that the snapshot
is still current, then replaces the file. A stale writer fails explicitly,
including after a password change. Initial CLI creation and backup publication
are create-only. Tests reproduced two successful stale writers losing an
addition before this guard; synchronized regression processes now require an
explicit conflict. This is regression evidence, not an independent audit.

The persistent `.NAME.lock` sidecar contains no vault data or password. Its
inode must remain stable; never remove it while writers may be active. Locks
are released by closing the descriptor, including process exit. A busy lock
fails immediately (status 6) without waiting or retrying a password. File
symlinks and multiply linked targets are refused for writes; directory aliases
share the canonical lock. POSIX uses `flock`; Windows locks one byte with
`msvcrt.locking`. Validate network/removable filesystem lock semantics before
relying on them; these tests cover local CI filesystems only.

The guard coordinates writers running this implementation. Older versions,
external tools, forced full replacements and hostile directory changes are
outside the optimistic mutation contract. A fresh `Vault` has no loaded
revision and remains an explicit replacement API; mutation callers must load
the existing destination. This adds neither rollback protection nor crash
durability guarantees. The file format and cryptography are unchanged.

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

AES-GCM authentication failures (including wrong passwords and modified
encrypted payloads) raise `InvalidPassword`. `CorruptedVault` is raised only
when decryption succeeds but JSON or vault-model validation fails.

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

Report suspected security vulnerabilities privately to
[security@desktop-2fa.org](mailto:security@desktop-2fa.org). Do not open a
public issue or include real vault files, passwords, or TOTP secrets in a
report. For general questions and support, contact
[contact@desktop-2fa.org](mailto:contact@desktop-2fa.org).

---

This document describes the implementation at Desktop-2FA 0.9.0. Review it
alongside the source code for the exact behavior of a particular release.
