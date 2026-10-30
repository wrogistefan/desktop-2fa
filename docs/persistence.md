# Atomic publication and crash durability

## Decision and evidence (S17 / #48)

After flushing and `fsync`ing the complete encrypted temporary file, the writer
publishes it with `os.replace`, or a create-only hard link. Create-only writes
remove the temporary link before synchronizing the parent directory. On POSIX,
the writer now opens and `fsync`s that directory. Windows skips this POSIX call.
The D2FA v1 format, KDF and encryption are unchanged.

Atomic publication means readers see a complete old or new file. It does not
mean a successful return alone guarantees survival of sudden power loss. The
[Linux fsync manual](https://man7.org/linux/man-pages/man2/fsync.2.html) explicitly
requires a separate directory sync for directory-entry persistence. This is the
evidence for the narrow POSIX improvement, not a claim of universal durability.

## Errors before and after publication

Before publication, a write/flush/fsync/replace failure leaves an existing
destination unchanged and attempts to clean up only the writer's own temporary
file. Existing I/O exception/status contracts continue to apply.

Once replace/link succeeds, rollback is **not** promised. Failure to remove the
temporary link, open/sync/close the parent directory raises
`VaultDurabilityError`, a `VaultIOError` subclass. CLI status is 1, with JSON error
`vault_durability_uncertain`. The message says the vault was written and asks
the caller to reload before retrying. The in-memory instance records the new
revision even if directory synchronization fails. No automatic retry, deletion
or rollback of the destination occurs.

Check the destination using the password just used to save it (including the
new password after a password change). Keep existing backups; do not assume
the old password or old contents remain current because the command failed.
An unsupported directory-sync operation is reported as uncertain completion,
rather than silently presented as a confirmed durable write.

## Platform and threat-model limits

- Linux/macOS use POSIX directory synchronization when the filesystem supports
  it. This does not sync newly created ancestor directories; for stronger
  operational assurance, provision an existing destination directory first.
- macOS does not request `F_FULLFSYNC`. Apple's
  [fsync manual](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/fsync.2.html)
  distinguishes ordinary fsync from device-cache flushing. Stronger macOS
  device-cache guarantees need a separately measured implementation.
- Windows flushes the temporary file before publication, but this implementation
  does not add directory/volume flushing or write-through replacement.
  Microsoft's [FlushFileBuffers documentation](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-flushfilebuffers)
  describes different APIs and volume-flush privileges; no unsupported POSIX
  call or administrative volume operation is attempted here.
- Network filesystems, storage controllers, device caches, concurrent hostile
  path replacement and hardware failures can weaken guarantees. Publication
  locks coordinate cooperating writers; they do not prevent rollback by an
  attacker or create a journal. Maintain independent encrypted backups.

Tests exercise actual temporary-directory publication/round trips on each CI
platform and inject failures to check operation order, cleanup, committed data,
revision state and truthful errors. POSIX CI additionally executes actual
directory fsync. These tests do **not** simulate real power loss or certify a
filesystem/device's guarantees. Follow-up evidence would require crash/power-cut
testing on named filesystems and hardware, and evaluation of macOS full-sync,
Windows publication APIs and newly created ancestor directories.
