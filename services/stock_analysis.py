from __future__ import annotations

from typing import Annotated, Any, Dict, List, Optional

import pandas as pd
import yfinance as yf
from tqdm import tqdm

from fastmcp import FastMCPApp, FastMCP
from prefab_ui.actions import SetState, ShowToast
from prefab_ui.actions.mcp import CallTool
from prefab_ui.app import PrefabApp
from prefab_ui.components import (
    Badge,
    Button,
    Card,
    CardContent,
    CardHeader,
    CardTitle,
    Column,
    Form,
    Grid,
    Heading,
    If,
    Input,
    Loader,
    Muted,
    Progress,
    Row,
    Separator,
    Slot,
    Text,
)
from prefab_ui.components.charts import BarChart, ChartSeries
from prefab_ui.rx import RESULT, Rx

# ── In-memory store ───────────────────────────────────────────────────────────
ticker_data: dict[str, Any] = {}

# ── App ───────────────────────────────────────────────────────────────────────
app = FastMCPApp("Stock Analysis")

# ── Backend tool 1: fetch all tickers ─────────────────────────────────────────
@app.tool()
def get_info_for_tickers(
    tickers: Annotated[List[str], "List of stock ticker symbols, e.g. ['AAPL', 'GOOG']"],
    period: Optional[Annotated[str, "data period, e.g. '1mo', '3mo', '1y', '5y'"]] = "3mo",
    start_date: Optional[Annotated[str, "start date in YYYY-MM-DD format"]] = None,
    end_date: Optional[Annotated[str, "end date in YYYY-MM-DD format"]] = None,
) -> dict:
    """
    Fetch historical stock data for the given tickers.
    Returns a status dict with the list of loaded tickers.
    """
    loaded: list[str] = []
    total = len(tickers)

    for i, ticker in enumerate(tqdm(tickers, desc="Fetching stock ticker data")):
        df: pd.DataFrame = yf.download(
            ticker,
            period=period,
            start=start_date,
            end=end_date,
            progress=False,
        )
        if df.empty:
            continue
        # Flatten multi-level columns if present
        if isinstance(df.columns, pd.MultiIndex):
            df = df.stack(level=1).sort_values(["Ticker", "Date"], ascending=False).reset_index()
        else:
            df = df.reset_index()
            df["Ticker"] = ticker

        ticker_data[ticker] = df
        loaded.append(ticker)

    return {"loaded": loaded, "total": total}


# ── Backend tool 2: get data for a single ticker ──────────────────────────────
@app.tool()
def get_individual_ticker_data(
    ticker: str,
) -> Dict[str, List[dict]] | None:
    """
    Get historical OHLCV records for a single ticker as a list of dicts.
    Dates are formatted as short strings for chart x-axis labels.
    """
    df = ticker_data.get(ticker)
    if not isinstance(df, pd.DataFrame):
        return None

    keep = [c for c in ["Date", "Open", "High", "Low", "Close", "Volume"] if c in df.columns]
    out = df[keep].copy()

    # Format date as short label for chart x-axis
    if "Date" in out.columns:
        out["Date"] = pd.to_datetime(out["Date"]).dt.strftime("%b %d")

    # Reverse so oldest → newest on chart x-axis
    out = out.iloc[::-1].reset_index(drop=True)

    return {
        "ticker": ticker,
        "records": out.to_dict(orient="records"),
    }


