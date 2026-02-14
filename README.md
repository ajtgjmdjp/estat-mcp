# estat-mcp

[![PyPI](https://img.shields.io/pypi/v/estat-mcp)](https://pypi.org/project/estat-mcp/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

[e-Stat](https://www.e-stat.go.jp/) (政府統計の総合窓口) API client and MCP server for Japanese government statistics.

## What is this?

**estat-mcp** provides programmatic access to Japan's official statistics portal ([e-Stat](https://www.e-stat.go.jp/)), which hosts 3,000+ statistical tables covering population, economy, prices, labor, agriculture, and regional data. It exposes these as both a Python async client and an [MCP](https://modelcontextprotocol.io/) server for AI assistants.

- Search statistics by keyword (人口, GDP, CPI, etc.)
- Retrieve metadata to understand table structure (表章事項, 分類事項, 時間軸, 地域)
- Fetch statistical data with automatic pagination for large datasets
- **Type-safe Pydantic models** with Polars/pandas DataFrame export
- **Rate limiting** built-in for API compliance
- MCP server with 4 tools for Claude Desktop and other AI tools

## Quick Start

### Installation

```bash
pip install estat-mcp
# or
uv add estat-mcp
```

### Get an API Key

Register (free) at [e-Stat API](https://www.e-stat.go.jp/api/api-info/use-api) and set:

```bash
export ESTAT_APP_ID=your_app_id_here
```

### 30-Second Example

```python
import asyncio
from estat_mcp import EstatClient

async def main():
    async with EstatClient() as client:
        # Search for population statistics
        tables = await client.search_stats("人口")
        print(tables[0].name)  # 人口推計

        # Get metadata
        meta = await client.get_meta(tables[0].id)
        print(f"Time periods: {[t.name for t in meta.time_items]}")

        # Fetch data (Tokyo, 2024)
        data = await client.get_data(
            tables[0].id,
            cd_area="13000",   # Tokyo
            cd_time="2024000", # 2024
            limit=100
        )
        
        # Export as DataFrame
        df = data.to_polars()
        print(df)

asyncio.run(main())
```

### CLI Quick Start

```bash
# Test API connectivity
estat-mcp test

# Search for CPI statistics
estat-mcp search "消費者物価指数" --limit 10

# Fetch data for a table
estat-mcp data 0003410379 --cd-area 13000 --format table

# Start MCP server
estat-mcp serve
```

## MCP Server

Add to your AI tool's MCP config:

<details>
<summary><b>Claude Desktop</b> (~⁠/Library/Application Support/Claude/claude_desktop_config.json)</summary>

```json
{
  "mcpServers": {
    "estat": {
      "command": "uvx",
      "args": ["estat-mcp", "serve"],
      "env": {
        "ESTAT_APP_ID": "your_app_id_here"
      }
    }
  }
}
```
</details>

<details>
<summary><b>Cursor</b> (~⁠/.cursor/mcp.json)</summary>

```json
{
  "mcpServers": {
    "estat": {
      "command": "uvx",
      "args": ["estat-mcp", "serve"],
      "env": {
        "ESTAT_APP_ID": "your_app_id_here"
      }
    }
  }
}
```
</details>

Then ask your AI: "日本の人口統計を教えて" or "東京の最新CPIは？"

### Available MCP Tools

| Tool | Description |
|------|-------------|
| `search_statistics` | キーワードで統計テーブルを検索 |
| `get_statistic_meta` | テーブル構造（表章事項・分類事項・時間軸・地域）を取得 |
| `get_statistic_data` | 統計データを取得（フィルタ・ページネーション対応） |
| `get_all_statistic_data` | 全ページ自動取得（max_pages制限付き） |

## Python API

### Search → Metadata → Data Flow

```python
import asyncio
from estat_mcp import EstatClient

async def main():
    async with EstatClient() as client:
        # 1. Search for statistics tables
        tables = await client.search_stats("消費者物価指数", limit=5)
        # → [StatsTable(id="0003410379", name="消費者物価指数", ...), ...]

        stats_id = tables[0].id

        # 2. Get metadata to understand structure
        meta = await client.get_meta(stats_id)
        print(f"Table items: {[i.name for i in meta.table_items]}")
        print(f"Time periods: {[t.name for t in meta.time_items]}")
        print(f"Areas: {[a.name for a in meta.area_items]}")

        # 3. Fetch data with filters
        data = await client.get_data(
            stats_id,
            cd_area="13000",      # Tokyo only
            cd_time="2024000",    # 2024 only
            limit=1000
        )

        # 4. Export to DataFrame
        df = data.to_polars()
        print(df)

asyncio.run(main())
```

### Automatic Pagination

For large datasets, use `get_all_data()` to automatically fetch all pages:

```python
# Fetch up to 10 pages (safety limit)
all_data = await client.get_all_data(
    stats_id,
    max_pages=10,
    cd_cat01="100"  # Filter by classification
)
print(f"Fetched {len(all_data.values)} / {all_data.total_count} records")
```

### Polars Export

```python
# Requires: pip install estat-mcp[polars]
df = data.to_polars()
```

## CLI Reference

```bash
# Search for statistics tables
estat-mcp search <keyword> [options]
  --limit, -n     Max results (default: 20)
  --format, -f    Output format: table|json (default: table)

# Fetch statistical data
estat-mcp data <stats_id> [options]
  --limit, -n       Max records (default: 100)
  --format, -f      Output format: table|json (default: table)
  --cd-tab          Filter by table item code
  --cd-time         Filter by time code
  --cd-area         Filter by area code
  --cd-cat01        Filter by classification code

# Test API connectivity
estat-mcp test

# Show version
estat-mcp version

# Start MCP server
estat-mcp serve [--transport stdio|sse]
```

## Available Data

e-Stat provides access to 3,000+ statistical tables:

| Category | Examples |
|----------|----------|
| **Population** | 人口推計、国勢調査、将来人口推計 |
| **Economy** | GDP、企業統計、商業統計、工業統計 |
| **Prices** | 消費者物価指数(CPI)、企業物価指数 |
| **Labor** | 労働力調査、賃金構造基本統計調査 |
| **Trade** | 貿易統計、国際収支統計 |
| **Agriculture** | 農業センサス、漁業センサス、林野統計 |
| **Regional** | 小地域・地域メッシュ、都道府県・市区町村データ |

## Integration with edinet-mcp

estat-mcp works alongside [edinet-mcp](https://github.com/ajtgjmdjp/edinet-mcp) for comprehensive Japanese financial data:

- **edinet-mcp**: Company financial statements (有価証券報告書)
- **estat-mcp**: Macroeconomic and demographic statistics

Example workflow:
1. Use edinet-mcp to get Toyota's revenue from EDINET
2. Use estat-mcp to get auto industry production statistics
3. Compare company performance against industry trends

## API Reference

### `EstatClient`

```python
from estat_mcp import EstatClient

async with EstatClient(
    app_id="...",           # or ESTAT_APP_ID env var
    timeout=60.0,           # request timeout
    rate_limit=0.5,         # requests per second
) as client:
    # Search
    tables: list[StatsTable] = await client.search_stats("人口", limit=20)
    
    # Metadata
    meta: StatsMeta = await client.get_meta("0003410379")
    
    # Data (single page)
    data: StatsData = await client.get_data(
        "0003410379",
        cd_area="13000",
        cd_time="2024000",
        limit=1000
    )
    
    # Data (all pages)
    all_data: StatsData = await client.get_all_data(
        "0003410379",
        max_pages=10
    )
```

### `StatsData`

```python
# Access values
for v in data.values:
    print(v.value)              # The numeric value
    print(v.time_code)          # Time dimension code
    print(v.area_code)          # Area dimension code
    print(v.classification_codes)  # Dict of classification codes

# Export
json_data = data.to_dicts()     # list[dict]
df = data.to_polars()           # polars.DataFrame (requires polars)
```

### Response Format

e-Stat API uses XML-style conventions in JSON:

```json
{
  "TABLE_INF": [
    {"@code": "110", "@name": "人口", "@unit": "人", "@level": "1"}
  ],
  "VALUE": [
    {"@tab": "110", "@time": "2024000", "@area": "13000", "$": "13960000"}
  ]
}
```

- `@`-prefixed keys are XML attributes
- `$` contains the text content

estat-mcp handles this automatically — you get clean Python objects.

## Development

```bash
git clone https://github.com/ajtgjmdjp/estat-mcp
cd estat-mcp
uv sync --extra dev
uv run pytest -v           # Run tests
uv run ruff check src/     # Lint
uv build                   # Build package
```

## Project Structure

```
estat-mcp/
├── src/estat_mcp/
│   ├── __init__.py      # Public API exports
│   ├── client.py        # EstatClient (async HTTP)
│   ├── models.py        # Pydantic models (StatsTable, StatsData, etc.)
│   ├── server.py        # MCP server (FastMCP)
│   └── cli.py           # Command-line interface
├── tests/               # Test suite
├── examples/            # Example scripts
├── pyproject.toml       # Project configuration
└── README.md
```

## Data Attribution

This project uses data from [e-Stat](https://www.e-stat.go.jp/) (政府統計の総合窓口),
operated by the Statistics Bureau of Japan (総務省統計局).
e-Stat data is provided as open government data.

## Related Projects

- [edinet-mcp](https://github.com/ajtgjmdjp/edinet-mcp) — EDINET financial data MCP server
- [jfinqa](https://github.com/ajtgjmdjp/jfinqa) — Japanese financial QA benchmark

## License

Apache-2.0

<!-- mcp-name: io.github.ajtgjmdjp/estat-mcp -->
