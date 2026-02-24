"""Command-line interface for estat-mcp.

Provides five commands:
- ``estat-mcp search``: Search for statistical tables
- ``estat-mcp data``: Fetch statistical data
- ``estat-mcp test``: Test API key and connectivity
- ``estat-mcp serve``: Start the MCP server
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import TYPE_CHECKING, Literal, cast

import click
import httpx
from loguru import logger

from estat_mcp.client import EstatAPIError

if TYPE_CHECKING:
    from estat_mcp.models import StatsData, StatsTable


def _handle_api_error(e: Exception, prefix: str = "Error") -> None:
    """Print an API error message to stderr and exit with code 1."""
    click.echo(f"{prefix}: {e}", err=True)
    raise SystemExit(1) from None


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging.")
def cli(verbose: bool) -> None:
    """e-Stat API client and MCP server for Japanese government statistics."""
    level = "DEBUG" if verbose else "INFO"
    logger.remove()
    logger.add(sys.stderr, level=level, format="{time:HH:mm:ss} | {level:<7} | {message}")


@cli.command()
@click.argument("keyword")
@click.option("--limit", "-n", default=20, help="Max results to show (default: 20).")
@click.option(
    "--format",
    "-f",
    "fmt",
    type=click.Choice(["table", "json"]),
    default="table",
    help="Output format.",
)
def search(keyword: str, limit: int, fmt: str) -> None:
    """Search for statistical tables by keyword.

    Examples:

        estat-mcp search 人口

        estat-mcp search "消費者物価指数" --limit 10

        estat-mcp search GDP --format json
    """
    from estat_mcp.client import EstatClient

    async def _run() -> list[StatsTable]:
        async with EstatClient() as client:
            return await client.search_stats(keyword, limit=limit)

    try:
        tables = asyncio.run(_run())
    except (EstatAPIError, httpx.HTTPError, json.JSONDecodeError) as e:
        _handle_api_error(e)

    if fmt == "json":
        click.echo(json.dumps([t.model_dump() for t in tables], ensure_ascii=False, indent=2))
        return

    if not tables:
        click.echo(f"No statistics found for '{keyword}'")
        return

    # Table format
    click.echo(f"Found {len(tables)} statistical tables:\n")
    click.echo(f"{'ID':<15} {'Organization':<20} {'Survey Date':<12} Name")
    click.echo("-" * 80)
    for t in tables:
        org = t.organization or ""
        if len(org) > 18:
            org = org[:16] + ".."
        survey = t.survey_date or ""
        click.echo(f"{t.id:<15} {org:<20} {survey:<12} {t.name}")


@cli.command()
@click.argument("stats_id")
@click.option("--limit", "-n", default=100, help="Max records to fetch (default: 100).")
@click.option(
    "--format",
    "-f",
    "fmt",
    type=click.Choice(["table", "json"]),
    default="table",
    help="Output format.",
)
@click.option("--cd-tab", default=None, help="Filter by table item code (表章事項コード).")
@click.option("--cd-time", default=None, help="Filter by time code (時間軸事項コード).")
@click.option("--cd-area", default=None, help="Filter by area code (地域事項コード).")
@click.option("--cd-cat01", default=None, help="Filter by classification code 01.")
def data(
    stats_id: str,
    limit: int,
    fmt: str,
    cd_tab: str | None,
    cd_time: str | None,
    cd_area: str | None,
    cd_cat01: str | None,
) -> None:
    """Fetch statistical data for a table.

    Examples:

        estat-mcp data 0003410379

        estat-mcp data 0003410379 --limit 50 --format json

        estat-mcp data 0003410379 --cd-area 13000 --cd-time 2024000
    """
    from estat_mcp.client import EstatClient

    async def _run() -> StatsData:
        async with EstatClient() as client:
            return await client.get_data(
                stats_id,
                limit=limit,
                cd_tab=cd_tab,
                cd_time=cd_time,
                cd_area=cd_area,
                cd_cat01=cd_cat01,
            )

    try:
        result = asyncio.run(_run())
    except (EstatAPIError, httpx.HTTPError, json.JSONDecodeError) as e:
        _handle_api_error(e)

    if fmt == "json":
        click.echo(json.dumps(result.to_dicts(), ensure_ascii=False, indent=2))
        return

    # Table format
    click.echo(f"Statistics ID: {result.stats_id}")
    click.echo(f"Total records: {result.total_count}")
    click.echo(f"Fetched: {len(result.values)}\n")

    if not result.values:
        click.echo("No data returned.")
        return

    # Show first few values
    click.echo("Sample data (first 10 rows):\n")
    for i, v in enumerate(result.values[:10], 1):
        dims = []
        if v.table_code:
            dims.append(f"tab={v.table_code}")
        if v.time_code:
            dims.append(f"time={v.time_code}")
        if v.area_code:
            dims.append(f"area={v.area_code}")
        for k, val in v.classification_codes.items():
            dims.append(f"{k}={val}")
        dim_str = ", ".join(dims) if dims else "no dimensions"
        click.echo(f"  {i:2}. value={v.value} ({dim_str})")

    if len(result.values) > 10:
        click.echo(f"\n  ... and {len(result.values) - 10} more rows")


@cli.command("test")
def test_connection() -> None:
    """Test API key and connectivity to e-Stat.

    Verifies that your ESTAT_APP_ID is set and working by making
    a lightweight API call.

    Examples:

        estat-mcp test
    """
    from estat_mcp import __version__

    click.echo(f"estat-mcp v{__version__}\n")

    # 1. Check API key
    api_key = os.environ.get("ESTAT_APP_ID", "")
    if not api_key:
        click.echo("[FAIL] ESTAT_APP_ID is not set", err=True)
        click.echo(
            "  Get an appId from: https://www.e-stat.go.jp/api/api-info/use-api",
            err=True,
        )
        click.echo(
            "  Then set it with: export ESTAT_APP_ID=your_app_id",
            err=True,
        )
        sys.exit(1)
    click.echo(f"[OK]   ESTAT_APP_ID is set ({api_key[:4]}...{api_key[-4:]})")

    # 2. Test API connectivity
    click.echo("\nTesting API connectivity...")

    from estat_mcp.client import EstatClient

    async def _test() -> str:
        async with EstatClient() as client:
            tables = await client.search_stats("人口", limit=3)
            if tables:
                return f"Found {len(tables)} results (e.g. {tables[0].name})"
            return "API responded but no results for test query"

    try:
        result = asyncio.run(_test())
        click.echo(f"[OK]   {result}")
    except (EstatAPIError, httpx.HTTPError, json.JSONDecodeError) as e:
        _handle_api_error(e, prefix="[FAIL] API error")

    click.echo("\nAll checks passed.")


@cli.command()
def version() -> None:
    """Show version information."""
    from estat_mcp import __version__

    click.echo(f"estat-mcp {__version__}")


@cli.command()
@click.option(
    "--transport",
    type=click.Choice(["stdio", "sse"]),
    default="stdio",
    help="MCP transport protocol.",
)
def serve(transport: str) -> None:
    """Start the e-Stat MCP server.

    For Claude Desktop, add this to your config:

        {"mcpServers": {"estat": {"command": "uvx", "args": ["estat-mcp", "serve"]}}}
    """
    from estat_mcp.server import mcp

    logger.info(f"Starting e-Stat MCP server ({transport} transport)")
    mcp.run(transport=cast('Literal["stdio", "sse"]', transport))


if __name__ == "__main__":
    cli()
