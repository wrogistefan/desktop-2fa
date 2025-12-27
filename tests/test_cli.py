from typer.testing import CliRunner

from desktop_2fa.cli.main import app

runner = CliRunner()


def test_list():
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
