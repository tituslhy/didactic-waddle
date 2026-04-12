"""
Stock Ticker Dashboard — standalone Prefab UI preview
------------------------------------------------------
Run with:
    prefab serve app.py

UI-only mockup for layout verification. Uses hardcoded sample data.
No MCP server or yfinance calls needed.
"""

from prefab_ui.actions import SetState, ShowToast
from prefab_ui.app import PrefabApp
from prefab_ui.components import (
    Badge,
    Button,
    Card,
    CardContent,
    CardHeader,
    CardTitle,
    Column,
    ForEach,
    Grid,
    Heading,
    If,
    Input,
    Loader,
    Muted,
    Progress,
    Row,
    Separator,
    Text,
)
from prefab_ui.components.charts import BarChart, ChartSeries
from prefab_ui.components.control_flow import Else
from prefab_ui.rx import Rx

# ── Sample data (stands in for yfinance output) ───────────────────────────────
SAMPLE_RECORDS = [
    {"Date": "Jan 01", "Close": 182.5, "High": 184.2, "Low": 181.0, "Open": 183.0, "Volume": 52_000_000},
    {"Date": "Jan 08", "Close": 185.1, "High": 187.0, "Low": 183.5, "Open": 182.8, "Volume": 61_000_000},
    {"Date": "Jan 15", "Close": 188.3, "High": 190.1, "Low": 186.4, "Open": 185.2, "Volume": 48_000_000},
    {"Date": "Jan 22", "Close": 186.9, "High": 189.5, "Low": 185.0, "Open": 188.0, "Volume": 55_000_000},
    {"Date": "Jan 29", "Close": 191.2, "High": 193.0, "Low": 189.8, "Open": 187.5, "Volume": 70_000_000},
    {"Date": "Feb 05", "Close": 189.7, "High": 192.4, "Low": 188.0, "Open": 191.0, "Volume": 44_000_000},
    {"Date": "Feb 12", "Close": 194.5, "High": 196.2, "Low": 193.1, "Open": 190.0, "Volume": 66_000_000},
    {"Date": "Feb 19", "Close": 197.0, "High": 198.5, "Low": 195.5, "Open": 194.8, "Volume": 58_000_000},
]

SAMPLE_TICKERS = ["AAPL", "MSFT", "GOOG"]

# ── Reactive references ───────────────────────────────────────────────────────
panel_open    = Rx("panel_open")
is_fetching   = Rx("is_fetching")
is_charting   = Rx("is_charting")
active_ticker = Rx("active_ticker")
loaded        = Rx("loaded")
fetch_pct     = Rx("fetch_pct")
show_charts   = Rx("show_charts")
ticker_count  = Rx("ticker_count")

