# estat-mcp

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

[e-Stat](https://www.e-stat.go.jp/) (政府統計の総合窓口) API client and MCP server for Japanese government statistics.

## Features

- **Async HTTP client** — High-performance async/await API client
- **MCP server** — Model Context Protocol server for LLM integration
- **Type-safe** — Full type hints with Pydantic v2 models
- **Rate limiting** — Built-in rate limiter for API compliance
- **Pagination support** — Handle large datasets automatically

## Installation

```bash
# Clone the repository
git clone https://github.com/ajtgjmdjp/estat-mcp.git
cd estat-mcp

# Install with uv
uv pip install -e ".[dev]"

# Or with pip
pip install -e ".[dev]"
```

## Quick Start

### Python Client

```python
import asyncio
from estat_mcp import EstatClient

async def main():
    async with EstatClient(app_id="YOUR_APP_ID") as client:
        # Search for statistics tables
        tables = await client.search_stats("人口")  # Population
        print(f"Found {len(tables)} tables")
        print(tables[0].name)

        # Get metadata
        meta = await client.get_meta(tables[0].id)
        print(f"Time periods: {[t.name for t in meta.time_items]}")

        # Get data
        data = await client.get_data(tables[0].id, limit=100)
        for v in data.values[:5]:
            print(f"{v.time_code}: {v.value}")

asyncio.run(main())
```

### MCP Server

Add to your Claude Desktop config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "estat": {
      "command": "uvx",
      "args": ["estat-mcp", "serve"]
    }
  }
}
```

Or run directly:

```bash
export ESTAT_APP_ID="your_app_id"
estat-mcp serve
```

## Getting an API Key

1. Visit [e-Stat API registration](https://www.e-stat.go.jp/api/api-info/use-api)
2. Register for an application ID (appId)
3. Set as environment variable: `ESTAT_APP_ID` or pass to `EstatClient(app_id=...)`

## Available Data

e-Stat provides access to 3,000+ statistical tables including:

- **Population**: 人口推計、国勢調査
- **Economy**: GDP、企業統計、商業統計、工業統計
- **Prices**: 消費者物価指数(CPI)、企業物価指数
- **Labor**: 労働力調査、賃金構造基本統計調査
- **Agriculture**: 農業センサス、漁業センサス
- **Regional**: 小地域統計、市区町村データ

## Development

```bash
# Run tests
uv run pytest

# Run linting
uv run ruff check src tests
uv run ruff format src tests

# Type checking
uv run mypy src

# Build package
uv build
```

## Project Structure

```
estat-mcp/
├── src/estat_mcp/
│   ├── __init__.py      # Public API exports
│   ├── client.py        # EstatClient implementation
│   ├── models.py        # Pydantic data models
│   ├── server.py        # MCP server (FastMCP)
│   └── cli.py           # Command-line interface
├── tests/               # Test suite
├── pyproject.toml       # Project configuration
└── README.md
```

## License

Apache-2.0
