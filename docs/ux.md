# CLI UX Specification — Vault Lifecycle

This document defines the expected user experience (UX) for the desktop‑2fa
command‑line interface. It describes observable behavior and messaging,
independent of internal implementation details.

The goal is to ensure that all CLI interactions are:
- explicit
- predictable
- deterministic
- free of silent side‑effects

This document is the authoritative UX contract for both CLI and future GUI
implementations.

---

## Core UX Principles

1. Vault creation must never be silent.
2. Interactive creation and password change require confirmation; supplied options do not.
3. Invalid passwords must never mutate state.
4. Every command must clearly communicate what is happening.
5. UX describes intent, even if implementation is implicit.
6. Successful mutations report confirmation; output modes apply only where explicitly supported.

---

## Vault States

- Vault Missing — no vault file exists on disk
- Vault Exists — vault file exists
- Password Required — vault exists but is not yet decrypted
- Password Invalid — incorrect password provided

---

## UX Behavior by State

### State: Vault Missing

d2fa list

No vault found.
A new encrypted vault will be created.

Enter new vault password:
Confirm vault password:

Vault created at <path>
No entries found.

d2fa add NAME ISSUER SECRET

No vault found.
A new encrypted vault will be created.

Enter new vault password:
Confirm vault password:

Vault created at <path>
Entry added: NAME

d2fa code NAME

No vault found.

No vault is created in this case.

---

### State: Vault Exists (Password Required)

d2fa list

Enter vault password:
- EntryName (Issuer)

d2fa add NAME ISSUER SECRET

Enter vault password:
Entry added: NAME

---

### State: Invalid Password

For any command requiring vault access:

Invalid vault password.

- No confirmation prompt
- No side‑effects
- Vault remains unchanged

---

## Interactive Secret Entry

Interactive `add` retains the visible `Name (unique identifier):` and `Issuer:`
prompts. Its dedicated `Secret:` prompt hides input without a second secret
confirmation. This applies when all values are prompted and when only the
secret is missing. Success and validation messages do not reproduce the secret
or the entire provisioning URI. Existing positional arguments remain available.

A URI entered at the visible issuer prompt can still be echoed. For hidden key
entry, use a plain issuer and the dedicated secret prompt; argument-based secrets
and URIs may also be exposed in shell history or process inspection. Hiding
terminal input does not protect against a compromised host.

## URI-based Add

`d2fa add "otpauth://totp/..."` and a URI entered at the interactive issuer
prompt use the same parser and preserve algorithm, digits and period. No
separate secret prompt is shown for a URI. The decoded URI label supplies the
account name; a conflicting issuer query/prefix or separate secret is rejected.
Invalid provisioning data exits with status 6 before vault access and cannot
create a vault or replace an existing one. Omitted optional parameters retain
SHA1/6/30 defaults, and the manual `add NAME ISSUER SECRET` syntax is unchanged.

## UX Invariants

- Vault creation is always announced.
- Password confirmation occurs only during creation.
- Wrong passwords never trigger writes.
- Failed operations return non-zero status even in non-interactive mode.
  Authentication is 2, missing entry 3, missing vault 4 and validation 6;
  I/O/permission, corrupted data and unsupported formats are 1. Required
  clipboard failure remains 5. See the [full contract](user_manual.md#exit-codes).
- Output is deterministic and testable.

### Entry resolution for code generation and removal

`code NAME` and `remove NAME` first match the exact account name. Only when
there is no such match do they fall back to a unique issuer. Matching remains
case-sensitive and independent of entry order. An issuer cannot shadow an
exact account name, including when several accounts share that issuer.

Multiple matches at the selected tier abort the operation with an
`Ambiguous entry` error and exit status 6, without saving or deleting entries,
generating a code, or touching the clipboard. In JSON code mode the error id is
`entry_ambiguous`; quiet mode suppresses its message while retaining the failure
status. Legacy duplicate account names are not automatically repaired.

---

## Notes

Current behavior may be transitional while UX is refined.
This document defines the target behavior and serves as the basis
for future refactors and GUI development.

### Vault compatibility and recovery

The loader accepts the D2FA v1 header and payload schema 1. Supported historical
fixture coverage and unsupported pre-header/empty-password cases are described
in the [manual](user_manual.md#version-compatibility). Never initialize over an
unreadable original as an automatic recovery step.

## Rename Command — Duplicate Detection

Rename uses an exact account name first, then a unique issuer fallback. Multiple
matches at the selected tier are refused with status 6 unless `--index N`
selects a matching entry. The one-based index comes from `list --indices`;
indices can change after edits. An occupied destination is refused before
mutation. Successful rename changes both account name and issuer while
preserving secrets and TOTP parameters. See [duplicate repair](user_manual.md#duplicate-names-in-vault).

## Contact

For questions or support, contact us at contact@desktop-2fa.org

### CLI output streams

`code --json` always renders a single success/error object on stdout (except
explicit help/version actions); option conflicts retain JSON rendering even with
`--quiet`. Raw success contains only the code and a newline. Errors, warnings and
password prompts use stderr. Quiet suppresses both streams while preserving the
exit status; it requires a supplied password/password file instead of prompting.
Duplicate warnings omit record names. `Vault.load()` itself is
silent; callers may inspect `duplicate_account_names` for legacy repair.
