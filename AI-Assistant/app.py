import pandas as pd
import streamlit as st
from pathlib import Path


st.set_page_config(page_title="Executive AI Business Analyst", page_icon="📈", layout="wide")

st.markdown(
    """
    <style>
    .hero-title {
        font-size: 2.1rem;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 0.2rem;
    }
    .hero-subtitle {
        font-size: 1rem;
        color: #475569;
        margin-bottom: 1rem;
    }
    .kpi-card {
        background: linear-gradient(135deg, #0f172a, #1e3a8a);
        color: white;
        padding: 16px;
        border-radius: 12px;
        margin-bottom: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    }
    .kpi-title {
        font-size: 0.9rem;
        opacity: 0.85;
        margin-bottom: 6px;
    }
    .kpi-value {
        font-size: 1.35rem;
        font-weight: 700;
    }
    .kpi-delta {
        font-size: 0.9rem;
        margin-top: 6px;
        opacity: 0.9;
    }
    .panel {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 16px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        margin-bottom: 16px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def format_currency(value: float) -> str:
    return f"£{value:,.0f}"


def format_percent(value: float) -> str:
    return f"{value:.1%}" if pd.notna(value) else "n/a"

REPO_ROOT = Path(__file__).resolve().parent.parent


def discover_data_files(workspace_ROOT: Path):
    product_files = sorted(REPO_ROOT.rglob("*product*.csv"), key=lambda p: str(p))
    transaction_files = sorted(REPO_ROOT.rglob("*transaction*.csv"), key=lambda p: str(p))
    returns_files = sorted(REPO_ROOT.rglob("*return*.csv"), key=lambda p: str(p))
    store_files = sorted(REPO_ROOT.rglob("*store*.csv"), key=lambda p: str(p))
    region_files = sorted(REPO_ROOT.rglob("*region*.csv"), key=lambda p: str(p))

    return {
        "products": product_files,
        "transactions": transaction_files,
        "returns": returns_files,
        "stores": store_files,
        "regions": region_files,
    }


def validate_columns(df: pd.DataFrame, required_columns: list, file_name: str):
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        raise ValueError(f"Required columns missing in {file_name}: {', '.join(missing)}")


def load_dashboard_data(workspace_root: Path):
    files = discover_data_files(workspace_root)

    product_files = [p for p in files["products"] if "customer" not in str(p).lower()]
    transaction_files = files["transactions"]
    returns_files = files["returns"]
    store_files = files["stores"]
    region_files = files["regions"]

    if not product_files:
        raise FileNotFoundError("No product CSV file was found in the workspace.")
    if not transaction_files:
        raise FileNotFoundError("No transaction CSV file was found in the workspace.")
    if not returns_files:
        raise FileNotFoundError("No returns CSV file was found in the workspace.")
    if not store_files:
        raise FileNotFoundError("No store CSV file was found in the workspace.")
    if not region_files:
        raise FileNotFoundError("No region CSV file was found in the workspace.")

    products = pd.concat([pd.read_csv(p) for p in product_files], ignore_index=True)
    transactions = pd.concat([pd.read_csv(p) for p in transaction_files], ignore_index=True)
    returns = pd.concat([pd.read_csv(p) for p in returns_files], ignore_index=True)
    stores = pd.concat([pd.read_csv(p) for p in store_files], ignore_index=True)
    regions = pd.concat([pd.read_csv(p) for p in region_files], ignore_index=True)

    validate_columns(products, ["product_id", "product_name", "product_retail_price", "product_cost"], "products")
    validate_columns(transactions, ["transaction_date", "product_id", "store_id", "quantity"], "transactions")
    validate_columns(returns, ["return_date", "product_id", "store_id", "quantity"], "returns")
    validate_columns(stores, ["store_id", "region_id", "store_name"], "stores")
    validate_columns(regions, ["region_id", "sales_region"], "regions")

    for df in [products, transactions, returns, stores, regions]:
        for col in df.columns:
            if "date" in col.lower():
                df[col] = pd.to_datetime(df[col], errors="coerce")

    products["product_retail_price"] = pd.to_numeric(products["product_retail_price"], errors="coerce").fillna(0)
    products["product_cost"] = pd.to_numeric(products["product_cost"], errors="coerce").fillna(0)
    transactions["quantity"] = pd.to_numeric(transactions["quantity"], errors="coerce").fillna(0)
    returns["quantity"] = pd.to_numeric(returns["quantity"], errors="coerce").fillna(0)

    transactions = transactions.merge(products[["product_id", "product_name", "product_retail_price", "product_cost"]], on="product_id", how="left")
    transactions = transactions.merge(stores[["store_id", "region_id", "store_name"]], on="store_id", how="left")
    transactions = transactions.merge(regions[["region_id", "sales_region"]], on="region_id", how="left")

    transactions["revenue"] = transactions["quantity"] * transactions["product_retail_price"]
    transactions["cost"] = transactions["quantity"] * transactions["product_cost"]
    transactions["profit"] = transactions["revenue"] - transactions["cost"]
    transactions["month"] = transactions["transaction_date"].dt.to_period("M").astype(str)

    returns = returns.merge(products[["product_id", "product_name"]], on="product_id", how="left")
    returns = returns.merge(stores[["store_id", "region_id", "store_name"]], on="store_id", how="left")
    returns = returns.merge(regions[["region_id", "sales_region"]], on="region_id", how="left")
    returns["month"] = returns["return_date"].dt.to_period("M").astype(str)

    months = sorted(transactions["month"].dropna().unique())
    if not months:
        raise ValueError("No valid transaction dates were found.")

    current_month = months[-1]
    previous_month = months[-2] if len(months) > 1 else months[-1]

    current_tx = transactions[transactions["month"] == current_month]
    previous_tx = transactions[transactions["month"] == previous_month]

    current_revenue = float(current_tx["revenue"].sum())
    previous_revenue = float(previous_tx["revenue"].sum())
    current_profit = float(current_tx["profit"].sum())
    previous_profit = float(previous_tx["profit"].sum())
    current_transactions = int(current_tx.shape[0])
    current_quantity_sold = int(current_tx["quantity"].sum())

    current_returns = int(returns.loc[returns["month"] == current_month, "quantity"].sum())
    previous_returns = int(returns.loc[returns["month"] == previous_month, "quantity"].sum())
    current_return_rate = current_returns / current_quantity_sold if current_quantity_sold else 0.0

    monthly_summary = (
        transactions.groupby("month")
        .agg(revenue=("revenue", "sum"), profit=("profit", "sum"), transactions=("profit", "size"), quantity_sold=("quantity", "sum"))
        .reset_index()
    )
    monthly_summary = monthly_summary.sort_values("month")
    monthly_summary["month_label"] = pd.to_datetime(monthly_summary["month"] + "-01")

    product_summary = (
        current_tx.groupby("product_name")
        .agg(revenue=("revenue", "sum"), profit=("profit", "sum"), quantity_sold=("quantity", "sum"))
        .reset_index()
        .sort_values("revenue", ascending=False)
    )

    region_summary = (
        current_tx.groupby("sales_region")
        .agg(revenue=("revenue", "sum"), profit=("profit", "sum"), quantity_sold=("quantity", "sum"))
        .reset_index()
        .sort_values("revenue", ascending=False)
    )

    store_summary = (
        current_tx.groupby("store_name")
        .agg(revenue=("revenue", "sum"), profit=("profit", "sum"), quantity_sold=("quantity", "sum"))
        .reset_index()
        .sort_values("revenue", ascending=False)
    )

    product_change = (
        current_tx.groupby("product_name")
        .agg(current_revenue=("revenue", "sum"))
        .join(
            previous_tx.groupby("product_name").agg(previous_revenue=("revenue", "sum")),
            how="left"
        )
        .fillna({"previous_revenue": 0.0})
    )
    product_change["change"] = product_change["current_revenue"] - product_change["previous_revenue"]
    product_change = product_change.reset_index().sort_values("change")

    region_change = (
        current_tx.groupby("sales_region")
        .agg(current_revenue=("revenue", "sum"))
        .join(
            previous_tx.groupby("sales_region").agg(previous_revenue=("revenue", "sum")),
            how="left"
        )
        .fillna({"previous_revenue": 0.0})
    )
    region_change["change"] = region_change["current_revenue"] - region_change["previous_revenue"]
    region_change = region_change.reset_index().sort_values("change")

    store_change = (
        current_tx.groupby("store_name")
        .agg(current_revenue=("revenue", "sum"))
        .join(
            previous_tx.groupby("store_name").agg(previous_revenue=("revenue", "sum")),
            how="left"
        )
        .fillna({"previous_revenue": 0.0})
    )
    store_change["change"] = store_change["current_revenue"] - store_change["previous_revenue"]
    store_change = store_change.reset_index().sort_values("change")

    profit_margin = current_profit / current_revenue if current_revenue else 0.0
    revenue_change = current_revenue - previous_revenue
    revenue_change_pct = revenue_change / previous_revenue if previous_revenue else 0.0
    profit_change = current_profit - previous_profit
    profit_change_pct = profit_change / previous_profit if previous_profit else 0.0

    return {
        "current_month": current_month,
        "previous_month": previous_month,
        "current_revenue": current_revenue,
        "previous_revenue": previous_revenue,
        "revenue_change": revenue_change,
        "revenue_change_pct": revenue_change_pct,
        "current_profit": current_profit,
        "previous_profit": previous_profit,
        "profit_change": profit_change,
        "profit_change_pct": profit_change_pct,
        "profit_margin": profit_margin,
        "transactions": current_transactions,
        "quantity_sold": current_quantity_sold,
        "current_returns": current_returns,
        "previous_returns": previous_returns,
        "return_rate": current_return_rate,
        "monthly_summary": monthly_summary,
        "product_summary": product_summary,
        "region_summary": region_summary,
        "store_summary": store_summary,
        "product_change": product_change,
        "region_change": region_change,
        "store_change": store_change,
    }


def build_executive_summary(metrics: dict) -> str:
    current_month_label = pd.Period(metrics["current_month"], freq="M").strftime("%B %Y")
    if metrics["revenue_change"] < 0:
        direction = "declined"
    elif metrics["revenue_change"] > 0:
        direction = "improved"
    else:
        direction = "was stable"

    return (
        f"In {current_month_label}, revenue was {format_currency(metrics['current_revenue'])} and profit was {format_currency(metrics['current_profit'])}. "
        f"The profit margin was {format_percent(metrics['profit_margin'])}. Revenue {direction} versus the previous month, "
        f"with a {format_currency(abs(metrics['revenue_change']))} change and a {format_percent(abs(metrics['revenue_change_pct']))} movement."
    )


def answer_question(question: str, metrics: dict):
    q = question.lower().strip()
    if "revenue this month" in q or "what is revenue" in q:
        return {
            "title": "Revenue this month",
            "figures": [
                f"Current month revenue: {format_currency(metrics['current_revenue'])}",
                f"Previous month revenue: {format_currency(metrics['previous_revenue'])}",
                f"Change: {format_currency(metrics['revenue_change'])} ({format_percent(metrics['revenue_change_pct'])})",
            ],
            "explanation": "Revenue for the current month is based on actual quantity sold multiplied by retail price.",
            "drivers": [
                f"Top positive product: {metrics['product_change'].iloc[-1]['product_name']}" if not metrics['product_change'].empty else "No product detail available",
                f"Top negative product: {metrics['product_change'].iloc[0]['product_name']}" if not metrics['product_change'].empty else "No product detail available",
            ],
            "recommendation": "Protect the strongest revenue lines and review the largest revenue detractors before the next trading cycle.",
            "chart": "revenue_trend",
        }

    if "profit this month" in q or "what is profit" in q:
        return {
            "title": "Profit this month",
            "figures": [
                f"Current month profit: {format_currency(metrics['current_profit'])}",
                f"Previous month profit: {format_currency(metrics['previous_profit'])}",
                f"Change: {format_currency(metrics['profit_change'])} ({format_percent(metrics['profit_change_pct'])})",
            ],
            "explanation": "Profit reflects actual revenue less cost, using product cost and quantity sold.",
            "drivers": [
                f"Current profit margin: {format_percent(metrics['profit_margin'])}",
                f"Top negative product: {metrics['product_change'].iloc[0]['product_name']}" if not metrics['product_change'].empty else "No product detail available",
            ],
            "recommendation": "Focus on margin quality in the weakest product and regional segments.",
            "chart": "profit_trend",
        }

    if "compared with last month" in q or "compared with previous month" in q or "performing compared" in q:
        return {
            "title": "Performance versus last month",
            "figures": [
                f"Revenue change: {format_currency(metrics['revenue_change'])} ({format_percent(metrics['revenue_change_pct'])})",
                f"Profit change: {format_currency(metrics['profit_change'])} ({format_percent(metrics['profit_change_pct'])})",
                f"Transactions: {metrics['transactions']}",
            ],
            "explanation": "The month-over-month comparison uses the latest complete month versus the prior month in the available data.",
            "drivers": [
                f"Largest negative product: {metrics['product_change'].iloc[0]['product_name']}" if not metrics['product_change'].empty else "No product detail available",
                f"Largest negative region: {metrics['region_change'].iloc[0]['sales_region']}" if not metrics['region_change'].empty else "No region detail available",
            ],
            "recommendation": "Prioritise recovery in the weakest areas while protecting margin discipline.",
            "chart": "trend_table",
        }

    if "why did revenue drop" in q or "revenue drop" in q or "decline" in q:
        negative_products = metrics["product_change"].head(5)
        negative_regions = metrics["region_change"].head(5)
        return {
            "title": "Why revenue changed",
            "figures": [
                f"Current revenue: {format_currency(metrics['current_revenue'])}",
                f"Previous revenue: {format_currency(metrics['previous_revenue'])}",
                f"Difference: {format_currency(metrics['revenue_change'])} ({format_percent(metrics['revenue_change_pct'])})",
            ],
            "explanation": "Revenue movement is being explained by the products and regions that changed the most between the current and prior month.",
            "drivers": [
                f"Negative products: {', '.join(negative_products['product_name'].tolist())}" if not negative_products.empty else "No negative product contributors found",
                f"Negative regions: {', '.join(negative_regions['sales_region'].tolist())}" if not negative_regions.empty else "No negative regional contributors found",
            ],
            "recommendation": "Investigate the largest revenue losses first and support recovery plans in those areas.",
            "chart": "revenue_drivers",
        }

    if "why did profit change" in q or "profit change" in q:
        negative_products = metrics["product_change"].head(5)
        return {
            "title": "Why profit changed",
            "figures": [
                f"Current profit: {format_currency(metrics['current_profit'])}",
                f"Previous profit: {format_currency(metrics['previous_profit'])}",
                f"Difference: {format_currency(metrics['profit_change'])} ({format_percent(metrics['profit_change_pct'])})",
            ],
            "explanation": "Profit movement is driven by volume, pricing and cost behaviour in the current month versus the prior month.",
            "drivers": [
                f"Negative products: {', '.join(negative_products['product_name'].tolist())}" if not negative_products.empty else "No negative product contributors found",
                f"Current margin: {format_percent(metrics['profit_margin'])}",
            ],
            "recommendation": "Target margin protection in the products with the largest negative profit movement.",
            "chart": "profit_drivers",
        }

    if "which products caused the decline" in q or "products caused" in q:
        negative_products = metrics["product_change"].head(5)
        return {
            "title": "Products contributing to decline",
            "figures": [
                f"Current month revenue: {format_currency(metrics['current_revenue'])}",
                f"Previous month revenue: {format_currency(metrics['previous_revenue'])}",
            ],
            "explanation": "The products listed below are the largest detractors versus the prior month.",
            "drivers": [
                f"{row['product_name']}: {format_currency(row['change'])}" for _, row in negative_products.iterrows()
            ],
            "recommendation": "Focus commercial attention and promotional support on the strongest recovery candidates.",
            "chart": "product_table",
        }

    if "which stores underperformed" in q:
        underperforming_stores = metrics["store_change"].head(5)
        return {
            "title": "Underperforming stores",
            "figures": [
                f"Current month revenue: {format_currency(metrics['current_revenue'])}",
            ],
            "explanation": "Stores are ranked by revenue change versus the prior month.",
            "drivers": [
                f"{row['store_name']}: {format_currency(row['change'])}" for _, row in underperforming_stores.iterrows()
            ],
            "recommendation": "Review store execution, local activity and stock availability for the weakest stores.",
            "chart": "store_table",
        }

    if "which regions underperformed" in q:
        underperforming_regions = metrics["region_change"].head(5)
        return {
            "title": "Underperforming regions",
            "figures": [
                f"Current month revenue: {format_currency(metrics['current_revenue'])}",
            ],
            "explanation": "Regions are ranked by revenue change versus the prior month.",
            "drivers": [
                f"{row['sales_region']}: {format_currency(row['change'])}" for _, row in underperforming_regions.iterrows()
            ],
            "recommendation": "Concentrate management attention on the regions with the largest revenue decline.",
            "chart": "region_table",
        }

    if "what should management focus on" in q or "management focus" in q:
        top_negative_product = metrics["product_change"].iloc[0] if not metrics["product_change"].empty else None
        top_negative_region = metrics["region_change"].iloc[0] if not metrics["region_change"].empty else None
        return {
            "title": "Management focus areas",
            "figures": [
                f"Revenue change: {format_currency(metrics['revenue_change'])}",
                f"Profit change: {format_currency(metrics['profit_change'])}",
            ],
            "explanation": "The highest-priority actions are the areas with the largest current-month decline versus the prior month.",
            "drivers": [
                f"Largest negative product: {top_negative_product['product_name']} ({format_currency(top_negative_product['change'])})" if top_negative_product is not None else "No product detail available",
                f"Largest negative region: {top_negative_region['sales_region']} ({format_currency(top_negative_region['change'])})" if top_negative_region is not None else "No regional detail available",
            ],
            "recommendation": "Coordinate recovery actions around the weakest product and regional segments while protecting margin quality.",
            "chart": "focus_summary",
        }

    return {
        "title": "Executive insight",
        "figures": [f"Current month revenue: {format_currency(metrics['current_revenue'])}", f"Current month profit: {format_currency(metrics['current_profit'])}"],
        "explanation": "Please ask one of the supported executive questions about revenue, profit, performance, product declines, stores or regions.",
        "drivers": ["No specific drivers available for this question"],
        "recommendation": "Use one of the supported leadership questions to receive a focused executive view.",
        "chart": "none",
    }


workspace_root = Path(__file__).resolve().parent.parent

try:
    metrics = load_dashboard_data(workspace_root)
except FileNotFoundError as exc:
    st.error(str(exc))
    st.stop()
except ValueError as exc:
    st.error(str(exc))
    st.stop()

st.markdown("<div class='hero-title'>Executive AI Business Analyst</div>", unsafe_allow_html=True)
st.markdown("<div class='hero-subtitle'>Senior leadership view of revenue, profitability and business performance for Maven Market</div>", unsafe_allow_html=True)

st.markdown("### Executive Summary")
st.info(build_executive_summary(metrics))

st.markdown("### KPI Dashboard")
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(f"<div class='kpi-card'><div class='kpi-title'>Revenue</div><div class='kpi-value'>{format_currency(metrics['current_revenue'])}</div><div class='kpi-delta'>vs previous month: {format_currency(metrics['revenue_change'])}</div></div>", unsafe_allow_html=True)
with col2:
    st.markdown(f"<div class='kpi-card'><div class='kpi-title'>Profit</div><div class='kpi-value'>{format_currency(metrics['current_profit'])}</div><div class='kpi-delta'>vs previous month: {format_currency(metrics['profit_change'])}</div></div>", unsafe_allow_html=True)
with col3:
    st.markdown(f"<div class='kpi-card'><div class='kpi-title'>Profit Margin</div><div class='kpi-value'>{format_percent(metrics['profit_margin'])}</div><div class='kpi-delta'>Current month margin</div></div>", unsafe_allow_html=True)

col4, col5, col6 = st.columns(3)
with col4:
    st.markdown(f"<div class='kpi-card'><div class='kpi-title'>Revenue vs Previous Month</div><div class='kpi-value'>{format_percent(metrics['revenue_change_pct'])}</div><div class='kpi-delta'>{format_currency(metrics['revenue_change'])} change</div></div>", unsafe_allow_html=True)
with col5:
    st.markdown(f"<div class='kpi-card'><div class='kpi-title'>Transactions</div><div class='kpi-value'>{metrics['transactions']:,}</div><div class='kpi-delta'>Current month</div></div>", unsafe_allow_html=True)
with col6:
    st.markdown(f"<div class='kpi-card'><div class='kpi-title'>Return Rate</div><div class='kpi-value'>{format_percent(metrics['return_rate'])}</div><div class='kpi-delta'>Returns over units sold</div></div>", unsafe_allow_html=True)

st.markdown("### Monthly Revenue and Profit Trend")
trend_chart = metrics["monthly_summary"].copy()
trend_chart = trend_chart[["month", "revenue", "profit"]].rename(columns={"revenue": "Revenue", "profit": "Profit"})
trend_chart.set_index("month", inplace=True)
st.line_chart(trend_chart)

col7, col8 = st.columns(2)
with col7:
    st.markdown("### Top 10 Products by Revenue")
    top_products = metrics["product_summary"].head(10)[["product_name", "revenue"]].rename(columns={"product_name": "Product", "revenue": "Revenue"})
    st.bar_chart(top_products.set_index("Product"), horizontal=True)
with col8:
    st.markdown("### Revenue by Region")
    region_chart = metrics["region_summary"][["sales_region", "revenue"]].rename(columns={"sales_region": "Region", "revenue": "Revenue"})
    st.bar_chart(region_chart.set_index("Region"), horizontal=True)

st.markdown("### Revenue Change Drivers")
col9, col10 = st.columns(2)
with col9:
    st.markdown("#### Top 5 negative product contributors")
    negative_products = metrics["product_change"].head(5)[["product_name", "change"]].rename(columns={"product_name": "Product", "change": "Impact"})
    negative_products["Impact"] = negative_products["Impact"].apply(lambda x: format_currency(x))
    st.dataframe(negative_products, use_container_width=True, hide_index=True)
with col10:
    st.markdown("#### Top 5 positive product contributors")
    positive_products = metrics["product_change"].tail(5)[["product_name", "change"]].rename(columns={"product_name": "Product", "change": "Impact"})
    positive_products["Impact"] = positive_products["Impact"].apply(lambda x: format_currency(x))
    st.dataframe(positive_products, use_container_width=True, hide_index=True)

col11, col12 = st.columns(2)
with col11:
    st.markdown("#### Top 5 underperforming stores")
    underperforming_stores = metrics["store_change"].head(5)[["store_name", "change"]].rename(columns={"store_name": "Store", "change": "Impact"})
    underperforming_stores["Impact"] = underperforming_stores["Impact"].apply(lambda x: format_currency(x))
    st.dataframe(underperforming_stores, use_container_width=True, hide_index=True)
with col12:
    st.markdown("#### Top 5 underperforming regions")
    underperforming_regions = metrics["region_change"].head(5)[["sales_region", "change"]].rename(columns={"sales_region": "Region", "change": "Impact"})
    underperforming_regions["Impact"] = underperforming_regions["Impact"].apply(lambda x: format_currency(x))
    st.dataframe(underperforming_regions, use_container_width=True, hide_index=True)

st.markdown("### Ask the Executive Analyst")
question = st.text_area("Ask a business question", placeholder="Example: Why did revenue drop this month?")

if question:
    response = answer_question(question, metrics)
    st.markdown(f"#### {response['title']}")
    for item in response["figures"]:
        st.write(f"- {item}")
    st.markdown("**Executive explanation**")
    st.write(response["explanation"])
    st.markdown("**Main drivers**")
    for item in response["drivers"]:
        st.write(f"- {item}")
    st.markdown("**Recommendation**")
    st.success(response["recommendation"])

    if response["chart"] == "revenue_trend":
        st.line_chart(metrics["monthly_summary"].set_index("month")["revenue"])
    elif response["chart"] == "profit_trend":
        st.line_chart(metrics["monthly_summary"].set_index("month")["profit"])
    elif response["chart"] == "revenue_drivers":
        st.dataframe(metrics["product_change"].head(5)[["product_name", "change"]].rename(columns={"product_name": "Product", "change": "Impact"}), use_container_width=True, hide_index=True)
    elif response["chart"] == "product_table":
        st.dataframe(metrics["product_change"].head(5)[["product_name", "change"]].rename(columns={"product_name": "Product", "change": "Impact"}), use_container_width=True, hide_index=True)
    elif response["chart"] == "store_table":
        st.dataframe(metrics["store_change"].head(5)[["store_name", "change"]].rename(columns={"store_name": "Store", "change": "Impact"}), use_container_width=True, hide_index=True)
    elif response["chart"] == "region_table":
        st.dataframe(metrics["region_change"].head(5)[["sales_region", "change"]].rename(columns={"sales_region": "Region", "change": "Impact"}), use_container_width=True, hide_index=True)

st.caption("Proof of concept using sample data. The production version can connect to an approved Power BI semantic model, live APIs and an authorised AI model.")