# ── Backend tool 3: build the chart dashboard for one ticker ─────────────────
@app.tool()
def build_ticker_dashboard(ticker: str) -> PrefabApp:
    """
    Build a Prefab chart dashboard for one ticker (4 sub-charts: Close, High, Low, Open, Volume).
    Called from the UI via CallTool; the result fills a Slot.
    """
    result = get_individual_ticker_data(ticker)
    if result is None or not result.get("records"):
        with Column(gap=2) as view:
            Text(f"No data available for {ticker}.", css_class="text-destructive")
        return PrefabApp(view=view)

    records = result["records"]

    def make_chart(data_key: str, label: str, colour_class: str) -> None:
        with Card():
            with CardHeader():
                CardTitle(f"{ticker} — {label}")
            with CardContent():
                BarChart(
                    data=records,
                    series=[ChartSeries(data_key=data_key, label=label)],
                    x_axis="Date",
                    height=220,
                    bar_radius=2,
                    show_legend=False,
                    show_tooltip=True,
                    show_grid=True,
                    # Thin bars give line-chart feel when there are many points
                    bar_size=3,
                )

    with Column(gap=4, css_class="p-4") as view:
        Heading(f"{ticker} Dashboard", level=2)
        with Grid(columns={"default": 1, "lg": 2}, gap=4):
            make_chart("Close",  "Close Price",  "text-blue-500")
            make_chart("High",   "Daily High",   "text-green-500")
            make_chart("Low",    "Daily Low",    "text-red-500")
            make_chart("Open",   "Open Price",   "text-yellow-500")
        with Card():
            with CardHeader():
                CardTitle(f"{ticker} — Volume")
            with CardContent():
                BarChart(
                    data=records,
                    series=[ChartSeries(data_key="Volume", label="Volume")],
                    x_axis="Date",
                    height=160,
                    bar_radius=2,
                    show_legend=False,
                    show_tooltip=True,
                    show_grid=True,
                    bar_size=3,
                )

    return PrefabApp(view=view)


