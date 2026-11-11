# Documentation

Start with the [user manual](user_manual.md) for current commands, global option
placement, password files, recovery and exit/output contracts. Examples use
synthetic data; choose a temporary vault with `--vault` when trying them.

- [Security model and limitations](SECURITY.md)
- [Cryptographic format and compatibility](crypto.md)
- [Persistence guarantees and evidence](persistence.md)
- [CLI UX contract](ux.md) and [presentation/output](cli-ux.md)
- [External adapter scope](import_adapters.md) (Python helpers, not CLI modes)
- [Development tools](development.md)
- [CI graph, tested runtimes and publication gates](ci.md)
- [Repository inventory](repository_inventory.md)
- [Release readiness checklist](release_checklist.md)
- [Historical reports](archive/README.md), preserved with provenance and superseded banners

The 0.11.0 [Textual interface](user_manual.md#textual-terminal-ui) includes
account and vault operations, live codes and password-confirmed writes. See its
[threat analysis](textual-security.md) and [synthetic captures](../assets/screenshots/textual-ui/README.md). Vaults remain offline. No document is a certification
or a guarantee against a compromised host, offline guessing or power loss.
