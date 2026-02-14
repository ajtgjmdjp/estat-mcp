"""Tests for estat_mcp.client."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from estat_mcp.client import EstatAPIError, EstatClient, _RateLimiter, _ensure_list, _parse_numeric


class TestHelpers:
    def test_ensure_list_with_list(self) -> None:
        assert _ensure_list([1, 2]) == [1, 2]

    def test_ensure_list_with_dict(self) -> None:
        assert _ensure_list({"a": 1}) == [{"a": 1}]

    def test_ensure_list_with_none(self) -> None:
        assert _ensure_list(None) == []

    def test_ensure_list_with_empty(self) -> None:
        assert _ensure_list([]) == []

    def test_parse_numeric_int(self) -> None:
        assert _parse_numeric("520999398") == 520999398

    def test_parse_numeric_float(self) -> None:
        assert _parse_numeric("99.5") == 99.5

    def test_parse_numeric_missing(self) -> None:
        assert _parse_numeric("-") is None
        assert _parse_numeric("***") is None
        assert _parse_numeric("X") is None

    def test_parse_numeric_string(self) -> None:
        assert _parse_numeric("N/A") == "N/A"


class TestEstatClient:
    def test_client_initialization(self) -> None:
        client = EstatClient(app_id="test_app_id")
        assert client._app_id == "test_app_id"
        assert client._timeout == 60.0

    def test_client_initialization_no_app_id(self) -> None:
        client = EstatClient()
        assert client._app_id is None

    @pytest.mark.asyncio
    async def test_client_context_manager(self) -> None:
        async with EstatClient(app_id="test") as client:
            assert isinstance(client, EstatClient)

    def test_build_params_with_app_id(self) -> None:
        client = EstatClient(app_id="test_id")
        params = client._build_params({"extra": "value"})
        assert params["appId"] == "test_id"
        assert params["extra"] == "value"

    def test_build_params_without_app_id(self) -> None:
        client = EstatClient()
        params = client._build_params()
        assert "appId" not in params

    def test_rate_limiter(self) -> None:
        limiter = _RateLimiter(1.0)
        assert limiter._interval == 1.0


class TestSearchStatsParsing:
    @pytest.mark.asyncio
    async def test_parse_search_response(self) -> None:
        mock_response = {
            "GET_STATS_LIST": {
                "RESULT": {"STATUS": 0},
                "DATALIST_INF": {
                    "NUMBER": 1,
                    "TABLE_INF": [
                        {
                            "@id": "0003410379",
                            "STAT_NAME": {"@code": "00200521", "$": "国勢調査"},
                            "GOV_ORG": {"@code": "00200", "$": "総務省"},
                            "STATISTICS_NAME": "国勢調査 人口等基本集計",
                            "TITLE": {"@no": "001", "$": "人口推計（令和元年）"},
                            "SURVEY_DATE": "201910",
                            "OPEN_DATE": "2019-12-20",
                        }
                    ],
                },
            }
        }

        client = EstatClient(app_id="test")
        with patch.object(client, "_get_json", new_callable=AsyncMock, return_value=mock_response):
            tables = await client.search_stats("人口")

        assert len(tables) == 1
        assert tables[0].id == "0003410379"
        assert tables[0].name == "人口推計（令和元年）"
        assert tables[0].gov_code == "00200521"
        assert tables[0].organization == "総務省"
        assert tables[0].statistics_name == "国勢調査 人口等基本集計"
        await client.close()

    @pytest.mark.asyncio
    async def test_parse_search_single_item(self) -> None:
        """Single TABLE_INF item (dict instead of list)."""
        mock_response = {
            "GET_STATS_LIST": {
                "RESULT": {"STATUS": 0},
                "DATALIST_INF": {
                    "NUMBER": 1,
                    "TABLE_INF": {
                        "@id": "0003410379",
                        "STAT_NAME": {"@code": "00200521", "$": "国勢調査"},
                        "GOV_ORG": {"@code": "00200", "$": "総務省"},
                        "STATISTICS_NAME": "国勢調査",
                        "TITLE": {"@no": "001", "$": "人口推計"},
                        "SURVEY_DATE": "201910",
                        "OPEN_DATE": "2019-12-20",
                    },
                },
            }
        }

        client = EstatClient(app_id="test")
        with patch.object(client, "_get_json", new_callable=AsyncMock, return_value=mock_response):
            tables = await client.search_stats("人口")

        assert len(tables) == 1
        assert tables[0].id == "0003410379"
        await client.close()

    @pytest.mark.asyncio
    async def test_parse_search_empty(self) -> None:
        """Empty response."""
        mock_response = {
            "GET_STATS_LIST": {
                "RESULT": {"STATUS": 0},
                "DATALIST_INF": {
                    "NUMBER": 0,
                    "TABLE_INF": [],
                },
            }
        }

        client = EstatClient(app_id="test")
        with patch.object(client, "_get_json", new_callable=AsyncMock, return_value=mock_response):
            tables = await client.search_stats("nonexistent")

        assert len(tables) == 0
        await client.close()


class TestGetMetaParsing:
    @pytest.mark.asyncio
    async def test_parse_meta_response(self) -> None:
        mock_response = {
            "GET_META_INFO": {
                "RESULT": {"STATUS": 0},
                "METADATA_INF": {
                    "CLASS_INF": {
                        "CLASS_OBJ": [
                            {
                                "@id": "tab",
                                "@name": "表章項目",
                                "CLASS": {"@code": "00001", "@name": "人口", "@level": "1", "@unit": "人"},
                            },
                            {
                                "@id": "cat01",
                                "@name": "男女別",
                                "CLASS": [
                                    {"@code": "100", "@name": "総数", "@level": "1"},
                                    {"@code": "110", "@name": "男", "@level": "2"},
                                ],
                            },
                            {
                                "@id": "time",
                                "@name": "時間軸",
                                "CLASS": [
                                    {"@code": "2024000", "@name": "2024年", "@level": "1"},
                                ],
                            },
                            {
                                "@id": "area",
                                "@name": "地域",
                                "CLASS": [
                                    {"@code": "00000", "@name": "全国", "@level": "1"},
                                ],
                            },
                        ]
                    }
                },
            }
        }

        client = EstatClient(app_id="test")
        with patch.object(client, "_get_json", new_callable=AsyncMock, return_value=mock_response):
            meta = await client.get_meta("0003410379")

        assert meta.stats_id == "0003410379"
        assert len(meta.table_items) == 1
        assert meta.table_items[0].code == "00001"
        assert meta.table_items[0].name == "人口"
        assert meta.table_items[0].unit == "人"
        assert "cat01" in meta.classification_items
        assert len(meta.classification_items["cat01"]) == 2
        assert len(meta.time_items) == 1
        assert meta.time_items[0].code == "2024000"
        assert len(meta.area_items) == 1
        assert meta.area_items[0].code == "00000"
        await client.close()

    @pytest.mark.asyncio
    async def test_parse_meta_single_class_obj(self) -> None:
        """Single CLASS_OBJ (dict instead of list)."""
        mock_response = {
            "GET_META_INFO": {
                "RESULT": {"STATUS": 0},
                "METADATA_INF": {
                    "CLASS_INF": {
                        "CLASS_OBJ": {
                            "@id": "tab",
                            "@name": "表章項目",
                            "CLASS": {"@code": "00001", "@name": "人口", "@level": "1"},
                        }
                    }
                },
            }
        }

        client = EstatClient(app_id="test")
        with patch.object(client, "_get_json", new_callable=AsyncMock, return_value=mock_response):
            meta = await client.get_meta("0003410379")

        assert len(meta.table_items) == 1
        assert meta.table_items[0].code == "00001"
        await client.close()


class TestGetDataParsing:
    @pytest.mark.asyncio
    async def test_parse_data_response(self) -> None:
        mock_response = {
            "GET_STATS_DATA": {
                "RESULT": {"STATUS": 0},
                "STATISTICAL_DATA": {
                    "RESULT_INF": {
                        "TOTAL_NUMBER": 100,
                        "FROM_NUMBER": 1,
                        "TO_NUMBER": 3,
                        "NEXT_KEY": 4,
                    },
                    "DATA_INF": {
                        "VALUE": [
                            {"@tab": "00001", "@cat01": "100", "@time": "2024000", "@area": "00000", "@unit": "人", "$": "125000000"},
                            {"@tab": "00001", "@cat01": "110", "@time": "2024000", "@area": "00000", "@unit": "人", "$": "61000000"},
                            {"@tab": "00001", "@cat01": "100", "@time": "2024000", "@area": "13000", "@unit": "人", "$": "-"},
                        ],
                    },
                },
            }
        }

        client = EstatClient(app_id="test")
        with patch.object(client, "_get_json", new_callable=AsyncMock, return_value=mock_response):
            data = await client.get_data("0003410379")

        assert data.stats_id == "0003410379"
        assert data.total_count == 100
        assert data.next_key == "4"
        assert len(data.values) == 3
        assert data.values[0].value == 125000000
        assert data.values[0].table_code == "00001"
        assert data.values[0].time_code == "2024000"
        assert data.values[0].area_code == "00000"
        assert data.values[0].classification_codes == {"cat01": "100"}
        assert data.values[2].value is None  # "-" is missing
        await client.close()

    @pytest.mark.asyncio
    async def test_parse_data_no_next_key(self) -> None:
        """Response without NEXT_KEY (last page)."""
        mock_response = {
            "GET_STATS_DATA": {
                "RESULT": {"STATUS": 0},
                "STATISTICAL_DATA": {
                    "RESULT_INF": {
                        "TOTAL_NUMBER": 1,
                        "FROM_NUMBER": 1,
                        "TO_NUMBER": 1,
                    },
                    "DATA_INF": {
                        "VALUE": [
                            {"@tab": "00001", "@time": "2024000", "@area": "00000", "$": "42"},
                        ],
                    },
                },
            }
        }

        client = EstatClient(app_id="test")
        with patch.object(client, "_get_json", new_callable=AsyncMock, return_value=mock_response):
            data = await client.get_data("0003410379")

        assert data.next_key is None
        assert data.total_count == 1
        assert len(data.values) == 1
        assert data.values[0].value == 42
        await client.close()

    @pytest.mark.asyncio
    async def test_parse_data_float_value(self) -> None:
        """Float values in data."""
        mock_response = {
            "GET_STATS_DATA": {
                "RESULT": {"STATUS": 0},
                "STATISTICAL_DATA": {
                    "RESULT_INF": {"TOTAL_NUMBER": 1},
                    "DATA_INF": {
                        "VALUE": [
                            {"@tab": "00001", "@time": "2024000", "$": "99.5"},
                        ],
                    },
                },
            }
        }

        client = EstatClient(app_id="test")
        with patch.object(client, "_get_json", new_callable=AsyncMock, return_value=mock_response):
            data = await client.get_data("test_id")

        assert data.values[0].value == 99.5
        await client.close()

    @pytest.mark.asyncio
    async def test_parse_data_missing_markers(self) -> None:
        """Various missing data markers."""
        mock_response = {
            "GET_STATS_DATA": {
                "RESULT": {"STATUS": 0},
                "STATISTICAL_DATA": {
                    "RESULT_INF": {"TOTAL_NUMBER": 4},
                    "DATA_INF": {
                        "VALUE": [
                            {"@tab": "00001", "$": "-"},
                            {"@tab": "00001", "$": "***"},
                            {"@tab": "00001", "$": "x"},
                            {"@tab": "00001", "$": "X"},
                        ],
                    },
                },
            }
        }

        client = EstatClient(app_id="test")
        with patch.object(client, "_get_json", new_callable=AsyncMock, return_value=mock_response):
            data = await client.get_data("test_id")

        for v in data.values:
            assert v.value is None
        await client.close()


class TestAPIStatusCheck:
    """Tests for e-Stat API application-level error detection."""

    def test_check_api_status_success(self) -> None:
        client = EstatClient(app_id="test")
        # STATUS 0 = success, should not raise
        data = {"GET_STATS_LIST": {"RESULT": {"STATUS": 0, "DATE": "2026-01-01"}}}
        client._check_api_status(data)

    def test_check_api_status_auth_error(self) -> None:
        client = EstatClient(app_id="test")
        data = {
            "GET_STATS_LIST": {
                "RESULT": {
                    "STATUS": 100,
                    "ERROR_MSG": "認証に失敗しました。",
                }
            }
        }
        with pytest.raises(EstatAPIError, match="認証に失敗しました"):
            client._check_api_status(data)

    def test_check_api_status_generic_error(self) -> None:
        client = EstatClient(app_id="test")
        data = {
            "GET_STATS_DATA": {
                "RESULT": {
                    "STATUS": 1,
                }
            }
        }
        with pytest.raises(EstatAPIError, match="API error"):
            client._check_api_status(data)

    def test_check_api_status_no_result(self) -> None:
        client = EstatClient(app_id="test")
        # No RESULT key — should not raise
        data = {"GET_STATS_LIST": {"DATALIST_INF": {}}}
        client._check_api_status(data)

    def test_env_var_fallback(self) -> None:
        """EstatClient reads ESTAT_APP_ID from env when no app_id given."""
        import os

        with patch.dict(os.environ, {"ESTAT_APP_ID": "env_test_key"}):
            client = EstatClient()
            assert client._app_id == "env_test_key"
