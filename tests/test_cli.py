"""Tests for estat_mcp.cli."""

from __future__ import annotations

from click.testing import CliRunner

from estat_mcp.cli import cli


class TestSearchCommand:
    """Tests for the search command."""

    def test_search_help(self) -> None:
        """Test search command help message."""
        runner = CliRunner()
        result = runner.invoke(cli, ["search", "--help"])
        assert result.exit_code == 0
        assert "search" in result.output.lower()
        assert "--limit" in result.output
        assert "--format" in result.output


class TestDataCommand:
    """Tests for the data command."""

    def test_data_help(self) -> None:
        """Test data command help message."""
        runner = CliRunner()
        result = runner.invoke(cli, ["data", "--help"])
        assert result.exit_code == 0
        assert "data" in result.output.lower()
        assert "--limit" in result.output
        assert "--format" in result.output
        assert "--cd-tab" in result.output
        assert "--cd-time" in result.output
        assert "--cd-area" in result.output
        assert "--cd-cat01" in result.output


class TestTestCommand:
    """Tests for the test command."""

    def test_test_help(self) -> None:
        """Test test command help message."""
        runner = CliRunner()
        result = runner.invoke(cli, ["test", "--help"])
        assert result.exit_code == 0
        assert "test" in result.output.lower()
        assert "api" in result.output.lower() or "connectivity" in result.output.lower()


class TestVersionCommand:
    """Tests for the version command."""

    def test_version(self) -> None:
        """Test version command."""
        runner = CliRunner()
        result = runner.invoke(cli, ["version"])
        assert result.exit_code == 0
        assert "estat-mcp" in result.output
        assert "0.2.0" in result.output


class TestServeCommand:
    """Tests for the serve command."""

    def test_serve_help(self) -> None:
        """Test serve command help message."""
        runner = CliRunner()
        result = runner.invoke(cli, ["serve", "--help"])
        assert result.exit_code == 0
        assert "serve" in result.output.lower()
        assert "--transport" in result.output


class TestCLI:
    """Tests for the main CLI."""

    def test_cli_help(self) -> None:
        """Test main CLI help message."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "search" in result.output
        assert "data" in result.output
        assert "test" in result.output
        assert "serve" in result.output

    def test_cli_verbose(self) -> None:
        """Test verbose flag."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--verbose", "version"])
        assert result.exit_code == 0
        # Verbose mode should work without error
