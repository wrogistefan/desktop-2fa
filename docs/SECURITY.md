# Security Model & Threat Analysis

## Overview

Desktop-2FA is an offline, stateless 2FA manager designed for secure local storage of TOTP secrets. This document describes the security architecture, threat model, and security guarantees provided by Desktop-2FA.

---

## Security Goals

1. **Confidentiality**: TOTP secrets are encrypted and protected from unauthorized access
2. **Integrity**: Vault data cannot be modified without detection
3. **Authenticity**: Users verify their identity with passwords before vault access
4. **Availability**: Users can always access their TOTP secrets with correct credentials
5. **Auditability**: All critical operations are logged with clear error messages
6. **Autonomy**: No cloud dependencies, complete local control

---

## Threat Model

### In Scope (Threats We Protect Against)

| Threat | Risk | Mitigation |
|--------|------|-----------|
| **Unauthorized file access** | Attacker reads vault file | AES-256-GCM encryption |
| **Vault tampering** | Attacker modifies vault data | GCM authentication tag |
| **Password guessing** | Attacker brute-force attempts | Argon2id KDF, password strength checks |
| **Memory attacks** | Attacker accesses RAM during operation | Python runtime limitations, brief key retention |
| **Side-channel attacks** | Timing/power analysis on encryption | Hardware/OS responsibility, use of standard libraries |
| **Backup compromise** | Backups are stolen | Same encryption as primary vault |
| **Configuration tampering** | Attacker modifies config file | User responsibility (not in scope for now) |
| **Weak password selection** | User chooses guessable password | zxcvbn-based strength enforcement |

### Out of Scope (Threats We Don't Address)

