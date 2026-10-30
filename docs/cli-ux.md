# CLI presentation and output

Current behavior is defined by the [UX contract](ux.md) and the
[user manual](user_manual.md#exit-codes). Global options precede the command.
There is no unlock timeout or persistent authenticated session. Diagnostics
use stderr, and `code --json`, `--raw` and `--quiet` obey the documented stream
contract. Labels are literal text; terminal colors are not part of the API.

The older enhanced-UX proposal is [archived](archive/cli-ux.md); its proposed
unlock-window behavior and colored examples are not implemented contracts.