# ── UI entry point ────────────────────────────────────────────────────────────
@app.ui()
def stock_ticker_app() -> PrefabApp:
    """
    Open the Stock Ticker Analysis app.

    Home page with a ticker form + collapsible side panel.
    Fetching shows a progress loader (per-ticker % for multiple, spinner for one).
    Charting shows a loader before rendering each dashboard.
    """
    # Reactive state references
    tickers_raw   = Rx("tickers_raw")       # raw comma-separated input string
    loaded        = Rx("loaded")            # list of successfully loaded tickers
    is_fetching   = Rx("is_fetching")       # bool: fetch in progress
    fetch_pct     = Rx("fetch_pct")         # 0-100 progress during multi-fetch
    fetch_label   = Rx("fetch_label")       # e.g. "Fetching AAPL (1/3)..."
    single_ticker = Rx("single_ticker")     # bool: only 1 ticker requested
    panel_open    = Rx("panel_open")        # bool: side panel visible
    is_charting   = Rx("is_charting")       # bool: chart load in progress
    active_ticker = Rx("active_ticker")     # ticker currently being charted

    # ── Layout ───────────────────────────────────────────────────────────────
    with Row(gap=0, css_class="min-h-screen") as view:

        # ── Collapsible side panel ────────────────────────────────────────
        with If(panel_open):
            with Column(
                gap=4,
                css_class="w-56 border-r p-4 bg-muted/30 shrink-0",
            ):
                with Row(align="center", css_class="justify-between"):
                    Text("Charts", css_class="font-semibold text-sm")
                    Button(
                        "✕",
                        variant="ghost",
                        css_class="h-6 w-6 p-0",
                        on_click=SetState("panel_open", False),
                    )
                Separator()

                # One "Plot" button per loaded ticker
                with If(loaded):
                    with Column(gap=2):         
                        
                        from prefab_ui.components.control_flow import ForEach
                                       
                        with ForEach("loaded") as item:
                            Button(
                                item,
                                variant="outline",
                                css_class="w-full text-xs",
                                on_click=[
                                    SetState("active_ticker", "{{ $item }}"),
                                    SetState("is_charting", True),
                                    CallTool(
                                        build_ticker_dashboard,
                                        arguments={"ticker": "{{ $item }}"},
                                        on_success=[
                                            SetState("chart_slot", RESULT),
                                            SetState("is_charting", False),
                                        ],
                                        on_error=[
                                            SetState("is_charting", False),
                                            ShowToast("Failed to load chart", variant="error"),
                                        ],
                                    ),
                                ],
                            )

        # ── Main content area ─────────────────────────────────────────────
        with Column(gap=6, css_class="flex-1 p-6 max-w-5xl mx-auto"):

            # Top bar: title + panel toggle
            with Row(align="center", css_class="justify-between"):
                Heading("📈 Stock Ticker Analysis", level=1)
                with If(panel_open == False):  # noqa: E712
                    Button(
                        "☰ Charts",
                        variant="outline",
                        on_click=SetState("panel_open", True),
                    )

            Separator()

            # ── Ticker input form ─────────────────────────────────────────
            with Card():
                with CardHeader():
                    CardTitle("Fetch Stock Data")
                with CardContent():
                    with Column(gap=4):
                        Muted(
                            "Enter one or more ticker symbols separated by commas. "
                            "E.g.  AAPL, MSFT, GOOG"
                        )
                        with Form(
                            on_submit=CallTool(
                                get_info_for_tickers,
                                # Form field "tickers_raw" is a comma-separated string.
                                # We pass it as a list by splitting in the tool via the
                                # pre-processing wrapper below.
                                arguments={
                                    "tickers": "{{ tickers_input.split(',').map(t => t.trim()).filter(t => t) }}",
                                    "period": "{{ period_input || '3mo' }}",
                                },
                                on_success=[
                                    SetState("loaded",       "{{ $result.loaded }}"),
                                    SetState("is_fetching",  False),
                                    SetState("fetch_pct",    100),
                                    ShowToast(
                                        "{{ $result.loaded.length }} ticker(s) loaded!",
                                        variant="success",
                                    ),
                                ],
                                on_error=[
                                    SetState("is_fetching", False),
                                    ShowToast("Fetch failed — check your tickers.", variant="error"),
                                ],
                            )
                        ):
                            Input(
                                name="tickers_input",
                                label="Tickers",
                                placeholder="AAPL, MSFT, GOOG",
                                required=True,
                            )
                            Input(
                                name="period_input",
                                label="Period (optional)",
                                placeholder="3mo  ·  1y  ·  5y  ·  max",
                            )
                            with Row(gap=2, align="center"):
                                Button(
                                    is_fetching.then("Fetching…", "Fetch Data"),
                                    disabled=is_fetching,
                                    on_click=SetState("is_fetching", True),
                                )
                                with If(is_fetching):
                                    Loader(size="sm", variant="pulse")

            # ── Multi-ticker progress bar (hidden when single or idle) ────
            with If(is_fetching):
                with Card():
                    with CardContent(css_class="pt-4"):
                        with Column(gap=2):
                            Text(fetch_label, css_class="text-sm text-muted-foreground")
                            Progress(value=fetch_pct, max=100)

            # ── Loaded tickers badges ─────────────────────────────────────
            with If(loaded):
                with Row(gap=2, align="center", css_class="flex-wrap"):
                    Muted("Loaded:")
                    
                    from prefab_ui.components.control_flow import ForEach
                    with ForEach("loaded") as item:
                        Badge(item, variant="secondary")
                    Button(
                        "☰ Open Charts Panel",
                        variant="outline",
                        css_class="ml-auto",
                        on_click=SetState("panel_open", True),
                    )

            Separator()

            # ── Chart area ────────────────────────────────────────────────
            with If(is_charting):
                with Column(gap=3, css_class="items-center py-8"):
                    Loader(variant="ios", size="lg")
                    Muted(f"Loading chart for {active_ticker}…")

            # Slot that gets filled by build_ticker_dashboard via CallTool
            Slot("chart_slot")

    return PrefabApp(
        view=view,
        title="Stock Ticker Analysis",
        state={
            "tickers_raw":    "",
            "loaded":         [],
            "is_fetching":    False,
            "fetch_pct":      0,
            "fetch_label":    "Fetching…",
            "single_ticker":  False,
            "panel_open":     False,
            "is_charting":    False,
            "active_ticker":  "",
            "chart_slot":     None,
        },
    )

mcp = FastMCP("Stock Analysis Tool", providers=[app])

# ── Entrypoint ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    mcp.run(transport="http", host="127.0.0.1", port=8888)