# Textual UI threat analysis (unreleased)

The UI uses the same D2FA v1 format, Argon2id, AES-GCM, loader validation,
size/type limits, revision checks and atomic publication as the CLI. There is
no format migration or change to cryptographic parameters or the common
cross-platform security standard. The Watch repository needs no corresponding
standard update for these UI changes.

## Assets and boundaries

Passwords, provisioning keys, decrypted entries, generated codes and existing
vault/backup files are the assets. Untrusted inputs include form values,
provisioning URIs, account labels, paths and encrypted files. The UI is a local
presentation layer, not a new trust boundary against a compromised host.

- Authentication: the UI keeps decrypted entries while unlocked, but does not
  store the password in the app. Five minutes without input triggers an
  automatic lock using monotonic time; timer updates do not extend the session.
  It cancels open forms and clears their secret fields, and defers locking until
  any active file operation has completed. Every mutation, backup and export reauthenticates.
  Unlock, creation and import are explicit actions. Supplied startup credentials
  are still exposed to the usual command-line/password-file risks.
- Accidental replacement: creation/import/export are create-only unless the
  user explicitly selects overwrite. Import is whole-vault replacement, not a
  merge. Removal requires a row selection, password and confirmation checkbox.
  Export/import reject source aliases and destination symlinks. Backups choose
  the next filename and publish create-only.
- Stale state: authenticated file revisions must match the displayed snapshot.
  Mutations use a copy retaining the original revision; Vault.save performs its
  final optimistic check under the publication lock. A failed mutation cannot
  alter the displayed data. Forced creation/import intentionally replace data
  and remain outside the optimistic mutation contract.
- Ambiguity: UI actions identify explicit original rows, even after search.
  Rename retains the Vault's collision checks and explicit index selection.
  Removal deletes only the explicitly selected row, including legacy duplicates;
  this differs from a name-based CLI selector without guessing among matches.
- Responsiveness: KDF, file access, password evaluation and clipboard calls run
  outside the event loop. A busy form prevents cancellation/quit during its
  write. OS termination or a crash can still interrupt the application; existing
  storage durability limitations apply. Post-publication errors require reload,
  not an assumption that the previous file was restored.
- Output: dynamic labels use literal rendering. Secret/password/URI inputs are
  masked, then cleared on submission/cancellation. Exception classification
  omits input values and evaluator feedback. Unexpected Textual errors produce
  a generic message instead of a traceback containing locals. The capture tool
  uses only temporary synthetic data and a stub clipboard.
- Codes: generation and remaining validity use the same timestamp and each
  entry's parameters. Period rollover refreshes the visible code, without
  changing the clipboard. Copy-only hides the code. A late clipboard result
  cannot restore codes after a lock, filter/selection change or new generation.
  If a slow clipboard operation crosses expiry it asks the user to copy again.

## Residual risks

An unlocked UI holds decrypted entries in Python objects. Manual/automatic locking and
exit release references, not guaranteed memory erasure. Masking cannot protect
against malware, screen recording, terminal capture, input-method history,
clipboard monitoring or memory inspection. The clipboard is not automatically
cleared. Python/Textual may temporarily retain input values in queued messages.
Do not treat clearing a widget as forensic erasure.

The filesystem checks do not defend against hostile directory component
replacement, rollback, external tools or older writers. In particular, importing
and creating with explicit overwrite are intentional full replacements. A
correct password and valid AES-GCM payload do not prove a backup is the newest.
See [the security model](SECURITY.md) and [persistence limits](persistence.md).

The tests exercise wrong passwords, invalid input, stale writers, I/O refusal,
password policy, period boundaries, duplicate selection, lock/copy interaction,
masked forms and full recovery flows. They are regression evidence, not a
security audit or certification. Native clipboard and terminal behavior on
all platforms require separate validation; headless captures do not prove it.
