# 🎨 Enhanced CLI UX Specification (Color + Interactive Mode)
*(Fully compatible with Vault Lifecycle Contract)*

This document extends the base UX contract with **presentation‑layer improvements** only.  
No behavioral changes, no new side‑effects, no new vault semantics.

Everything here is **pure UI sugar** layered on top of the existing rules.

---

# 🌈 Color Palette (Rich-compatible)

| Purpose | Color | Example |
|--------|--------|---------|
| Success | green | “Vault created.” |
| Warning | yellow | “No vault found.” |
| Error | red | “Invalid vault password.” |
| Prompt | cyan | “Enter vault password:” |
| Info | blue | “Entry added: GitHub” |
| Headings | bold white | section titles |

Colors are **never required for correctness** — they only enhance readability.

---

# 🧩 Interactive Mode (Optional, Never Implicit)

Interactive mode is allowed **only when arguments are missing**  
AND only for commands where this does not violate the contract.

Example:

```
d2fa add
```

→ Allowed, because vault creation rules remain unchanged  
→ No side‑effects until password is validated  
→ No silent writes

Interactive prompts:

```
[cyan]Name (unique identifier):[/cyan]
[cyan]Issuer:[/cyan]
[cyan]Secret:[/cyan]
```

If user provides arguments:

```
d2fa add GitHub GitHub ABC123
```

→ No interactivity  
→ No prompts  
→ Deterministic output

---

# 🧭 Enhanced UX by State

## 1. **Vault Missing**

### d2fa list

```
[yellow]No vault found.[/yellow]
A new encrypted vault will be created.

[cyan]Enter new vault password:[/cyan]
[cyan]Confirm vault password:[/cyan]

[green]Vault created at <path>.[/green]
[blue]No entries found.[/blue]
```

### d2fa add NAME ISSUER SECRET

```
[yellow]No vault found.[/yellow]
A new encrypted vault will be created.

[cyan]Enter new vault password:[/cyan]
[cyan]Confirm vault password:[/cyan]

[green]Vault created at <path>.[/green]
[green]Entry added:[/green] GitHub
```

### d2fa generate

```
[yellow]No vault found.[/yellow]
Nothing to generate.
```

**No vault is created** — invariant preserved.

---

## 2. **Vault Exists (Password Required)**

### d2fa list

```
[cyan]Enter vault password:[/cyan]

[white bold]Entries:[/white bold]
- GitHub (GitHub)
- AWS (Amazon)
```

### d2fa add NAME ISSUER SECRET

```
[cyan]Enter vault password:[/cyan]
[green]Entry added:[/green] GitHub
```

---

## 3. **Invalid Password**

```
[red bold]Invalid vault password.[/red bold]
```

- No confirmation prompt
- No retries
- No writes
- No state changes

Exactly as required.

---

## 4. **Vault Unlocked (Password Still Required)**

When the vault unlock timeout is active but no password is provided via options:

```
[red]Error: Vault is unlocked but password not provided. Use --password or --password-file.[/red]
```

**Security Enhancement:** Even during the unlock window, password authentication is mandated for every vault access. The unlock timeout requires explicit password provision via `--password` or `--password-file` options.

---

# 📦 Entry Listing (Improved Formatting)

```
[white bold]Stored entries:[/white bold]

[blue]Issuer[/blue]       [blue]Label[/blue]
-----------------------------------------
GitHub       lukas
AWS          root
Google       personal
```

Still deterministic.  
Still pure output formatting.

---

# 🧪 Entry Validation (Non-breaking UX improvement)

If secret is invalid Base32:

```
[red]Invalid secret: not valid Base32.[/red]
Example: ABCDEFGHIJKL2345
```

This does **not** violate the contract — it is a user input validation step.

---

# 🔗 otpauth:// URL Support (Pure UX Convenience)

Allowed:

```
d2fa add "otpauth://totp/GitHub:lukas?secret=ABC123&issuer=GitHub"
```

CLI extracts:

- issuer  
- label  
- secret  

This is **pure parsing**, no behavioral change.

---

# 🧹 Error Messages (Improved Clarity)

### Before:

```
Missing argument 'ISSUER'.
```

### After:

```
[red]Missing argument: ISSUER[/red]

Usage:
  d2fa add NAME ISSUER SECRET

Example:
  d2fa add GitHub GitHub ABCDEFGHIJKL1234
```

Still deterministic.  
Still no side‑effects.

---

# 🧠 UX Invariants (Reaffirmed)

All enhancements respect:

- Vault creation is always announced  
- Password confirmation only during creation  
- Wrong passwords never trigger writes  
- Output is deterministic  
- No silent side‑effects  
- No behavioral changes  

This is **presentation only**.

---

# 🚀 Implementation Notes

To implement this UX, you can use:

- **Rich** for colors, tables, prompts  
- **Typer** for CLI structure  
- **typer.RichHelpFormatter** for help output  
- **typer.Option(prompt=...)** for interactive mode  
- **custom Base32 validator** for secrets  
- **otpauth URL parser** (tiny function)

---

# ⚠️ Vault Format Change (0.6.0)

Starting with desktop‑2fa 0.6.0, vaults created with versions prior to 0.6.0 are not compatible and will be rejected as "unsupported format".  
Users must initialize a new vault using `d2fa init-vault`.  
See README.md for full details.

---

# 🔄 Rename Command — Duplicate Detection

The `rename` command enforces deterministic behavior when multiple entries match the target name:

- If **multiple entries** match the provided name (issuer or account_name), the rename is **aborted**
- Error message: `[red]Error: Multiple entries named '<name>' exist. Operation aborted. Resolve duplicates first.[/red]`
- No entry is renamed in this case
- This check occurs **before** any mutation

This ensures predictable behavior when working with vaults that contain duplicate names from older versions.
