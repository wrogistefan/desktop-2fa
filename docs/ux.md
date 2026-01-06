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
2. Password confirmation is required only when creating a new vault.
3. Invalid passwords must never mutate state.
4. Every command must clearly communicate what is happening.
5. UX describes intent, even if implementation is implicit.
6. All state-mutating operations MUST emit confirmation messages regardless of interactive mode.

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

Vault created at <path>.
No entries found.

d2fa add NAME ISSUER SECRET

No vault found.
A new encrypted vault will be created.

Enter new vault password:
Confirm vault password:

Vault created at <path>.
Entry added: NAME

d2fa generate

No vault found.
Nothing to generate.

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

## UX Invariants

- Vault creation is always announced.
- Password confirmation occurs only during creation.
- Wrong passwords never trigger writes.
- Output is deterministic and testable.

---

## Notes

Current behavior may be transitional while UX is refined.
This document defines the target behavior and serves as the basis
for future refactors and GUI development.

### ⚠️ Vault Format Change (0.6.0)
Starting with desktop‑2fa 0.6.0, vaults created with versions prior to 0.6.0 are not compatible and will be rejected as "unsupported format". Users must initialize a new vault using `d2fa init-vault`. See README.md for full details.

---

## Rename Command — Duplicate Detection

The `rename` command enforces deterministic behavior when multiple entries match the target name:

- If **multiple entries** match the provided name (issuer or account_name), the rename is **aborted**
- Error message: `Error: Multiple entries named '<name>' exist. Operation aborted. Resolve duplicates first.`
- No entry is renamed in this case
- This check occurs **before** any mutation

This ensures predictable behavior when working with vaults that contain duplicate names from older versions.
