"""Shared test fixtures for estat-mcp."""

from __future__ import annotations

import pytest

from estat_mcp.models import (
    DataSet,
    DataValue,
    MetaItem,
    StatsData,
    StatsMeta,
    StatsTable,
)


@pytest.fixture()
def sample_stats_table() -> StatsTable:
    """Sample statistics table metadata."""
    return StatsTable(
        id="0003410379",
        name="人口推計（令和元年）",
        gov_code="00200511",
        survey_date="201910",
        open_date="201912",
        organization="総務省統計局",
        statistics_name="人口推計",
    )


@pytest.fixture()
def sample_stats_meta() -> StatsMeta:
    """Sample statistics metadata."""
    return StatsMeta(
        stats_id="0003410379",
        table_items=[
            MetaItem(code="110", name="人口", level=1, unit="人"),
            MetaItem(code="120", name="男女別人口", level=1),
        ],
        classification_items={
            "class01": [
                MetaItem(code="100", name="総数", level=1),
                MetaItem(code="110", name="男", level=2),
                MetaItem(code="120", name="女", level=2),
            ]
        },
        time_items=[
            MetaItem(code="2024000", name="2024年", level=1),
            MetaItem(code="2023000", name="2023年", level=1),
        ],
        area_items=[
            MetaItem(code="00000", name="全国", level=1),
            MetaItem(code="13000", name="東京都", level=2),
        ],
    )


@pytest.fixture()
def sample_stats_data() -> StatsData:
    """Sample statistics data."""
    return StatsData(
        stats_id="0003410379",
        total_count=3,
        values=[
            DataValue(
                value=125000000,
                table_code="110",
                time_code="2024000",
                area_code="00000",
            ),
            DataValue(
                value=61000000,
                table_code="110",
                time_code="2024000",
                area_code="13000",
            ),
            DataValue(
                value=64000000,
                table_code="110",
                time_code="2024000",
                area_code="00000",
                classification_codes={"cat01": "110"},
            ),
        ],
    )


@pytest.fixture()
def sample_dataset() -> DataSet:
    """Sample dataset."""
    return DataSet(
        id="00200511-20240101120000-0",
        stats_id="0003410379",
        name="人口推計_東京",
        description="東京都の人口データ",
    )
