"""Domain models for e-Stat API data.

All public models use Pydantic v2 for validation and serialization.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# StatsTable
# ---------------------------------------------------------------------------


class StatsTable(BaseModel):
    """A statistical table metadata from e-Stat.

    Attributes:
        id: Unique statistics table identifier (statsDataId).
        name: Table name in Japanese.
        gov_code: Government statistics code (5 or 8 digits).
        survey_date: Survey date information.
        open_date: Date the table was made available.
        organization: Organization name that published the statistics.
        statistics_name: Name of the statistical survey.
    """

    id: str
    name: str
    gov_code: str | None = None
    survey_date: str | None = None
    open_date: str | None = None
    organization: str | None = None
    statistics_name: str | None = None

    model_config = {"frozen": True}

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> StatsTable:
        """Construct from e-Stat API response.

        Handles both the real e-Stat API v3.0 format (UPPERCASE keys with
        @-prefixed attributes and $ text content) and a simplified format
        with plain/prefixed keys.

        Real e-Stat format example::

            {
                "@id": "0003410379",
                "STAT_NAME": {"@code": "00200521", "$": "国勢調査"},
                "GOV_ORG": {"@code": "00200", "$": "総務省"},
                "STATISTICS_NAME": "国勢調査 人口等基本集計",
                "TITLE": {"@no": "001", "$": "人口推計"},
                "SURVEY_DATE": "201910",
                "OPEN_DATE": "2019-12-20",
            }
        """
        # Detect real e-Stat API v3.0 format by checking for UPPERCASE keys
        # that are unique to the real format (TITLE, STAT_NAME, GOV_ORG, etc.)
        _estat_keys = {"TITLE", "STAT_NAME", "GOV_ORG", "STATISTICS_NAME", "SURVEY_DATE"}
        if _estat_keys & data.keys():
            title = data.get("TITLE", {})
            name = title.get("$", "") if isinstance(title, dict) else str(title) if title else ""

            stat_name_obj = data.get("STAT_NAME", {})
            gov_code = (
                stat_name_obj.get("@code")
                if isinstance(stat_name_obj, dict)
                else None
            )

            gov_org = data.get("GOV_ORG", {})
            organization = (
                gov_org.get("$") if isinstance(gov_org, dict) else None
            )

            return cls(
                id=str(data.get("@id", "")),
                name=name,
                gov_code=gov_code,
                survey_date=str(data.get("SURVEY_DATE", "")) or None,
                open_date=data.get("OPEN_DATE"),
                organization=organization,
                statistics_name=data.get("STATISTICS_NAME"),
            )

        # --- Fallback: simplified format with plain/@-prefixed keys ---
        def _get(key: str) -> Any:
            return data.get(key) or data.get(f"@{key}")

        # Get organization from gov_org object
        org = ""
        gov_org = data.get("gov_org", {})
        if isinstance(gov_org, dict):
            org = gov_org.get("$") or gov_org.get("@name", "")

        return cls(
            id=_get("id") or "",
            name=_get("statistic_name") or _get("name") or "",
            gov_code=_get("stats_code") or _get("gov_code"),
            survey_date=_get("survey_date") or _get("survey_data"),
            open_date=_get("open_date") or _get("open_data"),
            organization=org or _get("organization") or _get("stat_name"),
            statistics_name=_get("statistics_name") or _get("stat_name"),
        )


# ---------------------------------------------------------------------------
# StatsMeta
# ---------------------------------------------------------------------------


class MetaItem(BaseModel):
    """A single metadata item (表章事項, 分類事項, etc.)."""

    code: str
    name: str
    level: int = 1
    unit: str | None = None

    model_config = {"frozen": True}


class StatsMeta(BaseModel):
    """Metadata for a statistical table.

    Contains information about table structure including:
    - 表章事項 (table items)
    - 分類事項 (classification items, up to 15)
    - 時間軸事項 (time axis)
    - 地域事項 (area items)

    Attributes:
        stats_id: Statistics table ID.
        table_items: List of table header items (表章事項).
        classification_items: List of classification items by category.
        time_items: List of time axis items (時間軸事項).
        area_items: List of area items (地域事項).
    """

    stats_id: str
    table_items: list[MetaItem] = Field(default_factory=list)
    classification_items: dict[str, list[MetaItem]] = Field(default_factory=dict)
    time_items: list[MetaItem] = Field(default_factory=list)
    area_items: list[MetaItem] = Field(default_factory=list)

    model_config = {"frozen": True}

    def get_all_classifications(self) -> list[MetaItem]:
        """Return all classification items flattened."""
        items: list[MetaItem] = []
        for cat_list in self.classification_items.values():
            items.extend(cat_list)
        return items


# ---------------------------------------------------------------------------
# StatsData
# ---------------------------------------------------------------------------


class DataValue(BaseModel):
    """A single data value with its dimensions."""

    value: float | int | str | None
    table_code: str | None = None
    time_code: str | None = None
    area_code: str | None = None
    classification_codes: dict[str, str] = Field(default_factory=dict)

    model_config = {"frozen": True}


class StatsData(BaseModel):
    """Statistical data from e-Stat.

    Attributes:
        stats_id: Statistics table ID.
        total_count: Total number of data points.
        values: List of data values.
        next_key: Key for pagination (if more data available).
    """

    stats_id: str
    total_count: int = 0
    values: list[DataValue] = Field(default_factory=list)
    next_key: str | None = None

    model_config = {"frozen": True}

    def to_dicts(self) -> list[dict[str, Any]]:
        """Convert values to list of dictionaries."""
        result: list[dict[str, Any]] = []
        for v in self.values:
            d: dict[str, Any] = {"value": v.value}
            if v.table_code:
                d["table"] = v.table_code
            if v.time_code:
                d["time"] = v.time_code
            if v.area_code:
                d["area"] = v.area_code
            d.update(v.classification_codes)
            result.append(d)
        return result

    def to_polars(self) -> Any:
        """Convert to a Polars DataFrame.

        Requires polars to be installed (pip install estat-mcp[polars]).

        Returns a DataFrame with columns: value, table_code, time_code,
        area_code, and one column per classification code key.

        Raises:
            ImportError: If polars is not installed.
        """
        try:
            import polars as pl
        except ImportError:
            raise ImportError(
                "polars is required for to_polars(). "
                "Install it with: pip install estat-mcp[polars]"
            ) from None

        if not self.values:
            return pl.DataFrame()

        rows: list[dict[str, Any]] = []
        for v in self.values:
            row: dict[str, Any] = {
                "value": v.value,
                "table_code": v.table_code,
                "time_code": v.time_code,
                "area_code": v.area_code,
            }
            row.update(v.classification_codes)
            rows.append(row)

        return pl.DataFrame(rows)


# ---------------------------------------------------------------------------
# DataSet
# ---------------------------------------------------------------------------


class DataSet(BaseModel):
    """A registered dataset for filtering statistics.

    Datasets allow saving filter conditions for reuse.

    Attributes:
        id: Dataset ID.
        stats_id: Associated statistics table ID.
        name: Dataset name.
        description: Optional description.
    """

    id: str
    stats_id: str
    name: str = ""
    description: str = ""

    model_config = {"frozen": True}
