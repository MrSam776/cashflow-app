import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# =====================
# Cashflow Projection Logic
# =====================
def project_cashflow(
    annual_income,
    monthly_expenses,
    current_balance,
    monthly_contribution,
    annual_growth_rate,
    inflation_rate,
    projection_years,
    show_real=True,
):
    results = []

    balance = current_balance
    cumulative_contributions = 0
    cumulative_growth = 0
    annual_growth_rate_decimal = annual_growth_rate / 100
    inflation_rate_decimal = inflation_rate / 100

    for year in range(1, projection_years + 1):
        yearly_income = annual_income
        yearly_expenses = monthly_expenses * 12
        yearly_contributions = monthly_contribution * 12

        # Update contributions
        cumulative_contributions += yearly_contributions
        balance += yearly_contributions

        # Apply growth
        growth = balance * annual_growth_rate_decimal
        cumulative_growth += growth
        balance += growth

        # Deduct expenses
        balance -= yearly_expenses

        # Inflation-adjusted (real values)
        if show_real:
            discount_factor = (1 + inflation_rate_decimal) ** year
            display_balance = balance / discount_factor
            display_contributions = cumulative_contributions / discount_factor
            display_growth = cumulative_growth / discount_factor
            display_expenses = (yearly_expenses * year) / discount_factor
        else:
            display_balance = balance
            display_contributions = cumulative_contributions
            display_growth = cumulative_growth
            display_expenses = yearly_expenses * year

        results.append(
            {
                "Year": year,
                "Income": yearly_income,
                "Expenses": display_expenses,
                "Contributions": display_contributions,
                "Growth": display_growth,
                "End Balance": display_balance,
            }
        )

    return pd.DataFrame(results)

# =====================
# Streamlit UI
# =====================
st.set_page_config(page_title="Cashflow Modeller", layout="wide")

st.title("💷 Cashflow Modelling Tool")
st.markdown("A free, utilitarian cashflow modeller for DIY financial planning.")

# Sidebar inputs
st.sidebar.header("Inputs")

annual_income = st.sidebar.number_input("Annual Income (£)", min_value=0, value=50000, step=1000)
monthly_expenses = st.sidebar.number_input("Monthly Expenses (£)", min_value=0, value=2500, step=100)
current_balance = st.sidebar.number_input("Current Savings (£)", min_value=0, value=20000, step=1000)
monthly_contribution = st.sidebar.number_input("Monthly Contribution (£)", min_value=0, value=800, step=50)
annual_growth_rate = st.sidebar.number_input("Annual Growth Rate (%)", min_value=0.0, value=6.0, step=0.1)
inflation_rate = st.sidebar.number_input("Inflation Rate (%)", min_value=0.0, value=2.5, step=0.1)
projection_years = st.sidebar.slider("Projection Horizon (Years)", min_value=1, max_value=60, value=40)

# Real vs Nominal toggle
mode = st.sidebar.radio("Show Values In:", ["Real (£, inflation-adjusted)", "Nominal (£)"])
show_real = mode.startswith("Real")

# Run projection
df = project_cashflow(
    annual_income,
    monthly_expenses,
    current_balance,
    monthly_contribution,
    annual_growth_rate,
    inflation_rate,
    projection_years,
    show_real,
)

# =====================
# Graph
# =====================
fig = go.Figure()

# Stacked areas
fig.add_trace(go.Scatter(
    x=df["Year"], y=df["Contributions"],
    mode="lines", name="Contributions",
    stackgroup="one"
))
fig.add_trace(go.Scatter(
    x=df["Year"], y=df["Growth"],
    mode="lines", name="Growth",
    stackgroup="one"
))
fig.add_trace(go.Scatter(
    x=df["Year"], y=df["Expenses"],
    mode="lines", name="Expenses",
    stackgroup="one"
))

# Net balance line
fig.add_trace(go.Scatter(
    x=df["Year"], y=df["End Balance"],
    mode="lines+markers", name="Net Wealth",
    line=dict(color="black", width=3)
))

fig.update_layout(
    title="Cashflow Projection",
    xaxis_title="Year",
    yaxis_title="£ Value",
    legend_title="Components",
    hovermode="x unified",
    template="plotly_white"
)

st.plotly_chart(fig, use_container_width=True)

# =====================
# Data Table
# =====================
st.subheader("Projection Data")
st.dataframe(df, use_container_width=True)
