"""Select output mode before Click parses options or invokes callbacks."""

import sys
from collections.abc import Sequence
from typing import Any

import click
from typer.core import TyperGroup

from desktop_2fa.constants import ExitCode

from .output import OutputMode, failure, output_mode


def requested_mode(args: Sequence[str]) -> OutputMode:
    """Inspect only code options, skipping values of global password/path flags."""
    index = 0
    while index < len(args):
        arg = args[index]
        if arg in {"--password", "--password-file", "--vault"}:
            index += 2
            continue
        if arg == "code":
            flags = args[index + 1 :]
            if "--" in flags:
                flags = flags[: flags.index("--")]
            return OutputMode("--json" in flags, "--raw" in flags, "--quiet" in flags)
        if not arg.startswith("-"):
            break
        index += 1
    return OutputMode()


class OutputGroup(TyperGroup):
    def main(
        self,
        args: Sequence[str] | None = None,
        prog_name: str | None = None,
        complete_var: str | None = None,
        standalone_mode: bool = True,
        windows_expand_args: bool = True,
        **extra: Any,
    ) -> Any:
        arguments = list(sys.argv[1:] if args is None else args)
        token = output_mode.set(requested_mode(arguments))
        try:
            return super().main(
                args=arguments,
                prog_name=prog_name,
                complete_var=complete_var,
                standalone_mode=standalone_mode,
                windows_expand_args=windows_expand_args,
                **extra,
            )
        finally:
            output_mode.reset(token)

    def parse_args(self, ctx: click.Context, args: list[str]) -> list[str]:
        try:
            return super().parse_args(ctx, args)
        except click.UsageError:
            self._usage_failure()
            raise

    def invoke(self, ctx: click.Context) -> Any:
        try:
            return super().invoke(ctx)
        except click.UsageError:
            self._usage_failure()
            raise

    @staticmethod
    def _usage_failure() -> None:
        mode = output_mode.get()
        if mode.json or mode.quiet:
            # Parser text may include a rejected value (including key material).
            failure(ExitCode.INVALID_PASSWORD, "usage_error", "Invalid command syntax.")
            raise click.exceptions.Exit(2)
