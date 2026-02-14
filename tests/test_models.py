"""Tests for estat_mcp.models."""

from __future__ import annotations

from estat_mcp.models import (
    DataSet,
    DataValue,
    MetaItem,
    StatsData,
    StatsMeta,
    StatsTable,
)


class TestStatsTable:
    def test_stats_table_creation(self) -> None:
        """Test StatsTable creation."""
        table = StatsTable(
            id="0003410379",
            name="人口推計",
            gov_code="00200511",
        )
        assert table.id == "0003410379"
        assert table.name == "人口推計"
        assert table.gov_code == "00200511"

    def test_stats_table_from_api_response_plain(self) -> None:
        """Test StatsTable from API response with plain keys."""
        data = {
            "id": "0003410379",
            "statistic_name": "人口推計（令和元年）",
            "stats_code": "00200511",
            "survey_date": "201910",
        }
        table = StatsTable.from_api_response(data)
        assert table.id == "0003410379"
        assert table.name == "人口推計（令和元年）"
        assert table.gov_code == "00200511"
        assert table.survey_date == "201910"

    def test_stats_table_from_api_response_prefixed(self) -> None:
        """Test StatsTable from API response with @-prefixed keys."""
        data = {
            "@id": "0003410379",
            "@statistic_name": "人口推計（令和元年）",
            "@stats_code": "00200511",
            "@survey_date": "201910",
            "gov_org": {"@code": "00200", "$": "総務省統計局"},
        }
        table = StatsTable.from_api_response(data)
        assert table.id == "0003410379"
        assert table.name == "人口推計（令和元年）"
        assert table.gov_code == "00200511"
        assert table.survey_date == "201910"

    def test_stats_table_from_api_response_estat_format(self) -> None:
        """Test StatsTable from real e-Stat API response format."""
        data = {
            "@id": "0003410379",
            "STAT_NAME": {"@code": "00200521", "$": "国勢調査"},
            "GOV_ORG": {"@code": "00200", "$": "総務省"},
            "STATISTICS_NAME": "国勢調査 人口等基本集計",
            "TITLE": {"@no": "001", "$": "人口推計（令和元年）"},
            "SURVEY_DATE": "201910",
            "OPEN_DATE": "2019-12-20",
        }
        table = StatsTable.from_api_response(data)
        assert table.id == "0003410379"
        assert table.name == "人口推計（令和元年）"
        assert table.gov_code == "00200521"
        assert table.organization == "総務省"
        assert table.statistics_name == "国勢調査 人口等基本集計"
        assert table.survey_date == "201910"
        assert table.open_date == "2019-12-20"


class TestStatsMeta:
    def test_stats_meta_creation(self) -> None:
        """Test StatsMeta creation."""
        meta = StatsMeta(
            stats_id="0003410379",
            table_items=[MetaItem(code="110", name="人口")],
        )
        assert meta.stats_id == "0003410379"
        assert len(meta.table_items) == 1
        assert meta.table_items[0].code == "110"

    def test_get_all_classifications(self) -> None:
        """Test getting all classification items."""
        meta = StatsMeta(
            stats_id="0003410379",
            classification_items={
                "class01": [MetaItem(code="100", name="総数")],
                "class02": [MetaItem(code="200", name="年齢")],
            },
        )
        all_items = meta.get_all_classifications()
        assert len(all_items) == 2


class TestStatsData:
    def test_stats_data_creation(self) -> None:
        """Test StatsData creation."""
        data = StatsData(
            stats_id="0003410379",
            total_count=100,
        )
        assert data.stats_id == "0003410379"
        assert data.total_count == 100

    def test_to_dicts(self) -> None:
        """Test converting values to dicts."""
        data = StatsData(
            stats_id="0003410379",
            values=[
                DataValue(value=100, table_code="110", time_code="2024000"),
                DataValue(value=200, table_code="120", area_code="13000"),
            ],
        )
        dicts = data.to_dicts()
        assert len(dicts) == 2
        assert dicts[0]["value"] == 100
        assert dicts[0]["table"] == "110"


class TestMetaItem:
    def test_meta_item_creation(self) -> None:
        """Test MetaItem creation."""
        item = MetaItem(code="110", name="人口", level=1, unit="人")
        assert item.code == "110"
        assert item.name == "人口"
        assert item.level == 1
        assert item.unit == "人"


class TestDataValue:
    def test_data_value_creation(self) -> None:
        """Test DataValue creation."""
        value = DataValue(
            value=125000000,
            table_code="110",
            time_code="2024000",
        )
        assert value.value == 125000000
        assert value.table_code == "110"


class TestDataSet:
    def test_dataset_creation(self) -> None:
        """Test DataSet creation."""
        dataset = DataSet(
            id="00200511-20240101120000-0",
            stats_id="0003410379",
            name="人口推計_東京",
        )
        assert dataset.id == "00200511-20240101120000-0"
        assert dataset.stats_id == "0003410379"
        assert dataset.name == "人口推計_東京"
