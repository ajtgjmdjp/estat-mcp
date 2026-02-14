"""Tests for estat_mcp.client pagination features."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from estat_mcp.client import EstatClient
from estat_mcp.models import DataValue, StatsData


class TestGetAllData:
    """Tests for get_all_data method with automatic pagination."""

    @pytest.mark.asyncio
    async def test_get_all_data_single_page(self) -> None:
        """Test get_all_data when all data fits in one page."""
        client = EstatClient(app_id="test")

        # Mock get_data to return single page
        mock_data = StatsData(
            stats_id="0003410379",
            total_count=100,
            values=[DataValue(value=i) for i in range(100)],
            next_key=None,
        )

        with patch.object(client, "get_data", new_callable=AsyncMock) as mock_get_data:
            mock_get_data.return_value = mock_data

            result = await client.get_all_data("0003410379", max_pages=10)

            assert result.stats_id == "0003410379"
            assert len(result.values) == 100
            assert result.total_count == 100
            assert result.next_key is None
            mock_get_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_data_multiple_pages(self) -> None:
        """Test get_all_data with multiple pages."""
        client = EstatClient(app_id="test")

        # Mock get_data to return 3 pages
        page1 = StatsData(
            stats_id="0003410379",
            total_count=250,
            values=[DataValue(value=i) for i in range(100)],
            next_key="101",
        )
        page2 = StatsData(
            stats_id="0003410379",
            total_count=250,
            values=[DataValue(value=i) for i in range(100, 200)],
            next_key="201",
        )
        page3 = StatsData(
            stats_id="0003410379",
            total_count=250,
            values=[DataValue(value=i) for i in range(200, 250)],
            next_key=None,
        )

        with patch.object(client, "get_data", new_callable=AsyncMock) as mock_get_data:
            mock_get_data.side_effect = [page1, page2, page3]

            result = await client.get_all_data("0003410379", max_pages=10)

            assert result.stats_id == "0003410379"
            assert len(result.values) == 250
            assert result.total_count == 250
            assert result.next_key is None
            assert mock_get_data.call_count == 3

    @pytest.mark.asyncio
    async def test_get_all_data_max_pages(self) -> None:
        """Test get_all_data respects max_pages limit."""
        client = EstatClient(app_id="test")

        # Mock get_data to always return next_key (infinite pages)
        page = StatsData(
            stats_id="0003410379",
            total_count=1000,
            values=[DataValue(value=i) for i in range(100)],
            next_key="101",
        )

        with patch.object(client, "get_data", new_callable=AsyncMock) as mock_get_data:
            mock_get_data.return_value = page

            result = await client.get_all_data("0003410379", max_pages=5)

            assert result.stats_id == "0003410379"
            assert len(result.values) == 500  # 5 pages * 100 values
            assert result.next_key is not None  # Indicates more data available
            assert mock_get_data.call_count == 5

    @pytest.mark.asyncio
    async def test_get_all_data_with_filters(self) -> None:
        """Test get_all_data passes filters correctly."""
        client = EstatClient(app_id="test")

        mock_data = StatsData(
            stats_id="0003410379",
            total_count=50,
            values=[DataValue(value=i) for i in range(50)],
            next_key=None,
        )

        with patch.object(client, "get_data", new_callable=AsyncMock) as mock_get_data:
            mock_get_data.return_value = mock_data

            await client.get_all_data(
                "0003410379",
                max_pages=10,
                cd_tab="110",
                cd_time="2024000",
                cd_area="13000",
            )

            # Check that filters were passed to get_data
            call_kwargs = mock_get_data.call_args.kwargs
            assert call_kwargs["cd_tab"] == "110"
            assert call_kwargs["cd_time"] == "2024000"
            assert call_kwargs["cd_area"] == "13000"
