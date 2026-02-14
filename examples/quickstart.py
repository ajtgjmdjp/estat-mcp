"""Quick start example for estat-mcp.

Before running, set your e-Stat API key:
    export ESTAT_APP_ID=your_app_id_here

Usage:
    uv run python examples/quickstart.py
"""

import asyncio
import os

from estat_mcp import EstatClient


async def main() -> None:
    app_id = os.environ.get("ESTAT_APP_ID")
    if not app_id:
        print("Set ESTAT_APP_ID environment variable first.")
        print("Get one at: https://www.e-stat.go.jp/api/api-info/use-api")
        return

    async with EstatClient(app_id=app_id) as client:
        # 1. Search for CPI (Consumer Price Index) statistics
        print("=== Search: 消費者物価指数 ===")
        tables = await client.search_stats("消費者物価指数", limit=5)
        for t in tables:
            print(f"  {t.id}  {t.name}  ({t.organization})")

        if not tables:
            print("  No tables found.")
            return

        # 2. Get metadata for the first table
        stats_id = tables[0].id
        print(f"\n=== Metadata for {stats_id} ===")
        meta = await client.get_meta(stats_id)

        print(f"  Table items: {len(meta.table_items)}")
        for item in meta.table_items[:5]:
            print(f"    {item.code}: {item.name} ({item.unit or '-'})")

        print(f"  Classifications: {list(meta.classification_items.keys())}")
        print(f"  Time periods: {len(meta.time_items)}")
        if meta.time_items:
            print(f"    Latest: {meta.time_items[0].name}")
        print(f"  Areas: {len(meta.area_items)}")

        # 3. Get data (first 100 records)
        print(f"\n=== Data for {stats_id} (limit=100) ===")
        data = await client.get_data(stats_id, limit=100)
        print(f"  Total records: {data.total_count}")
        print(f"  Fetched: {len(data.values)}")
        print(f"  Has more: {data.next_key is not None}")

        if data.values:
            print("\n  First 5 values:")
            for v in data.values[:5]:
                print(f"    tab={v.table_code} time={v.time_code} area={v.area_code} -> {v.value}")


if __name__ == "__main__":
    asyncio.run(main())
