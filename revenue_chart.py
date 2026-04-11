from prefab_ui.app import PrefabApp
from prefab_ui.components import Column, Heading
from prefab_ui.components.charts import BarChart, ChartSeries
from fastmcp import FastMCP
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

mcp = FastMCP("Dashboard")

@mcp.tool(app=True)
def revenue_chart(year: int) -> PrefabApp:
    """Show annual revenue as an interactive bar chart."""
    logger.info(f"Rendering revenue chart for year: {year}")
    data = [
        {"quarter": "Q1", "revenue": 42000},
        {"quarter": "Q2", "revenue": 51000},
        {"quarter": "Q3", "revenue": 47000},
        {"quarter": "Q4", "revenue": 63000},
    ]

    with Column(gap=4, css_class="p-6") as view:
        Heading(f"{year} Revenue")
        BarChart(
            data=data,
            series=[ChartSeries(data_key="revenue", label="Revenue")],
            x_axis="quarter",
        )

    return PrefabApp(view=view)

if __name__ == "__main__":
    mcp.run(transport="http", host="127.0.0.1", port=8888)