# ── App ───────────────────────────────────────────────────────────────────────
with PrefabApp(
    title="Stock Ticker Analysis",
    state={
        "panel_open":    False,
        "is_fetching":   False,
        "is_charting":   False,
        "active_ticker": "AAPL",
        "loaded":        SAMPLE_TICKERS,
        "fetch_pct":     60,            # non-zero so progress bar is visible
        "show_charts":   True,          # True so charts render on load for preview
        "ticker_count":  len(SAMPLE_TICKERS),
    },
) as app:

    with Row(gap=0, css_class="min-h-screen"):

        # ── Collapsible side panel ────────────────────────────────────────
        with If(panel_open):
            with Column(gap=4, css_class="w-52 border-r p-4 bg-muted/30 shrink-0"):
                with Row(align="center", css_class="justify-between"):
                    Text("Plot Tickers", css_class="font-semibold text-sm")
                    Button(
                        "✕",
                        variant="ghost",
                        css_class="h-6 w-6 p-0 text-xs",
                        on_click=SetState("panel_open", False),
                    )
                Separator()
                with Column(gap=2):
                    with ForEach("loaded") as item:
                        Button(
                            item,
                            variant="outline",
                            css_class="w-full text-xs",
                            on_click=[
                                SetState("active_ticker", "{{ $item }}"),
                                SetState("is_charting", True),
                                SetState("show_charts", True),
                                # In the real app, is_charting → False after CallTool resolves.
                                # For preview, we clear it immediately.
                                SetState("is_charting", False),
                            ],
                        )

        # ── Main content ──────────────────────────────────────────────────
        with Column(gap=6, css_class="flex-1 p-6 max-w-5xl mx-auto"):

            # Top bar: title + panel toggle button
            with Row(align="center", css_class="justify-between"):
                Heading("📈 Stock Ticker Analysis", level=1)
                with If(panel_open == False):  # noqa: E712
                    Button(
                        "☰  Plot Tickers",
                        variant="outline",
                        on_click=SetState("panel_open", True),
                    )

            Separator()

            # ── Ticker form ───────────────────────────────────────────────
            with Card():
                with CardHeader():
                    CardTitle("Fetch Stock Data")
                with CardContent():
                    with Column(gap=4):
                        Muted(
                            "Enter one or more ticker symbols separated by commas, "
                            "e.g. AAPL, MSFT, GOOG"
                        )
                        Input(
                            name="tickers_input",
                            label="Tickers",
                            placeholder="AAPL, MSFT, GOOG",
                        )
                        Input(
                            name="period_input",
                            label="Period (optional)",
                            placeholder="3mo  ·  1y  ·  5y  ·  max",
                        )
                        with Row(gap=3, align="center"):
                            Button(
                                is_fetching.then("Fetching…", "Fetch Data"),
                                disabled=is_fetching,
                                on_click=[
                                    SetState("is_fetching", True),
                                    ShowToast("Fetching… (preview only)", variant="default"),
                                ],
                            )
                            with If(is_fetching):
                                Loader(size="sm", variant="pulse")

            # ── Progress / spinner during fetch ───────────────────────────
            with If(is_fetching):
                with Card():
                    with CardContent(css_class="pt-4"):
                        with Column(gap=2):
                            with If(ticker_count == 1):
                                # Single ticker → indeterminate spinner
                                with Row(gap=2, align="center"):
                                    Loader(size="sm", variant="ios")
                                    Muted("Fetching data…")
                            with Else():
                                # Multiple tickers → percentage progress bar
                                Muted(f"Fetching… {fetch_pct}% complete")
                                Progress(value=fetch_pct, max=100)

            # ── Loaded tickers badges ─────────────────────────────────────
            with If(loaded):
                with Row(gap=2, align="center", css_class="flex-wrap"):
                    Muted("Loaded:")
                    with ForEach("loaded") as item:
                        Badge(item, variant="secondary")
                    Button(
                        "☰ Open Charts Panel",
                        variant="outline",
                        css_class="ml-auto",
                        on_click=SetState("panel_open", True),
                    )

            Separator()

            # ── Chart loading spinner ─────────────────────────────────────
            with If(is_charting):
                with Column(gap=3, css_class="items-center py-8"):
                    Loader(variant="ios", size="lg")
                    Muted(f"Loading chart for {active_ticker}…")

            # ── Chart dashboard ───────────────────────────────────────────
            with If(show_charts):
                with Column(gap=4):
                    Heading(f"{active_ticker} Dashboard", level=2)

                    with Grid(columns={"default": 1, "lg": 2}, gap=4):
                        for field, label in [
                            ("Close", "Close Price"),
                            ("High",  "Daily High"),
                            ("Low",   "Daily Low"),
                            ("Open",  "Open Price"),
                        ]:
                            with Card():
                                with CardHeader():
                                    CardTitle(label)
                                with CardContent():
                                    BarChart(
                                        data=SAMPLE_RECORDS,
                                        series=[ChartSeries(data_key=field, label=label)],
                                        x_axis="Date",
                                        height=220,
                                        bar_radius=2,
                                        show_legend=False,
                                        show_tooltip=True,
                                        show_grid=True,
                                        bar_size=4,
                                    )

                    with Card():
                        with CardHeader():
                            CardTitle("Volume")
                        with CardContent():
                            BarChart(
                                data=SAMPLE_RECORDS,
                                series=[ChartSeries(data_key="Volume", label="Volume")],
                                x_axis="Date",
                                height=160,
                                bar_radius=2,
                                show_legend=False,
                                show_tooltip=True,
                                show_grid=True,
                                bar_size=4,
                            )