"""Command-line interface for estat-mcp."""

from __future__ import annotations

import asyncio

import click

from estat_mcp.server import mcp


@click.group()
def cli() -> None:
    """e-Stat MCP server and client CLI."""
    pass


@cli.command()
@click.option(
    "--transport",
    type=click.Choice(["stdio", "sse"]),
    default="stdio",
    help="Transport protocol (stdio or sse)",
)
def serve(transport: str) -> None:
    """Start the MCP server."""
    mcp.run(transport=transport)


@cli.command()
def version() -> None:
    """Show version information."""
    from estat_mcp import __version__

    click.echo(f"estat-mcp {__version__}")


if __name__ == "__main__":
    cli()
