"""estat-mcp: e-Stat API client and MCP server for Japanese government statistics.

Quick start::

    import asyncio
    from estat_mcp import EstatClient

    async def main():
        async with EstatClient(app_id="YOUR_APP_ID") as client:
            # Search for statistics tables
            tables = await client.search_stats("人口")
            print(tables[0].name)

            # Get meta information
            meta = await client.get_meta(tables[0].id)
            print(meta.classification_items)

            # Get statistical data
            data = await client.get_data(tables[0].id)
            print(data.values)

    asyncio.run(main())
"""

from estat_mcp.client import EstatAPIError, EstatClient
from estat_mcp.models import (
    DataSet,
    StatsData,
    StatsMeta,
    StatsTable,
)

__all__ = [
    "DataSet",
    "EstatAPIError",
    "EstatClient",
    "StatsData",
    "StatsMeta",
    "StatsTable",
]

__version__ = "0.2.2"
