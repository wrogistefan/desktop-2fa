# Cryptographic Contract

This document specifies the cryptographic implementation and security guarantees for Desktop 2FA.

## Overview

Desktop 2FA uses a hybrid cryptographic system combining Argon2id key derivation with AES-GCM encryption to provide secure offline storage of TOTP secrets.

## Security Goals

- **Confidentiality**: TOTP secrets must remain inaccessible without the user passphrase
- **Integrity**: Detect any tampering with stored data
- **Authentication**: Ensure data authenticity and prevent replay attacks
- **Forward Security**: Compromise of encrypted data should not reveal historical secrets

## Cryptographic Primitives

### Key Derivation: Argon2id

**Algorithm**: Argon2id (version 1.3)
**Purpose**: Derive a 256-bit encryption key from user passphrase

**Parameters**:
- `time_cost`: 4 iterations
- `memory_cost`: 131,072 KiB (128 MiB)
- `parallelism`: 2 threads
- `hash_len`: 32 bytes (256 bits)
- `salt_len`: 16 bytes

**Rationale**:
- Argon2id provides resistance against both CPU and GPU-based attacks
- Parameters chosen to provide ~100ms derivation time on modern hardware (2025-era)
- Memory cost of 128 MiB provides strong resistance to GPU attacks
- Parallelism of 2 is suitable for most desktop systems

### Symmetric Encryption: AES-GCM

**Algorithm**: AES-256-GCM
**Key Size**: 256 bits
**Purpose**: Encrypt/decrypt vault data with authenticated encryption

**Parameters**:
- `key`: 32 bytes (256 bits) derived from Argon2id
- `nonce`: 12 bytes (96 bits) randomly generated per encryption
- `tag`: 16 bytes (128 bits) authentication tag

**Format**: `nonce (12 bytes) + ciphertext + tag (16 bytes)`

**Rationale**:
- AES-GCM provides authenticated encryption (confidentiality + integrity)
- 256-bit key provides adequate security margin for the foreseeable future
- 96-bit nonce provides 2^96 possible values, virtually eliminating collision risk
- 128-bit authentication tag provides strong integrity guarantees

## Vault File Format

### ⚠️ IMPORTANT NOTICE — Vault Format Change (0.6.0)

Starting with desktop‑2fa 0.6.0, the vault file format has been fully audited and stabilized as part of the Vault Security Audit (Phases 1–5).

This audit introduced a strict, versioned vault header and hardened cryptographic parameters.

As a result:

Vaults created with versions prior to 0.6.0 are not compatible with 0.6.0+.

Older vaults did not include:

- a version field in the header,
- the finalized magic header (D2FA),
- the audited Argon2id parameters,
- the stable ciphertext layout introduced after the audit.

Because these fields are now required for safe parsing and forward compatibility, vaults created before the audit cannot be imported by current versions of the application.

This is intentional and was required to guarantee:

- deterministic parsing rules,
- safe rejection of malformed or ambiguous vaults,
- future‑proofing for format evolution,
- cryptographic correctness validated in the audit.

#### What this means for users
If your vault was created with 0.5.6 or earlier, it will be rejected as "unsupported format".

You will need to initialize a new vault using `d2fa init-vault`.

All vaults created with 0.6.0 and later include a versioned header and will remain compatible with future releases.

#### Why no automatic migration?
The pre‑audit vaults lacked the metadata required to safely migrate them:

- no version field → impossible to reliably detect layout,
- inconsistent Argon2id parameters → unsafe to reinterpret,
- no stable header → cannot distinguish valid vaults from corrupted files,
- ciphertext structure changed during the audit.

Attempting to "guess" the format would introduce ambiguity and weaken the security guarantees established by the audit.

#### Going forward
From 0.6.0 onward:

- every vault includes a versioned header,
- the format is stable and forward‑compatible,
- future changes will be handled through explicit version bumps,
- no further breaking changes are expected.

This ensures that vaults created today will remain readable in all future versions.

---

### Structure
```
+-------------+-------------+---------------------+
| Magic (4B)  | Version (1B)| Salt (16B)          |
+-------------+-------------+---------------------+
| Encrypted Blob (nonce + ciphertext + tag)     |
+------------------------------------------------+
```

### Constants
- `VAULT_MAGIC`: `b"D2FA"` (4 bytes)
- `VAULT_VERSION`: `b"\x01"` (1 byte, current version)
- `HEADER_LEN`: 5 bytes (magic + version)

### Encryption Process
1. Generate random 16-byte salt
2. Derive 32-byte key using Argon2id(password, salt)
3. Generate random 12-byte nonce
4. Serialize vault data to JSON bytes
5. Encrypt JSON bytes using AES-GCM(key, nonce)
6. Concatenate: `magic + version + salt + nonce + ciphertext + tag`

### Decryption Process
1. Verify magic header (`D2FA`)
2. Verify version (`\x01`)
3. Extract salt (16 bytes)
4. Derive key using Argon2id(password, salt)
5. Extract encrypted blob (nonce + ciphertext + tag)
6. Decrypt using AES-GCM(key, encrypted_blob)
7. Parse decrypted JSON into VaultData structure

## Security Guarantees

### Vault Unlocking Security
- Password authentication is mandated for every vault access, even during the unlock window
- The unlock timeout requires explicit password provision via `--password` or `--password-file` options
- The `.vault-unlocked` file contains only a timestamp and no sensitive data

### Confidentiality
- AES-256-GCM ensures that vault contents are unintelligible without the correct passphrase
- Argon2id key derivation prevents brute-force attacks on weak passphrases

### Integrity & Authentication
- AES-GCM authentication tag detects any modification of encrypted data
- Invalid password or corrupted data will fail decryption with high probability

### Forward Security
- Each encryption uses a unique random nonce and salt
- Compromise of one vault file does not compromise others (even with same password)

### Resistance to Attacks
- **Offline Brute Force**: Argon2id parameters provide ~100ms minimum work per attempt
- **GPU Attacks**: 128 MiB memory requirement makes GPU attacks economically unfeasible
- **Rainbow Tables**: Per-vault salt prevents precomputation attacks
- **Nonce Reuse**: Random 96-bit nonces prevent nonce reuse attacks

## Implementation Notes

### Dependencies
- `cryptography` library for AES-GCM implementation
- `argon2-cffi` library for Argon2id implementation

### Error Handling
- `InvalidPassword`: Raised when decryption fails (wrong password or corruption)
- `CorruptedVault`: Raised when decrypted data fails JSON/Pydantic validation
- `UnsupportedFormat`: Raised for invalid file format or version

### Performance Characteristics
- Key derivation: ~100ms on modern hardware
- Encryption/Decryption: Fast (< 1ms for typical vault sizes)
- Memory usage: ~128 MiB peak during key derivation

## Compliance

This implementation follows industry best practices:
- NIST SP 800-38D (GCM mode)
- RFC 9106 (Argon2)
- OWASP recommendations for password hashing
- RFC 6238 (TOTP, indirectly via secure secret storage)

## Future Considerations

### Parameter Updates
Parameters may be updated in future versions to maintain security as hardware advances. Backward compatibility will be maintained through version negotiation.

### Algorithm Migration
If cryptographic weaknesses are discovered, migration paths will be provided to transition to stronger algorithms while maintaining data accessibility.

---

*This contract is binding for all implementations of Desktop 2FA vault encryption.*