| Threat | Reason | Recommendation |
|--------|--------|-----------------|
| **Compromised host OS** | Cannot protect if OS is infected | Use trusted/verified operating system |
| **Malware on system** | Malware can read any decrypted data | Use antivirus/keep system updated |
| **Shoulder surfing** | Visual observation during password entry | User responsibility to secure workspace |
| **Weak system password** | User's login password is weak | Use strong OS password |
| **Stolen hardware** | Physical device theft with powered-on state | Use full-disk encryption + power off device |
| **TOTP code interception** | TOTP code transmitted to 2FA service (not Desktop-2FA's responsibility) | Trust the service provider |
| **Compromised dependencies** | Supply chain attack on libraries | Use from trusted sources (PyPI) |

---

## Cryptographic Architecture

### Vault Encryption

**Algorithm**: AES-256-GCM (Galois/Counter Mode)

**Advantages**:
- ✅ Authenticated encryption (AEAD)
- ✅ Detects tampering automatically
- ✅ Industry standard for secure vaults
- ✅ Hardware-accelerated on modern CPUs
- ✅ No padding oracle vulnerabilities

**Key Size**: 256 bits (32 bytes)

**Authentication Tag**: 128 bits (16 bytes) - prevents tampering

**Nonce/IV**: 96 bits (12 bytes) - randomly generated per encryption

### Key Derivation

**Algorithm**: Argon2id (RFC 9106 compliant)

**Parameters**:
- Time Cost: 4 (4 iterations)
- Memory Cost: 128 MiB (prevents GPU/ASIC attacks)
- Parallelism: 2 (two parallel threads)
- Output Length: 32 bytes (256 bits)
- Salt: Randomly generated, 16 bytes

**Advantages**:
- ✅ Memory-hard (resistant to GPU brute-force)
- ✅ Time-hard (slows down password guessing)
- ✅ Winner of Password Hashing Competition (2015)
- ✅ Resistant to side-channel attacks
- ✅ Configurable security parameters

**Security Against Brute-Force**:
- Single attempt: ~500ms (slow enough to deter attacks)
- 1 million attempts: ~139 hours on single CPU
- Dictionary attacks are similarly slowed

### Password Strength Evaluation

**Library**: zxcvbn (Dropbox's realistic password strength estimator)

**Scoring**:
```
Score 0-2: Weak (easily guessable)
Score 3-4: Strong (resistant to attacks)
```

**What zxcvbn Analyzes**:
- Dictionary words (common passwords, user info)
- Repeated patterns (111, aaa, qwerty)
- Sequences (abc, 123, qwer)
- L33t speak (p@ssw0rd)
- Spatial patterns (keyboard walks)
- Temporal patterns (dates, years)

**Enforcement Modes**:
1. **Warning Mode** (default)
   - Weak passwords trigger yellow warning
   - User can confirm continuation
   - Non-blocking, respects user autonomy

2. **Rejection Mode** (strict)
   - Weak passwords rejected immediately
   - Suitable for organizational policies
   - Configured via `reject_weak_passwords` option

---

## Vault Format & File Structure

### Header (Version 1)

```
Offset  Size  Content
------  ----  -------
0       4     Magic: 0xDEADBEEF
4       1     Version: 0x01
5       16    Salt (for key derivation)
21      16    Nonce/IV (for encryption)
37      16    Authentication Tag (for integrity)
```

**Total Header Size**: 53 bytes

### Encrypted Data

```
Offset  Content
------  -------
53      JSON-serialized vault data (encrypted)
```

### Data Format

```json
{
  "entries": [
    {
      "account_name": "GitHub",
      "issuer": "GitHub",
      "secret": "JBSWY3DPEHPK3PXP",
      "period": 30,
      "digits": 6,
      "algorithm": "SHA1"
    }
  ]
}
```

---

## Security Properties

### Confidentiality

**Guarantees**:
- Vault file is meaningless without correct password
- Brute-force attack requires millions of Argon2id computations
- Each vault uses unique random salt and nonce

**Key Length**: 256 bits (sufficient against quantum computers with Grover's algorithm for 128-bit security equivalent)

### Integrity

**Guarantees**:
- Any modification to vault file is detectable
- GCM authentication tag prevents tampering
- Header hash ensures metadata integrity
- Corrupted vault is rejected immediately

**Detection**: Decryption fails → `ValueError: Authentication tag verification failed`

### Authentication

**Guarantees**:
- User proves knowledge of password
- Password verified through Argon2id derivation
- Incorrect password produces wrong key → decryption fails
- No "close guess" attacks possible

**Attack Resistance**:
- Each wrong password attempt costs ~500ms (slow)
- No information leakage on partial password matches

### Availability

**Guarantees**:
- Vault is always accessible with correct password
- No external dependencies required
- No time-based lockouts (don't exist)
- Vault format is version-compatible

**Limitations**:
- Forgotten password → vault inaccessible (by design)
- Recommendation: Store password in password manager

---

## Operational Security

### Password Management

**Best Practices**:
1. ✅ Use passphrases (4+ words): `Battery-Horse-Staple-Correct`
2. ✅ Store in password manager (e.g., KeePass, Bitwarden)
3. ✅ Use unique password (not reused elsewhere)
4. ✅ Change password regularly (e.g., annually)
5. ✅ Never share password via insecure channels

**Weak Passwords to Avoid**:
- ❌ Dictionary words: `password`, `admin`, `vault`
- ❌ Keyboard patterns: `qwerty`, `asdfgh`
- ❌ Numeric sequences: `123456`, `111111`
- ❌ Personal info: birth dates, names, pet names
- ❌ Common phrases: `password123`, `admin2024`

### Vault Backup

**Recommendation**: Back up vault regularly

**Security**:
- Backups are encrypted with same cipher as primary vault
- Use same password as primary vault
- Store backups in secure location (encrypted disk, password manager, secure cloud)

**Backup Command**:
```bash
d2fa backup
```

**Manual Backup**:
```bash
cp ~/.desktop-2fa/vault ~/backups/vault.backup
```

### Configuration Security

**Config Location**: `~/.config/d2fa/config.toml`

**Security Considerations**:
- Config file is NOT encrypted
- Contains non-sensitive settings only
- Do NOT store passwords in config
- Protect config file permissions: `chmod 600`

**Recommended Settings**:
```toml
[security]
reject_weak_passwords = true  # Enforce strong passwords
```

### Vault File Permissions

**Recommended Setup**:
```bash
# Vault directory permissions
chmod 700 ~/.desktop-2fa/

# Vault file permissions
chmod 600 ~/.desktop-2fa/vault
```

**Why**:
- `700` on directory: only owner can read/write/execute
- `600` on file: only owner can read/write
- Prevents accidental access by other users

---

## Attack Scenarios

### Scenario 1: Attacker Steals Vault File

**Attacker's Goal**: Decrypt vault and obtain TOTP secrets

**Obstacles**:
1. Vault file is encrypted with AES-256-GCM
2. Key is derived from password using Argon2id
3. Argon2id is slow: ~500ms per attempt
4. Brute-force attack would take weeks/months

**Time Estimates** (single attacker, modern CPU):
- Common password (entropy ~40 bits): ~5 minutes
- Strong password (entropy ~60 bits): ~200 years
- Excellent passphrase (entropy ~90 bits): ~200 million years

**Mitigation**: Use strong password (score ≥ 3 in zxcvbn)

### Scenario 2: Attacker Modifies Vault File

**Attacker's Goal**: Inject malicious entry or change existing entry

**Obstacles**:
1. Modification requires decryption (need correct password)
2. Any change to ciphertext invalidates authentication tag
3. Decryption fails with integrity error
4. No information leakage on partial modifications

**Defense**: GCM authentication tag prevents tampering

### Scenario 3: Attacker Observes Password Entry

**Attacker's Goal**: Capture password during user input

**Obstacles**:
1. User enters password on trusted terminal
2. Desktop-2FA uses `getpass` for secure entry
3. Password not echoed to screen
4. Password not stored in command history

**Mitigation**: Use trusted workspace, disable terminal logging

### Scenario 4: Attacker Performs Dictionary Attack

**Attacker's Goal**: Guess password using dictionary

**Obstacles**:
1. Argon2id requires ~500ms per attempt
2. 100,000 dictionary words = ~50,000 seconds = ~14 hours
3. Attacker cannot parallelize effectively (memory-hard)

**Defense**: Strong password makes dictionary attack infeasible

### Scenario 5: User Forgets Password

**Scenario**: User loses access to vault

**Recovery Options**:
1. ✅ Restore from backup (if available)
2. ✅ Retrieve original secrets from service providers
3. ❌ Recover password (cryptographically impossible - by design)

**Prevention**: Store password in password manager

---

## Cryptographic Review

### Dependencies

| Library | Purpose | Version | Audit |
|---------|---------|---------|-------|
| cryptography | AES-GCM, random | ≥42.0.0 | Regularly audited |
| argon2-cffi | Argon2id KDF | ≥23.1.0 | Based on libargon2 |
| zxcvbn-python | Password strength | ≥4.0.0 | Based on Dropbox zxcvbn |

### Security Assumptions

1. **Python random**: Uses OS `urandom()` (cryptographically secure)
2. **cryptography library**: Maintained by Python Packaging Authority
3. **OpenSSL backend**: Hardware-accelerated on modern systems
4. **Argon2**: IETF RFC 9106 compliant reference implementation

### Known Limitations

1. **Python runtime**: GC/memory management not constant-time
2. **Timing attacks**: Possible but mitigated by Argon2id design
3. **Side-channels**: OS and hardware responsibility
4. **Key stretching**: Tradeoff between security and usability

---

## Security Updates & Advisories

### Reporting Security Issues

**DO NOT** open public GitHub issues for security vulnerabilities.

**Process**:
1. Email: security@desktop-2fa.org (if applicable)
2. Include: CVE information, affected versions, reproduction steps
3. Wait: 90 days for patch before public disclosure
4. Credit: Your name/organization in security advisory

### Version History

| Version | Date | Changes |
|---------|------|---------|
| 0.8.1dev | Jan 2026 | Development version |
| 0.8.0 | Jan 2026 | zxcvbn password strength evaluation added |
| 0.7.3 | Oct 2025 | Security hardening improvements |
| 0.7.0 | Aug 2025 | Initial stable release |

---

## Compliance & Standards

### RFC Standards

- **RFC 6238**: TOTP (Time-based One-Time Passwords)
- **RFC 3394**: AES Key Wrap Algorithm
- **RFC 9106**: Argon2 Password Hashing Function

### Security Standards

- **OWASP**: [Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
- **NIST SP 800-63B**: Digital Identity Guidelines
- **NIST SP 800-132**: Password-Based Key Derivation

### Cryptographic Standards

- **FIPS 197**: AES (Advanced Encryption Standard)
- **FIPS 202**: SHA-3 (Secure Hash Algorithm 3)

---

## Future Security Improvements

### Planned Features

1. **Hardware Security Module (HSM) Support**
   - Optional YubiKey integration
   - PIN-protected key material

2. **Biometric Authentication**
   - Fingerprint unlock (optional)
   - Falls back to password

3. **Time-based Lockout**
   - After N failed attempts, rate-limit attempts
   - Optional per configuration

4. **Encryption at Rest**
   - Multiple encryption keys for segments
   - Key rotation capabilities

5. **Audit Logging**
   - Operation history (encrypted)
   - Access time tracking

### Research Areas

1. Post-quantum cryptography (Argon2 already quantum-resistant)
2. Zero-knowledge proofs for password verification
3. Distributed trust (multiple shares of encryption key)

---

## References

### Academic Papers

1. Biryukov, A., Dinu, D., & Khovratovich, D. (2016). "Argon2: The Memory-Hard, GPU-Resistant Password Hashing and Key Derivation Function"
2. Wheeler, D. L. (2016). "zxcvbn: Low-Budget Password Strength Estimation"
3. McGrew, D. A., & Viega, J. (2005). "The Galois/Counter Mode of Operation (GCM)"

### Security Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [OWASP CryptoCheatSheet](https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html)
- [Crypto101](https://www.crypto101.io/) - Free cryptography course

### Tools & Utilities

- [KeePass](https://keepass.info/) - Password manager for storing Desktop-2FA password
- [Bitwarden](https://bitwarden.com/) - Cross-platform password manager
- [hashcat](https://hashcat.net/) - Reference for password strength estimation

---

## Security Checklist

### User Setup

- [ ] Use strong password (score ≥ 3 in zxcvbn)
- [ ] Store password in password manager
- [ ] Set vault file permissions to 600
- [ ] Set vault directory permissions to 700
- [ ] Enable `reject_weak_passwords = true` in config (recommended)
- [ ] Back up vault to secure location
- [ ] Keep system and dependencies updated

### System Setup

- [ ] Use trusted operating system
- [ ] Install antivirus/anti-malware
- [ ] Enable full-disk encryption
- [ ] Regular OS security updates
- [ ] Firewall enabled and configured
- [ ] Regular system backups

### Operational

- [ ] Change vault password regularly (annually)
- [ ] Review backup strategy
- [ ] Test password recovery process
- [ ] Monitor for security advisories
- [ ] Update Desktop-2FA regularly

---

## Contact & Support

For security-related questions or concerns:

- **Email**: security@desktop-2fa.org (if applicable)
- **GitHub Issues**: Use for non-security bugs/features
- **Discussions**: GitHub Discussions for general questions

---

**Last Updated**: January 2026
**Version**: 1.0
**Status**: Current
