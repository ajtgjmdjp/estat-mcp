"""MCP server exposing e-Stat tools to LLMs via FastMCP.

This module defines the MCP (Model Context Protocol) server that allows
AI assistants like Claude to search Japanese government statistics,
retrieve metadata, and fetch statistical data through the e-Stat API.

Usage with Claude Desktop (add to ``claude_desktop_config.json``)::

    {
      "mcpServers": {
        "estat": {
          "command": "uvx",
          "args": ["estat-mcp", "serve"]
        }
      }
    }
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Annotated, Any

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

from fastmcp import FastMCP
from pydantic import Field

from estat_mcp.client import EstatClient

# Lazily initialized client with lock for concurrent-safe access
_client: EstatClient | None = None
_client_lock = asyncio.Lock()


async def _get_client() -> EstatClient:
    """Return the shared EstatClient, creating it on first call.

    Uses double-checked locking to avoid race conditions when
    multiple MCP tool calls arrive concurrently.
    """
    global _client
    if _client is not None:
        return _client
    async with _client_lock:
        if _client is None:
            _client = EstatClient()
    return _client


@asynccontextmanager
async def _lifespan(server: FastMCP[dict[str, Any]]) -> AsyncIterator[dict[str, Any]]:
    """Manage EstatClient lifecycle — close httpx.AsyncClient on shutdown."""
    yield {}
    if _client is not None:
        await _client.close()


mcp = FastMCP(
    name="e-Stat",
    lifespan=_lifespan,
    instructions=(
        "e-Stat MCP server provides tools for accessing Japanese government "
        "statistics from the e-Stat portal (政府統計の総合窓口).\n\n"
        "You can search for statistical tables by keyword, retrieve metadata "
        "to understand table structure, and fetch actual statistical data.\n\n"
        "Key tools:\n"
        "- search_statistics: Find statistical tables by keyword\n"
        "- get_statistic_meta: Get table structure (dimensions, codes)\n"
        "- get_statistic_data: Fetch actual data values with filtering\n\n"
        "e-Stat contains data on:\n"
        "- Population and demographics (人口統計)\n"
        "- Economic indicators (GDP, CPI, trade)\n"
        "- Industry and business statistics\n"
        "- Agriculture, labor, and social statistics\n"
        "- Regional and municipal data\n\n"
        "Note: An e-Stat appId is required. Get one at:\n"
        "https://www.e-stat.go.jp/api/api-info/use-api"
    ),
)


@mcp.tool()
async def search_statistics(
    keyword: Annotated[
        str,
        Field(description="Search keyword (Japanese). Example: '人口' (population)"),
    ],
    limit: Annotated[
        int,
        Field(description="Maximum number of results (default: 20)", ge=1, le=100),
    ] = 20,
) -> list[dict[str, Any]]:
    """Search for statistical tables by keyword.

    Returns metadata for matching tables including ID, name, and organization.
    Use the table ID with get_statistic_meta or get_statistic_data.

    Example: search_statistics("人口") → population statistics tables
    """
    client = await _get_client()
    tables = await client.search_stats(keyword, limit=limit)
    return [
        {
            "id": t.id,
            "name": t.name,
            "gov_code": t.gov_code,
            "organization": t.organization,
            "survey_date": t.survey_date,
        }
        for t in tables
    ]


@mcp.tool()
async def get_statistic_meta(
    stats_id: Annotated[
        str,
        Field(description="Statistics table ID from search_statistics"),
    ],
) -> dict[str, Any]:
    """Get metadata for a statistical table.

    Returns the table structure including:
    - Table items (表章事項): Column headers
    - Classification items (分類事項): Category dimensions
    - Time items (時間軸事項): Time periods available
    - Area items (地域事項): Geographic areas

    Use this to understand what dimensions and codes are available
    before fetching data with get_statistic_data.
    """
    client = await _get_client()
    meta = await client.get_meta(stats_id)

    return {
        "stats_id": meta.stats_id,
        "table_items": [
            {"code": i.code, "name": i.name, "level": i.level, "unit": i.unit}
            for i in meta.table_items
        ],
        "classification_items": {
            k: [{"code": i.code, "name": i.name} for i in v]
            for k, v in meta.classification_items.items()
        },
        "time_items": [{"code": i.code, "name": i.name} for i in meta.time_items],
        "area_items": [{"code": i.code, "name": i.name} for i in meta.area_items],
    }


@mcp.tool()
async def get_statistic_data(
    stats_id: Annotated[
        str,
        Field(description="Statistics table ID"),
    ],
    limit: Annotated[
        int,
        Field(
            description="Maximum records to fetch (default: 1000)",
            ge=1,
            le=100000,
        ),
    ] = 1000,
    start_position: Annotated[
        int | None,
        Field(
            description="Start position for pagination. Use next_key from previous response.",
        ),
    ] = None,
    cd_tab: Annotated[
        str | None,
        Field(
            description="Filter by table item code. Example: '110' for population",
        ),
    ] = None,
    cd_time: Annotated[
        str | None,
        Field(description="Filter by time code (時間軸事項コード). Example: '2024000' for 2024"),
    ] = None,
    cd_area: Annotated[
        str | None,
        Field(description="Filter by area code (地域事項コード). Example: '13000' for Tokyo"),
    ] = None,
    cd_cat01: Annotated[
        str | None,
        Field(description="Filter by classification code 01 (分類事項01コード)"),
    ] = None,
    lv_tab: Annotated[
        str | None,
        Field(
            description="Table item hierarchy level. Example: '1' or '1-2'",
        ),
    ] = None,
    lv_time: Annotated[
        str | None,
        Field(description="Time axis hierarchy level (時間軸事項階層レベル)"),
    ] = None,
    lv_area: Annotated[
        str | None,
        Field(description="Area hierarchy level (地域事項階層レベル)"),
    ] = None,
) -> dict[str, Any]:
    """Fetch statistical data for a table with optional filtering and pagination.

    Returns the actual data values with their dimensions (time, area, classifications).
    For large tables, use filters to narrow down results before fetching.

    Pagination:
    - Use start_position to continue from a previous request
    - Check has_more and next_key in the response for more data

    Filter parameters:
    - cd_tab/cd_time/cd_area/cd_cat01: Filter by specific codes
    - lv_tab/lv_time/lv_area: Filter by hierarchy level (e.g., "1" or "1-3")

    The response includes:
    - values: List of data points with their dimension codes
    - total_count: Total number of records (may exceed limit)
    - has_more: Whether more data is available
    - next_key: Pagination key for the next page
    """
    client = await _get_client()
    data = await client.get_data(
        stats_id,
        limit=limit,
        start_position=start_position,
        cd_tab=cd_tab,
        cd_time=cd_time,
        cd_area=cd_area,
        cd_cat01=cd_cat01,
        lv_tab=lv_tab,
        lv_time=lv_time,
        lv_area=lv_area,
    )

    return {
        "stats_id": data.stats_id,
        "total_count": data.total_count,
        "values": [
            {
                "value": v.value,
                "table_code": v.table_code,
                "time_code": v.time_code,
                "area_code": v.area_code,
                **v.classification_codes,
            }
            for v in data.values[:100]  # Limit output size for MCP
        ],
        "has_more": data.next_key is not None,
        "next_key": data.next_key,
    }


@mcp.tool()
async def get_all_statistic_data(
    stats_id: Annotated[
        str,
        Field(description="Statistics table ID"),
    ],
    max_pages: Annotated[
        int,
        Field(
            description="Maximum pages to fetch (safety limit, default: 10)",
            ge=1,
            le=50,
        ),
    ] = 10,
    cd_tab: Annotated[
        str | None,
        Field(description="Filter by table item code (表章事項コード)"),
    ] = None,
    cd_time: Annotated[
        str | None,
        Field(description="Filter by time code (時間軸事項コード)"),
    ] = None,
    cd_area: Annotated[
        str | None,
        Field(description="Filter by area code (地域事項コード)"),
    ] = None,
    cd_cat01: Annotated[
        str | None,
        Field(description="Filter by classification code 01 (分類事項01コード)"),
    ] = None,
    lv_tab: Annotated[
        str | None,
        Field(description="Table item hierarchy level (表章事項階層レベル)"),
    ] = None,
    lv_time: Annotated[
        str | None,
        Field(description="Time axis hierarchy level (時間軸事項階層レベル)"),
    ] = None,
    lv_area: Annotated[
        str | None,
        Field(description="Area hierarchy level (地域事項階層レベル)"),
    ] = None,
) -> dict[str, Any]:
    """Fetch all statistical data with automatic pagination.

    Automatically follows next_key to fetch all pages until either:
    - No more pages (next_key is None)
    - max_pages limit is reached (safety limit)

    Use this for smaller datasets or when you need complete data.
    For large datasets, use get_statistic_data with manual pagination.

    Returns:
    - values: Sample of data (first 100 records from all pages)
    - total_count: Total number of records across all pages
    - fetched_count: Number of records actually fetched
    - has_more: Whether max_pages was reached before fetching all data
    """
    client = await _get_client()
    data = await client.get_all_data(
        stats_id,
        max_pages=max_pages,
        cd_tab=cd_tab,
        cd_time=cd_time,
        cd_area=cd_area,
        cd_cat01=cd_cat01,
        lv_tab=lv_tab,
        lv_time=lv_time,
        lv_area=lv_area,
    )

    return {
        "stats_id": data.stats_id,
        "total_count": data.total_count,
        "fetched_count": len(data.values),
        "values": [
            {
                "value": v.value,
                "table_code": v.table_code,
                "time_code": v.time_code,
                "area_code": v.area_code,
                **v.classification_codes,
            }
            for v in data.values[:100]  # Limit output size for MCP
        ],
        "has_more": data.next_key is not None,
        "note": (
            "First 100 records shown. Use get_statistic_data with start_position for more."
            if len(data.values) > 100
            else None
        ),
    }
