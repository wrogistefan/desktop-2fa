# 🔐 Security Policy

## Password Strength Policy

Desktop-2FA includes optional password strength checks using the **zxcvbn** library, which estimates password guessability based on common patterns, dictionary words, sequences, and other attack vectors. Enforcement runs in interactive password creation and change flows; passwords supplied through `--password` or `--password-file` bypass that enforcement. When `security.warn_on_weak_existing_passwords = true`, `d2fa vault unlock` may still evaluate an existing password and display a warning.

### Strength Scoring

zxcvbn returns scores from 0 to 4:

| Score | Classification | Examples | Recommendation |
|-------|-----------------|----------|-----------------|
| 0-2 | **Weak** | `password`, `123456`, `qwerty` | ❌ Not recommended |
| 3 | **Good** | `MyVault#2024`, `Correct-Horse` | ✅ Acceptable |
| 4 | **Excellent** | `Battery-Horse-Staple-Correct`, `unique+complex+long` | ⭐ Ideal |

In the interactive flows that run this check, scores below 3 are treated as weak. The score is an estimate, not a guarantee of resistance to guessing; examples below are illustrative and their actual scores can vary.

### Password Strength Examples

**Weak Passwords (Score < 3):**
- Common words: `password`, `admin`, `vault`, `letmein`
- Patterns: `123456`, `qwerty`, `abc123`, `password123`
- Predictable: `Admin2024`, `Summer2024`, `Vault123`

**Strong Passwords (Score >= 3):**
- Passphrases: `Battery-Horse-Staple-Correct`, `Hunter-Moon-Forest-Echo`
- Complex: `M@xL!nux#2024$Sec`, `VaultKey~!@#ABC123xyz`
- Mixed case + symbols + length: `MySecureV@ult!42`, `Desktop_2FA#OpenSource`

### Configuration

Edit `~/.config/d2fa/config.toml`:

```toml
[security]
# Whether to reject weak passwords (score < 3)
# false (default): Warn but allow user to continue
# true: Reject weak passwords immediately
reject_weak_passwords = false

# Legacy option (deprecated - kept for backward compatibility)
# If set, min_password_entropy is mapped to zxcvbn score >= 3
# min_password_entropy = 60
```

### Enforcement Modes

#### Mode 1: Warning + Confirmation (default)
```
reject_weak_passwords = false
```
When a weak password is entered:
1. A yellow warning message is displayed
2. User is prompted: `Continue with weak password? [y/N]`
3. User can choose to accept the weak password or re-enter

This mode balances security and user flexibility.

#### Mode 2: Strict Rejection
```
reject_weak_passwords = true
```
When a weak password is entered:
1. An error message is displayed
2. Command exits immediately
3. User must choose a stronger password

This mode enforces strict security policies.

#### Mode 3: Bypass (Testing/Development)
Using CLI flags or environment variables:
```bash
# Skip password strength checks
d2fa init-vault --allow-weak-passwords

# Or via environment variable
export D2FA_ALLOW_WEAK_PASSWORDS=1
d2fa change-password
```

This mode is useful for testing but should NOT be used in production.

Passwords passed through `--password` or `--password-file` bypass interactive
creation/change enforcement without requiring this flag or environment
variable. The optional existing-password warning on `d2fa vault unlock` can
still evaluate them. Protect these inputs appropriately, and avoid
command-line passwords where process arguments may be visible to other users
or captured by tooling.

The public Python `Vault.save()` and `Vault.load()` API require an explicit,
non-empty password. Omitting the argument raises `TypeError`; passing an empty
string raises `ValueError`. Passwordless vaults created by older API versions
must be re-saved with a non-empty password using the previous release before
upgrading; the current API will not open them.

AES-GCM authentication failures, including wrong passwords and modified
encrypted payloads, raise `InvalidPassword`. `CorruptedVault` is raised only
when decryption succeeds but JSON or vault-model validation fails.

### Best Practices

1. **Use Passphrases**: Longer passphrases are often stronger than complex single words
   - ✅ `Correct-Horse-Battery-Staple` (4 words)
   - ✅ `My-Vault-Password-2024` (memorable, ~40+ bits entropy)

2. **Mix Entropy Sources**: Combine case, numbers, and symbols
   - ✅ `Mountain1Blue$River` (mixed case + digit + symbol)
   - ✅ `Desert.Sand#Sky2024` (mixed entropy)

3. **Avoid Predictable Patterns**:
   - ❌ Sequential: `123456`, `abcdef`, `qwerty`
   - ❌ Keyboard patterns: `!!1234567`, `qwertyuiop`
   - ❌ Personal info: birth years, pet names, common words

4. **Use a Password Manager**: Generate and store strong passwords
   - Store the vault password in your password manager
   - Keep a backup in a secure location (e.g., encrypted file)

### Backward Compatibility

**Legacy `min_password_entropy` Option:**

If your config contains the old `min_password_entropy` setting:
```toml
[security]
min_password_entropy = 60  # deprecated
```

This setting is recognized and automatically mapped to zxcvbn score >= 3. No action is required—your vault will continue to work. However, we recommend removing this option from your config in favor of the new structure.

### Implementation Details

- **zxcvbn Library**: Industry-standard password strength estimator
- **Threshold**: Score < 3 is treated as weak
- **Interactive default**: Weak passwords show a warning and require confirmation
- **Existing-password warning**: `d2fa vault unlock` can check the existing password when `warn_on_weak_existing_passwords = true`
- **Rejection Mode**: Set `reject_weak_passwords = true` to enforce strict policies
- **No Entropy Calculation**: Desktop-2FA uses zxcvbn exclusively; legacy entropy functions are not used

### Security Hardening Timeline

- **v0.7.3**: Password confirmation, entropy calculation
- **v0.8.1**: zxcvbn integration, configuration mapping, vault unlock warning
- **v0.8.2**: Selectable vault paths, bounded vault loading, and atomic saves
- **v0.8.3**: Early Textual UI prototype; no changes to vault encryption or storage format

### Recommendations

1. Use **passphrases** for better memorability and security
2. Enable **`reject_weak_passwords = true`** in production environments
3. Use **`--allow-weak-passwords` only for testing**
4. **Back up your vault password** securely
5. **Change your vault password regularly** if you suspect compromise
6. **Never share** your vault password via unencrypted channels

### Reporting Security Issues

If you discover a security vulnerability, please report it responsibly:

1. Do NOT open a public GitHub issue
2. Check the [repository Security tab](https://github.com/wrogistefan/desktop-2fa/security) for current private reporting options
3. Include steps to reproduce and potential impact
4. Allow time for a fix before public disclosure

---

**Last Updated:** October 2026
**zxcvbn Integration:** v0.8.1
