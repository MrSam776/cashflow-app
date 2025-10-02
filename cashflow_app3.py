import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# -----------------------------
# Streamlit App Title
# -----------------------------
st.title("Cashflow & Compound Growth Model")

# -----------------------------
# Core Inputs (always visible)
# -----------------------------
st.header("Core Inputs")

initial_investment = st.number_input("Initial Investment (£)", min_value=0.0, value=0.0, step=100.0)
monthly_income = st.number_input("Monthly Income (£)", min_value=0.0, value=0.0, step=100.0)
monthly_expenses = st.number_input("Monthly Expenses (£)", min_value=0.0, value=0.0, step=100.0)
annual_growth_rate = st.number_input("Annual Growth Rate (%)", min_value=0.0, value=6.0, step=0.1) / 100

projection_years = st.number_input("Projection Period (years)", min_value=1, value=30, step=1)

# -----------------------------
# Optional Toggles
# -----------------------------

# Contributions toggle
use_contributions = st.checkbox("Add Monthly Contributions?")
if use_contributions:
    monthly_contribution = st.number_input("Monthly Contribution (£)", min_value=0.0, value=0.0, step=100.0)
    contribution_timing = st.selectbox("Contribution Timing", ["Start of Month", "End of Month"])
else:
    monthly_contribution = 0.0
    contribution_timing = "End of Month"

# Withdrawals toggle (multiple entries allowed)
use_withdrawals = st.checkbox("Add Withdrawals?")
withdrawals = []
if use_withdrawals:
    st.markdown("### Withdrawal Entries")
    num_withdrawals = st.number_input("Number of Withdrawals", min_value=1, value=1, step=1)

    for i in range(num_withdrawals):
        st.markdown(f"**Withdrawal {i+1}**")
        withdrawal_type = st.radio(f"Type (Withdrawal {i+1})", ["Monthly", "Lump Sum"], key=f"type_{i}")
        withdrawal_amount = st.number_input(f"Amount (£) for Withdrawal {i+1}", min_value=0.0, value=0.0, step=100.0, key=f"amt_{i}")
        withdrawal_start_year = st.number_input(f"Start Year for Withdrawal {i+1}", min_value=1, max_value=projection_years, value=5, key=f"year_{i}")

        withdrawals.append({
            "type": withdrawal_type,
            "amount": withdrawal_amount,
            "start_year": withdrawal_start_year
        })

# Inflation toggle
use_inflation = st.checkbox("Include Inflation?")
if use_inflation:
    annual_inflation = st.number_input("Annual Inflation Rate (%)", min_value=0.0, value=2.0, step=0.1) / 100
else:
    annual_inflation = 0.0

# Income growth toggle
use_income_growth = st.checkbox("Add Income Growth?")
if use_income_growth:
    income_growth_rate = st.number_input("Annual Income Growth Rate (%)", min_value=0.0, value=2.0, step=0.1) / 100
else:
    income_growth_rate = 0.0

# Expenses growth toggle
use_expenses_growth = st.checkbox("Add Expenses Growth?")
if use_expenses_growth:
    expenses_growth_rate = st.number_input("Annual Expenses Growth Rate (%)", min_value=0.0, value=2.0, step=0.1) / 100
else:
    expenses_growth_rate = 0.0

# -----------------------------
# Calculation Logic
# -----------------------------

months = projection_years * 12
balance = initial_investment
records = []

monthly_growth_rate = (1 + annual_growth_rate) ** (1/12) - 1
monthly_inflation_rate = (1 + annual_inflation) ** (1/12) - 1

for month in range(1, months + 1):
    year = (month - 1) // 12 + 1

    # Apply income and expenses (with growth)
    income = monthly_income * ((1 + income_growth_rate) ** (year - 1))
    expenses = monthly_expenses * ((1 + expenses_growth_rate) ** (year - 1))

    net_flow = income - expenses

    # Apply contributions
    if contribution_timing == "Start of Month":
        balance += monthly_contribution
    balance += net_flow

    # Apply withdrawals if conditions met
    if use_withdrawals:
        for w in withdrawals:
            if year >= w["start_year"]:
                if w["type"] == "Monthly":
                    balance -= w["amount"]
                elif w["type"] == "Lump Sum" and month == (w["start_year"] * 12):
                    balance -= w["amount"]

    # Apply growth
    balance *= (1 + monthly_growth_rate)

    # If contributions at end of month
    if contribution_timing == "End of Month":
        balance += monthly_contribution

    # Record end of each year
    if month % 12 == 0:
        total_withdrawals = 0
        if use_withdrawals:
            for w in withdrawals:
                if w["type"] == "Monthly" and year >= w["start_year"]:
                    total_withdrawals += w["amount"] * 12
                elif w["type"] == "Lump Sum" and year == w["start_year"]:
                    total_withdrawals += w["amount"]

        records.append({
            "Year": year,
            "Income": round(income * 12, 2),
            "Expenses": round(expenses * 12, 2),
            "Contributions": round(monthly_contribution * 12, 2) if use_contributions else 0,
            "Withdrawals": round(total_withdrawals, 2),
            "End Balance": round(balance, 2)
        })

# -----------------------------
# Results Table
# -----------------------------
df = pd.DataFrame(records)
st.subheader("Projection Table")
st.dataframe(df)

# -----------------------------
# Chart
# -----------------------------
fig = go.Figure()

fig.add_trace(go.Scatter(
    x=df["Year"], y=df["End Balance"], mode="lines+markers", name="End Balance"
))

fig.add_trace(go.Bar(
    x=df["Year"], y=df["Income"], name="Income"
))
fig.add_trace(go.Bar(
    x=df["Year"], y=df["Expenses"], name="Expenses"
))
if use_contributions:
    fig.add_trace(go.Bar(
        x=df["Year"], y=df["Contributions"], name="Contributions"
    ))
if use_withdrawals:
    fig.add_trace(go.Bar(
        x=df["Year"], y=df["Withdrawals"], name="Withdrawals"
    ))

fig.update_layout(
    barmode="stack",
    title="Cashflow Projection",
    xaxis_title="Year",
    yaxis_title="£ Value"
)

st.plotly_chart(fig, use_container_width=True)
