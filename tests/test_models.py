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

    def test_stats_table_from_api_response(self) -> None:
        """Test StatsTable from e-Stat API v3.0 TABLE_INF format."""
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

    def test_stats_table_from_api_response_string_title(self) -> None:
        """Test StatsTable with TITLE as plain string (not dict)."""
        data = {
            "@id": "0003410380",
            "STAT_NAME": {"@code": "00200521", "$": "国勢調査"},
            "GOV_ORG": {"@code": "00200", "$": "総務省"},
            "TITLE": "人口推計（令和二年）",
            "SURVEY_DATE": "202010",
        }
        table = StatsTable.from_api_response(data)
        assert table.id == "0003410380"
        assert table.name == "人口推計（令和二年）"

    def test_stats_table_from_api_response_minimal(self) -> None:
        """Test StatsTable with minimal fields."""
        data = {"@id": "0003410381"}
        table = StatsTable.from_api_response(data)
        assert table.id == "0003410381"
        assert table.name == ""
        assert table.gov_code is None
        assert table.organization is None


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


    def test_stats_data_to_polars(self) -> None:
        """Test converting StatsData to Polars DataFrame."""
        import polars as pl

        data = StatsData(
            stats_id="0003410379",
            total_count=3,
            values=[
                DataValue(
                    value=1000,
                    table_code="110",
                    time_code="2024000",
                    area_code="13000",
                    classification_codes={"cat01": "100"},
                ),
                DataValue(
                    value=2000,
                    table_code="110",
                    time_code="2023000",
                    area_code="13000",
                    classification_codes={"cat01": "100"},
                ),
                DataValue(
                    value=None,
                    table_code="120",
                    time_code="2024000",
                    area_code="14000",
                    classification_codes={"cat01": "200"},
                ),
            ],
        )
        df = data.to_polars()
        assert isinstance(df, pl.DataFrame)
        assert len(df) == 3
        assert "value" in df.columns
        assert "table_code" in df.columns
        assert "time_code" in df.columns
        assert "area_code" in df.columns
        assert "cat01" in df.columns
        assert df["value"][0] == 1000
        assert df["area_code"][1] == "13000"
        assert df["cat01"][2] == "200"

    def test_stats_data_to_polars_empty(self) -> None:
        """Test to_polars with empty values."""
        import polars as pl

        data = StatsData(stats_id="0003410379", total_count=0)
        df = data.to_polars()
        assert isinstance(df, pl.DataFrame)
        assert len(df) == 0


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


class TestStatsDataPolars:
    """Tests for StatsData Polars conversion."""

    def test_to_polars(self) -> None:
        """Test converting StatsData to Polars DataFrame."""
        import polars as pl

        data = StatsData(
            stats_id="0003410379",
            values=[
                DataValue(
                    value=125000000,
                    table_code="110",
                    time_code="2024000",
                    area_code="00000",
                    classification_codes={"cat01": "100"},
                ),
                DataValue(
                    value=61000000,
                    table_code="110",
                    time_code="2024000",
                    area_code="13000",
                    classification_codes={"cat01": "110"},
                ),
            ],
        )

        df = data.to_polars()
        assert isinstance(df, pl.DataFrame)
        assert len(df) == 2
        assert "value" in df.columns
        assert "table_code" in df.columns
        assert "time_code" in df.columns
        assert "area_code" in df.columns
        assert "cat01" in df.columns
        assert df["value"].to_list() == [125000000, 61000000]

    def test_to_polars_empty(self) -> None:
        """Test converting empty StatsData to Polars DataFrame."""
        import polars as pl

        data = StatsData(stats_id="0003410379", values=[])
        df = data.to_polars()
        assert isinstance(df, pl.DataFrame)
        assert len(df) == 0

    def test_to_polars_no_classification(self) -> None:
        """Test converting StatsData without classification codes."""
        import polars as pl

        data = StatsData(
            stats_id="0003410379",
            values=[
                DataValue(value=100, table_code="110"),
                DataValue(value=200, table_code="120"),
            ],
        )

        df = data.to_polars()
        assert isinstance(df, pl.DataFrame)
        assert len(df) == 2
        assert df["value"].to_list() == [100, 200]
        assert df["table_code"].to_list() == ["110", "120"]
