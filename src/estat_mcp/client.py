"""High-level async e-Stat API client.

This is the primary public interface of estat-mcp. All e-Stat operations —
statistics search, metadata retrieval, and data fetching — flow through
:class:`EstatClient`.

Example::

    import asyncio
    from estat_mcp import EstatClient

    async def main():
        async with EstatClient(app_id="YOUR_APP_ID") as client:
            tables = await client.search_stats("人口")
            meta = await client.get_meta(tables[0].id)
            data = await client.get_data(tables[0].id)
            print(data.values)

    asyncio.run(main())

e-Stat API v3.0 JSON response conventions:
    - UPPERCASE keys (GET_STATS_LIST, DATALIST_INF, TABLE_INF, etc.)
    - XML-style attributes prefixed with ``@`` (``@id``, ``@code``, ``@name``)
    - Text content stored in ``$`` key (e.g. ``{"@code": "00200", "$": "総務省"}``)
    - Single items may be a dict instead of a list; use :func:`_ensure_list`.
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
from loguru import logger

from estat_mcp.models import (
    DataSet,
    DataValue,
    MetaItem,
    StatsData,
    StatsMeta,
    StatsTable,
)

# e-Stat API v3.0 base URL
_BASE_URL = "https://api.e-stat.go.jp/rest/3.0/app/json/"

# HTTP status codes that warrant a retry
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}

# Default timeout (e-Stat can be slow)
_DEFAULT_TIMEOUT = 60.0

# Default rate limit (requests per second)
_DEFAULT_RATE_LIMIT = 1.0

# Special values treated as missing data
_MISSING_VALUES = {"-", "***", "x", "X", "...", "…"}


def _ensure_list(obj: Any) -> list[Any]:
    """Wrap a single dict in a list; pass through if already a list."""
    if isinstance(obj, list):
        return obj
    if obj:
        return [obj]
    return []


def _parse_numeric(raw: str) -> float | int | str | None:
    """Try to parse a string as int or float; return None for missing markers."""
    if raw in _MISSING_VALUES:
        return None
    try:
        return int(raw)
    except (ValueError, TypeError):
        pass
    try:
        return float(raw)
    except (ValueError, TypeError):
        return raw


class EstatAPIError(Exception):
    """Raised when the e-Stat API returns an unexpected response."""


class _RateLimiter:
    """Simple rate limiter for API requests."""

    def __init__(self, rate: float) -> None:
        self._interval = 1.0 / rate if rate > 0 else 0.0
        self._last_request: float = 0.0
        self._lock = asyncio.Lock()

    async def wait(self) -> None:
        """Wait if necessary to maintain the rate limit."""
        if self._interval <= 0:
            return
        async with self._lock:
            import time

            now = time.time()
            elapsed = now - self._last_request
            if elapsed < self._interval:
                await asyncio.sleep(self._interval - elapsed)
            self._last_request = time.time()


class EstatClient:
    """Async client for the e-Stat API v3.0."""

    def __init__(
        self,
        app_id: str | None = None,
        timeout: float = _DEFAULT_TIMEOUT,
        rate_limit: float = _DEFAULT_RATE_LIMIT,
    ) -> None:
        import os

        self._app_id = app_id or os.environ.get("ESTAT_APP_ID")
        if not self._app_id:
            logger.warning("No app_id provided. Set app_id or ESTAT_APP_ID env var.")

        self._timeout = timeout
        self._limiter = _RateLimiter(rate_limit)
        self._base_url = _BASE_URL

        self._http = httpx.AsyncClient(
            timeout=self._timeout,
            headers={"Accept": "application/json"},
        )

    async def close(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> EstatClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()

    def _build_params(self, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if self._app_id:
            params["appId"] = self._app_id
        if extra:
            params.update(extra)
        return params

    async def _request_with_retry(
        self, url: str, params: dict[str, Any]
    ) -> httpx.Response:
        last_exc: BaseException | None = None
        max_retries = 3

        for attempt in range(max_retries):
            await self._limiter.wait()
            try:
                resp = await self._http.get(url, params=params)
                if resp.status_code not in _RETRYABLE_STATUS:
                    resp.raise_for_status()
                    return resp
                last_exc = httpx.HTTPStatusError(
                    f"HTTP {resp.status_code}",
                    request=resp.request,
                    response=resp,
                )
            except httpx.TimeoutException as e:
                last_exc = e

            if attempt < max_retries - 1:
                delay = 2**attempt
                logger.warning(f"Retry {attempt + 1}/{max_retries} after {delay}s")
                await asyncio.sleep(delay)

        if isinstance(last_exc, httpx.HTTPError):
            raise EstatAPIError(f"HTTP error: {last_exc}") from last_exc
        raise last_exc  # type: ignore[misc]

    async def _get_json(self, url: str, params: dict[str, Any]) -> Any:
        data = (await self._request_with_retry(url, params)).json()
        self._check_api_status(data)
        return data

    def _check_api_status(self, data: Any) -> None:
        """Check e-Stat API response for application-level errors.

        e-Stat returns HTTP 200 even for errors like invalid appId.
        Errors are indicated by STATUS != 0 in the RESULT object.
        """
        for key in data:
            result = data[key].get("RESULT") if isinstance(data[key], dict) else None
            if result and isinstance(result, dict):
                status = result.get("STATUS")
                if status is not None and status != 0:
                    error_msg = result.get("ERROR_MSG", f"API error (status={status})")
                    raise EstatAPIError(error_msg)

    async def search_stats(
        self,
        keyword: str | None = None,
        *,
        survey_years: str | None = None,
        open_years: str | None = None,
        stats_field: str | None = None,
        gov_code: str | None = None,
        limit: int = 100,
    ) -> list[StatsTable]:
        url = f"{self._base_url}getStatsList"
        params = self._build_params()

        if keyword:
            params["searchWord"] = keyword
        if survey_years:
            params["surveyYears"] = survey_years
        if open_years:
            params["openYears"] = open_years
        if stats_field:
            params["statsField"] = stats_field
        if gov_code:
            params["statsCode"] = gov_code
        if limit:
            params["limit"] = limit

        data = await self._get_json(url, params)

        result: list[StatsTable] = []
        datalist = (
            data.get("GET_STATS_LIST", {})
            .get("DATALIST_INF", {})
            .get("TABLE_INF", [])
        )
        for item in _ensure_list(datalist):
            gov_org = item.get("GOV_ORG", {})
            stat_name_obj = item.get("STAT_NAME", {})
            title = item.get("TITLE", {})
            table = StatsTable(
                id=str(item.get("@id", "")),
                name=title.get("$", "") if isinstance(title, dict) else str(title),
                gov_code=(
                    stat_name_obj.get("@code")
                    if isinstance(stat_name_obj, dict)
                    else None
                ),
                survey_date=str(item.get("SURVEY_DATE", "")) or None,
                open_date=item.get("OPEN_DATE"),
                organization=(
                    gov_org.get("$") if isinstance(gov_org, dict) else None
                ),
                statistics_name=item.get("STATISTICS_NAME"),
            )
            result.append(table)

        logger.info(f"Found {len(result)} statistical tables")
        return result

    async def get_meta(self, stats_id: str) -> StatsMeta:
        url = f"{self._base_url}getMetaInfo"
        params = self._build_params({"statsDataId": stats_id})

        data = await self._get_json(url, params)

        metadata = data.get("GET_META_INFO", {}).get("METADATA_INF", {})
        class_inf = metadata.get("CLASS_INF", {})
        class_objs = _ensure_list(class_inf.get("CLASS_OBJ", []))

        table_items: list[MetaItem] = []
        classification_items: dict[str, list[MetaItem]] = {}
        time_items: list[MetaItem] = []
        area_items: list[MetaItem] = []

        for obj in class_objs:
            obj_id = obj.get("@id", "")
            classes = _ensure_list(obj.get("CLASS", []))
            items = [
                MetaItem(
                    code=c.get("@code", ""),
                    name=c.get("@name", ""),
                    level=int(c.get("@level", "1")),
                    unit=c.get("@unit"),
                )
                for c in classes
            ]

            if obj_id == "tab":
                table_items = items
            elif obj_id == "time":
                time_items = items
            elif obj_id == "area":
                area_items = items
            elif obj_id.startswith("cat"):
                classification_items[obj_id] = items

        return StatsMeta(
            stats_id=stats_id,
            table_items=table_items,
            classification_items=classification_items,
            time_items=time_items,
            area_items=area_items,
        )

    async def get_data(
        self,
        stats_id: str,
        *,
        dataset_id: str | None = None,
        lv_tab: str | None = None,
        cd_tab: str | None = None,
        lv_time: str | None = None,
        cd_time: str | None = None,
        lv_area: str | None = None,
        cd_area: str | None = None,
        cd_cat01: str | None = None,
        start_position: int | None = None,
        limit: int = 100000,
    ) -> StatsData:
        url = f"{self._base_url}getStatsData"
        params: dict[str, Any] = {}

        if dataset_id:
            params["dataSetId"] = dataset_id
        else:
            params["statsDataId"] = stats_id

        if lv_tab:
            params["lvTab"] = lv_tab
        if cd_tab:
            params["cdTab"] = cd_tab
        if lv_time:
            params["lvTime"] = lv_time
        if cd_time:
            params["cdTime"] = cd_time
        if lv_area:
            params["lvArea"] = lv_area
        if cd_area:
            params["cdArea"] = cd_area
        if cd_cat01:
            params["cdCat01"] = cd_cat01
        if start_position:
            params["startPosition"] = start_position
        if limit:
            params["limit"] = limit

        params = self._build_params(params)
        data = await self._get_json(url, params)

        stat_data = data.get("GET_STATS_DATA", {}).get("STATISTICAL_DATA", {})
        result_inf = stat_data.get("RESULT_INF", {})
        data_inf = stat_data.get("DATA_INF", {})

        values: list[DataValue] = []
        for item in _ensure_list(data_inf.get("VALUE", [])):
            raw_val = item.get("$")
            parsed_value: float | int | str | None = None
            if raw_val is not None:
                parsed_value = _parse_numeric(str(raw_val))

            classification_codes = {
                k.lstrip("@"): v for k, v in item.items() if k.startswith("@cat")
            }

            values.append(
                DataValue(
                    value=parsed_value,
                    table_code=item.get("@tab"),
                    time_code=item.get("@time"),
                    area_code=item.get("@area"),
                    classification_codes=classification_codes,
                )
            )

        total_count = result_inf.get("TOTAL_NUMBER", len(values))
        next_key_raw = result_inf.get("NEXT_KEY")
        next_key = str(next_key_raw) if next_key_raw is not None else None

        return StatsData(
            stats_id=stats_id,
            total_count=total_count,
            values=values,
            next_key=next_key,
        )

    async def get_all_data(
        self,
        stats_id: str,
        *,
        max_pages: int = 10,
        dataset_id: str | None = None,
        lv_tab: str | None = None,
        cd_tab: str | None = None,
        lv_time: str | None = None,
        cd_time: str | None = None,
        lv_area: str | None = None,
        cd_area: str | None = None,
        cd_cat01: str | None = None,
        limit: int = 100000,
    ) -> StatsData:
        """Fetch all statistical data with automatic pagination.

        Automatically follows next_key to fetch all pages until either:
        - No more pages (next_key is None)
        - max_pages limit is reached

        Args:
            stats_id: Statistics table ID.
            max_pages: Maximum number of pages to fetch (safety limit).
            dataset_id: Dataset ID (if using registered dataset).
            lv_tab: Table item level filter.
            cd_tab: Table item code filter.
            lv_time: Time axis level filter.
            cd_time: Time code filter.
            lv_area: Area level filter.
            cd_area: Area code filter.
            cd_cat01: Classification code 01 filter.
            limit: Records per page (default: 100000).

        Returns:
            StatsData with all values from all pages merged.
        """
        all_values: list[DataValue] = []
        start_position: int | None = None
        total_count = 0
        pages_fetched = 0

        while pages_fetched < max_pages:
            page = await self.get_data(
                stats_id,
                dataset_id=dataset_id,
                lv_tab=lv_tab,
                cd_tab=cd_tab,
                lv_time=lv_time,
                cd_time=cd_time,
                lv_area=lv_area,
                cd_area=cd_area,
                cd_cat01=cd_cat01,
                start_position=start_position,
                limit=limit,
            )

            all_values.extend(page.values)
            total_count = page.total_count
            pages_fetched += 1

            if page.next_key is None:
                break

            start_position = int(page.next_key)
            logger.debug(f"Fetching page {pages_fetched + 1} (start_position={start_position})")

        if pages_fetched >= max_pages and start_position is not None:
            logger.warning(f"Reached max_pages ({max_pages}). {len(all_values)}/{total_count} records fetched.")

        return StatsData(
            stats_id=stats_id,
            total_count=total_count,
            values=all_values,
            next_key=str(start_position) if pages_fetched >= max_pages else None,
        )

    async def register_dataset(
        self,
        stats_id: str,
        dataset_id: str | None = None,
        **filters: str,
    ) -> DataSet:
        url = f"{self._base_url.replace('/json/', '/')}postDataset"
        params: dict[str, Any] = {"statsDataId": stats_id}

        if dataset_id:
            params["dataSetId"] = dataset_id
        params.update(filters)

        params = self._build_params(params)

        await self._limiter.wait()
        resp = await self._http.post(url, data=params)
        resp.raise_for_status()

        data = resp.json()
        result = data.get("result", {})

        return DataSet(
            id=result.get("dataSetId", dataset_id or ""),
            stats_id=stats_id,
            name=filters.get("name", ""),
            description=filters.get("description", ""),
        )
