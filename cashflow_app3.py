import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json

st.set_page_config(page_title="Cashflow & Compound Growth App", layout="wide")

# ----------------------
# Core Calculation Logic
# ----------------------
def project_cashflow(
    annual_income,
    monthly_expenses,
    current_balance,
    monthly_contribution,
    annual_growth_rate,
    inflation_rate,
    projection_years,
    deposit_timing="Start",
    show_real=True,
):
    """
    Simulates monthly contributions and monthly compounding.
    - deposit_timing: "Start" = contributions at beginning of month (annuity-due),
                      "End"   = contributions at end of month (ordinary annuity)
    - Inflation-adjusted results if show_real=True.
    """

    monthly_rate = annual_growth_rate / 100.0 / 12.0
    balance = float(current_balance)
    cum_deposits = 0.0
    cum_interest = 0.0
    results = []
    cumulative_inflation = 1.0

    for year in range(1, projection_years + 1):
        year_deposits = 0.0
        year_interest = 0.0
        year_expenses = 0.0

        for m in range(12):
            # Contributions at start or end of month
            if deposit_timing == "Start":
                balance += monthly_contribution
                year_deposits += monthly_contribution
                cum_deposits += monthly_contribution

            # Apply monthly interest
            interest = balance * monthly_rate
            balance += interest
            year_interest += interest
            cum_interest += interest

            # Expenses (assumed monthly at month end)
            balance -= monthly_expenses
            year_expenses += monthly_expenses

            if deposit_timing == "End":
                balance += monthly_contribution
                year_deposits += monthly_contribution
                cum_deposits += monthly_contribution

        # End of year (nominal values)
        end_nominal = balance

        # Inflation adjustment
        cumulative_inflation *= (1.0 + inflation_rate / 100.0)
        if show_real:
            factor = cumulative_inflation
        else:
            factor = 1.0

        results.append(
            {
                "Year": year,
                "Deposits (cumulative)": round(cum_deposits / factor, 2),
                "Interest (cumulative)": round(cum_interest / factor, 2),
                "Expenses (year)": round(year_expenses / factor, 2),
                "End Balance": round(end_nominal / factor, 2),
            }
        )

    return pd.DataFrame(results)


# ----------------------
# Streamlit App
# ----------------------
st.title("💰 Cashflow & Compound Growth Model")

with st.sidebar:
    st.header("Inputs")

    current_balance = st.number_input("Current Balance (£)", min_value=0.0, value=0.0, step=100.0)
    monthly_contribution = st.number_input("Monthly Contributions (£)", min_value=0.0, value=800.0, step=100.0)
    monthly_expenses = st.number_input("Monthly Expenses (£)", min_value=0.0, value=0.0, step=50.0)
    annual_income = st.number_input("Annual Income (£)", min_value=0.0, value=0.0, step=1000.0)

    annual_growth_rate = st.number_input("Annual Growth Rate (%)", min_value=0.0, value=6.0, step=0.5)
    inflation_rate = st.number_input("Inflation Rate (%)", min_value=0.0, value=2.0, step=0.5)

    projection_years = st.slider("Projection Years", 1, 50, 30)

    deposit_timing = st.selectbox(
        "Deposit Timing",
        options=["Start", "End"],
        index=0,
        help="Choose whether deposits are made at the start or end of the month."
    )

    show_real = st.radio("Show Values:", ["Real (inflation-adjusted)", "Nominal"], index=0)
    show_real_flag = True if show_real.startswith("Real") else False

    # Save/Load functionality
    st.subheader("💾 Save & Load")
    if st.button("Save Inputs"):
        inputs = {
            "current_balance": current_balance,
            "monthly_contribution": monthly_contribution,
            "monthly_expenses": monthly_expenses,
            "annual_income": annual_income,
            "annual_growth_rate": annual_growth_rate,
            "inflation_rate": inflation_rate,
            "projection_years": projection_years,
            "deposit_timing": deposit_timing,
            "show_real": show_real_flag,
        }
        with open("inputs.json", "w") as f:
            json.dump(inputs, f)
        st.success("Inputs saved to inputs.json")

    uploaded_file = st.file_uploader("Load Inputs", type="json")
    if uploaded_file is not None:
        loaded_inputs = json.load(uploaded_file)
        st.session_state.update(loaded_inputs)
        st.success("Inputs loaded! Please refresh to apply.")


# ----------------------
# Run Projection
# ----------------------
df = project_cashflow(
    annual_income,
    monthly_expenses,
    current_balance,
    monthly_contribution,
    annual_growth_rate,
    inflation_rate,
    projection_years,
    deposit_timing,
    show_real_flag,
)

st.subheader("Projection Table")
st.dataframe(df, use_container_width=True)

# ----------------------
# Plot Graph
# ----------------------
fig = go.Figure()

fig.add_trace(go.Scatter(
    x=df["Year"],
    y=df["End Balance"],
    mode="lines+markers",
    name="End Balance",
    line=dict(color="black", width=3)
))

fig.add_trace(go.Bar(
    x=df["Year"],
    y=df["Deposits (cumulative)"],
    name="Deposits",
    marker=dict(color="blue"),
    opacity=0.6
))

fig.add_trace(go.Bar(
    x=df["Year"],
    y=df["Interest (cumulative)"],
    name="Growth (Interest)",
    marker=dict(color="green"),
    opacity=0.6
))

fig.add_trace(go.Bar(
    x=df["Year"],
    y=df["Expenses (year)"],
    name="Expenses",
    marker=dict(color="red"),
    opacity=0.6
))

fig.update_layout(
    barmode="stack",
    title="Cashflow Projection",
    xaxis_title="Year",
    yaxis_title="Balance (£)",
    legend_title="Components",
    template="plotly_white",
    height=600,
)

st.plotly_chart(fig, use_container_width=True)
