"""Exercise the release CLI on synthetic data and capture real output as SVG.

Run with the project venv. Never reads the default vault or system clipboard.
PNG rendering is a separate, optional browser operation.
"""

import argparse
import asyncio
import io
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import click
import pyperclip
from rich.console import Console
from rich.terminal_theme import MONOKAI
from rich.text import Text
from typer.main import get_command
from typer.testing import CliRunner

from desktop_2fa.cli.main import app
from desktop_2fa.ui_textual.app import D2FAApp
from desktop_2fa.vault import Vault

PASSWORD = "synthetic-release-password"
SECRET = "JBSWY3DPEHPK3PXP"
ROOT = Path(__file__).resolve().parents[1]


def save_svg(path: Path, content: str) -> None:
    """Remove whitespace-only artifacts emitted by Rich's SVG template."""
    path.write_text(
        "\n".join(line.rstrip() for line in content.splitlines()) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "assets/screenshots/release-0.10.0"
    )
    options = parser.parse_args()
    output = options.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    cases: list[dict[str, object]] = []
    sessions: dict[str, list[tuple[str, str]]] = {}
    executable = Path(sys.executable).parent / (
        "d2fa.exe" if os.name == "nt" else "d2fa"
    )
    with tempfile.TemporaryDirectory(prefix="d2fa-release-") as directory:
        work = Path(directory)
        (work / "demo-password.txt").write_text(PASSWORD, encoding="utf-8")
        (work / "wrong.txt").write_text("synthetic-wrong", encoding="utf-8")
        env = {
            **os.environ,
            "PYTHONUTF8": "1",
            "TERM": "xterm-256color",
            "FORCE_COLOR": "1",
            "COLUMNS": "100",
            "HOME": str(work),
            "USERPROFILE": str(work),
            "DESKTOP_2FA_VAULT": str(work / "demo.bin"),
        }
        env.pop("DESKTOP_2FA_FORCE_INTERACTIVE", None)
        flags = ["--password-file", "demo-password.txt", "--allow-weak-passwords"]

        def run(name, args, status=0, session=None, vault="demo.bin", extra=None):
            command = ["--vault", vault, *flags, *args]
            if extra is not None:
                command = extra
            result = subprocess.run(
                [str(executable), *command],
                cwd=work,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=60,
            )
            assert result.returncode == status, (
                f"{name}: expected {status}, got {result.returncode}: "
                f"{result.stdout}{result.stderr}"
            )
            cases.append({"case": name, "status": status, "driver": "subprocess"})
            if session:
                sessions.setdefault(session, []).append(
                    (
                        "d2fa " + subprocess.list2cmdline(command),
                        result.stdout + result.stderr,
                    )
                )
            return result

        def helps(command, prefix=()):
            run("help " + " ".join(prefix), [], extra=[*prefix, "--help"])
            if isinstance(command, click.Group):
                for name, child in command.commands.items():
                    helps(child, (*prefix, name))

        helps(get_command(app))
        run("no arguments", [], extra=[])
        run("version", [], extra=["--version"], session="accounts")
        alias = executable.with_name("desktop-2fa" + executable.suffix)
        for flag in ("--version", "--help"):
            result = subprocess.run(
                [str(alias), flag],
                cwd=work,
                env=env,
                capture_output=True,
                timeout=30,
            )
            assert result.returncode == 0
            cases.append(
                {"case": "desktop-2fa " + flag, "status": 0, "driver": "subprocess"}
            )
        run("init", ["vault", "init"], session="accounts")
        run("empty list", ["list"])
        run("manual add", ["add", "alice@example.com", "Example", SECRET])
        uri = (
            "otpauth://totp/Work:bob?secret="
            + SECRET
            + "&issuer=Work&algorithm=SHA256&digits=8&period=60"
        )
        run("URI add", ["add", uri])
        entries = Vault.load(work / "demo.bin", PASSWORD).entries
        assert (entries[1].algorithm, entries[1].digits, entries[1].period) == (
            "SHA256",
            8,
            60,
        )
        run("list indices", ["list", "--indices"], session="accounts")
        run("code", ["code", "alice@example.com"], session="codes")
        raw = run("raw", ["code", "bob", "--raw"], session="codes")
        assert raw.stdout.strip().isdigit() and len(raw.stdout.strip()) == 8
        structured = run("json", ["code", "bob", "--json"], session="codes")
        assert len(json.loads(structured.stdout)["code"]) == 8
        quiet = run("quiet", ["code", "bob", "--quiet"])
        assert not quiet.stdout and not quiet.stderr
        run("unlock", ["vault", "unlock"])
        run("path", ["vault", "path"])
        before = (work / "demo.bin").read_bytes()
        run("duplicate add", ["add", "bob", "Other", SECRET], 6)
        assert (work / "demo.bin").read_bytes() == before
        run("rename", ["rename", "bob", "work-bob"], session="rename")
        run(
            "collision",
            ["rename", "work-bob", "alice@example.com"],
            6,
            session="rename",
        )
        run("indexed rename", ["rename", "work-bob", "bob", "--index", "2"])
        run("invalid index", ["rename", "bob", "other", "--index", "99"], 6)
        run("backup", ["backup"], session="recovery")
        run("second backup", ["backup"])
        backups = list(work.glob("*.backup*.bin"))
        assert len(backups) == 2
        expected = Vault.load(work / "demo.bin", PASSWORD).data
        for backup in backups:
            assert Vault.load(backup, PASSWORD).data == expected
        run("export", ["export", "demo-export.bin"], session="recovery")
        exported = (work / "demo-export.bin").read_bytes()
        run("export refusal", ["export", "demo-export.bin"], 6, session="recovery")
        assert (work / "demo-export.bin").read_bytes() == exported
        run("force export", ["export", "demo-export.bin", "--force"])
        run(
            "import",
            ["import", "demo-export.bin"],
            vault="restored.bin",
            session="recovery",
        )
        run("import refusal", ["import", "demo-export.bin"], 6, vault="restored.bin")
        run(
            "force import",
            ["import", "demo-export.bin", "--force"],
            vault="restored.bin",
        )
        assert Vault.load(work / "restored.bin", PASSWORD).data == expected
        run("remove", ["remove", "bob"])
        run("missing entry", ["remove", "bob"], 3)
        run("alias init", ["init-vault"], vault="disposable.bin")
        run("init refusal", ["vault", "init"], 6, vault="disposable.bin")
        run("force init", ["vault", "init", "--force"], vault="disposable.bin")
        run(
            "wrong password",
            [],
            extra=["--vault", "demo.bin", "--password-file", "wrong.txt", "list"],
            status=2,
        )
        run("missing vault", ["code", "alice"], 4, vault="missing.bin")
        (work / "broken.bin").write_bytes(b"synthetic-corrupt-data")
        run("corrupt vault", ["list"], 1, vault="broken.bin")
        run("invalid secret", ["add", "bad", "Example", "!"], 6)
        run("invalid URI", ["add", "otpauth://hotp/invalid"], 6)
        run("incomplete add", ["add"], 6)
        run("conflicting output", ["code", "alice@example.com", "--raw", "--json"], 6)
        run("usage error", ["code"], 2)
        run("noninteractive password change", ["vault", "change-password"], 6)
        preserved = (work / "demo.bin").read_bytes()
        run("self export refusal", ["export", "demo.bin", "--force"], 6)
        assert (work / "demo.bin").read_bytes() == preserved
        for name, payload in (
            ("empty", b""),
            ("BOM", b"\xef\xbb\xbfsynthetic"),
            ("invalid UTF-8", b"\xff"),
        ):
            (work / "invalid-password.txt").write_bytes(payload)
            run(
                name + " password file",
                [],
                6,
                extra=[
                    "--vault",
                    "demo.bin",
                    "--password-file",
                    "invalid-password.txt",
                    "list",
                ],
            )
        run(
            "missing password file",
            [],
            1,
            extra=["--vault", "demo.bin", "--password-file", "absent.txt", "list"],
        )
        result = run(
            "quiet wrong password",
            [],
            2,
            extra=[
                "--vault",
                "demo.bin",
                "--password-file",
                "wrong.txt",
                "code",
                "alice@example.com",
                "--quiet",
            ],
        )
        assert not result.stdout and not result.stderr
        result = run("JSON missing account", ["code", "absent", "--json"], 3)
        assert json.loads(result.stdout)["error"] == "entry_not_found"

        runner = CliRunner()
        absolute = [
            "--vault",
            str(work / "demo.bin"),
            "--password-file",
            str(work / "demo-password.txt"),
            "--allow-weak-passwords",
        ]
        with patch("desktop_2fa.cli.main.is_interactive", return_value=True):
            result = runner.invoke(
                app, [*absolute, "add"], input=f"carol\nDemo\n{SECRET}\n"
            )
            assert result.exit_code == 0, result.output
            assert SECRET not in result.output
            cases.append(
                {
                    "case": "interactive hidden-secret add",
                    "status": 0,
                    "driver": "CliRunner",
                }
            )
            sessions["interactive"] = [
                (
                    "d2fa --vault demo.bin --password-file demo-password.txt --allow-weak-passwords add",
                    result.output,
                )
            ]
        with patch("pyperclip.copy") as clipboard:
            for switch in ("--copy", "--copy-only", "-c"):
                result = runner.invoke(app, [*absolute, "code", "carol", switch])
                assert result.exit_code == 0, result.output
                assert clipboard.call_args.args[0].isdigit()
                cases.append({"case": switch, "status": 0, "driver": "stub clipboard"})
        with patch(
            "pyperclip.copy",
            side_effect=pyperclip.PyperclipException("Synthetic unavailable clipboard"),
        ):
            result = runner.invoke(app, [*absolute, "code", "carol", "--copy"])
            assert result.exit_code == 0 and "Clipboard not available" in result.output
            cases.append(
                {
                    "case": "copy fallback without clipboard",
                    "status": 0,
                    "driver": "stub clipboard",
                }
            )
            result = runner.invoke(app, [*absolute, "code", "carol", "--copy-only"])
            assert result.exit_code == 5, result.output
            cases.append(
                {
                    "case": "clipboard unavailable",
                    "status": 5,
                    "driver": "stub clipboard",
                }
            )

        async def capture_ui():
            ui = D2FAApp(str(work / "demo.bin"), PASSWORD)
            async with ui.run_test(size=(100, 30)) as pilot:
                await pilot.pause()
                save_svg(
                    output / "textual.svg",
                    ui.export_screenshot(title="Desktop-2FA | SYNTHETIC DEMO"),
                )

        with patch(
            "desktop_2fa.ui_textual.app.run_textual",
            side_effect=lambda *a: asyncio.run(capture_ui()),
        ):
            result = runner.invoke(app, [*absolute, "ui"])
            assert result.exit_code == 0, result.output
            cases.append(
                {
                    "case": "ui mount and capture",
                    "status": 0,
                    "driver": "Textual headless",
                }
            )
        with (
            patch("desktop_2fa.cli.main.is_interactive", return_value=True),
            patch("getpass.getpass", return_value="synthetic-new-release-password"),
        ):
            result = runner.invoke(app, [*absolute, "vault", "change-password"])
            assert result.exit_code == 0, result.output
        assert Vault.load(work / "demo.bin", "synthetic-new-release-password").entries
        run("old password rejected after change", ["list"], 2)
        cases.append(
            {
                "case": "password change and reopen",
                "status": 0,
                "driver": "CliRunner / stub getpass",
            }
        )

    for name, transcript in sessions.items():
        console = Console(
            record=True, width=100, file=io.StringIO(), force_terminal=True
        )
        console.print("SYNTHETIC DEMO | Desktop-2FA 0.10.0", style="bold cyan")
        console.print(
            "Temporary vault and public example accounts. No real credentials.\n"
        )
        for command, result in transcript:
            console.print(Text("$ " + command, style="bold green"))
            console.print(Text.from_ansi(result.rstrip()))
            console.print()
        save_svg(
            output / f"{name}.svg",
            console.export_svg(
                title="Desktop-2FA | Demo terminal",
                theme=MONOKAI,
                unique_id="d2fa-" + name,
            ),
        )
    report = {
        "version": "0.10.0",
        "cases": cases,
        "passed": len(cases),
        "limitations": [
            "Windows / Python " + sys.version.split()[0],
            "Interactive prompts use CliRunner, not a native TTY",
            "System clipboard replaced by a stub",
            "Textual exercised headlessly; SVG is a rendered screen",
            "Terminal SVGs replay actual output; not desktop screenshots",
        ],
    }
    (output / "report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(f"{len(cases)} release CLI checks passed; captures: {output}")


if __name__ == "__main__":
    main()
