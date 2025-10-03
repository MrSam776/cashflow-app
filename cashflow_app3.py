# cashflow_app3.py
# Streamlit cashflow modeller - corrected and improved.
# - Accurate monthly compounding using nominal APR/12
# - Contribution timing (start/end)
# - Multiple withdrawals (monthly or lump sum)
# - Optional income/expense growth & inflation (displayed as real £)
# - JSON save/load (filename selectable) and CSV export
# - Yearly breakdown includes Yearly Deposits, Yearly Interest, Cumulative figures

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
from io import BytesIO

st.set_page_config(page_title="Cashflow & Compound Growth (Accurate)", layout="wide")
st.title("💰 Cashflow & Compound Growth (Accurate Monthly Model)")

# ---------------------
# Sidebar: first allow uploading a scenario BEFORE widgets are created
# ---------------------
st.sidebar.header("Load / Save scenarios")

uploaded = st.sidebar.file_uploader("Upload scenario JSON to use (optional)", type=["json"])
loaded_inputs = None
if uploaded is not None:
    try:
        loaded_inputs = json.loads(uploaded.getvalue().decode("utf-8"))
        st.sidebar.success("Scenario loaded — defaults updated below.")
    except Exception as e:
        st.sidebar.error("Failed to parse JSON: " + str(e))
        loaded_inputs = None

# Save-as filename (user can edit before pressing Save)
default_filename = "cashflow_scenario.json"
scenario_filename = st.sidebar.text_input("Filename for Save (e.g. myscenario.json)", value=default_filename)

# ---------------------
# Helper to get default values (prefer loaded_inputs when present)
# ---------------------
def d(key, default):
    if loaded_inputs and key in loaded_inputs:
        return loaded_inputs[key]
    return default

# ---------------------
# Core inputs (use loaded defaults if file uploaded)
# ---------------------
st.sidebar.markdown("---")
st.sidebar.header("Core inputs")
initial_investment = st.sidebar.number_input("Initial investment (£)", min_value=0.0, value=float(d("initial_investment", 0.0)), step=100.0)
monthly_income = st.sidebar.number_input("Monthly income (£)", min_value=0.0, value=float(d("monthly_income", 0.0)), step=50.0)
monthly_expenses = st.sidebar.number_input("Monthly expenses (£)", min_value=0.0, value=float(d("monthly_expenses", 0.0)), step=50.0)
annual_growth_rate = st.sidebar.number_input("Annual growth rate (%)", value=float(d("annual_growth_rate", 6.0)), step=0.01)
projection_years = st.sidebar.number_input("Projection years", min_value=1, max_value=100, value=int(d("projection_years", 30)))

# Contribution toggle and inputs (optional)
st.sidebar.markdown("---")
use_contributions = st.sidebar.checkbox("Enable monthly contributions?", value=bool(d("use_contributions", True)))
monthly_contribution = 0.0
contribution_timing = "Start of Month"
if use_contributions:
    monthly_contribution = st.sidebar.number_input("Monthly contribution (£)", min_value=0.0, value=float(d("monthly_contribution", 800.0)), step=10.0)
    contribution_timing = st.sidebar.selectbox("Contribution timing", options=["Start of Month", "End of Month"],
                                               index=0 if d("contribution_timing", "Start of Month").startswith("Start") else 1)

# Withdrawals: allow multiple entries
st.sidebar.markdown("---")
use_withdrawals = st.sidebar.checkbox("Enable withdrawals (multiple)?", value=bool(d("use_withdrawals", False)))
withdrawals = []
if use_withdrawals:
    # how many entries
    num_w = st.sidebar.number_input("Number of withdrawal entries", min_value=1, max_value=20, value=int(d("num_withdrawals", 1)))
    for i in range(int(num_w)):
        st.sidebar.markdown(f"Withdrawal #{i+1}")
        wtype = st.sidebar.selectbox(f"Type (#{i+1})", ["Monthly", "Lump Sum"], key=f"wtype_{i}", index=0)
        wamount = st.sidebar.number_input(f"Amount (£) (#{i+1})", min_value=0.0, value=float(d("withdrawals", [{}]*int(num_w))[i].get("amount", 0.0) if loaded_inputs and "withdrawals" in loaded_inputs and i < len(loaded_inputs["withdrawals"]) else 0.0), key=f"wamt_{i}", step=50.0)
        wstart = st.sidebar.number_input(f"Start year (#{i+1})", min_value=1, max_value=int(projection_years), value=int(d("withdrawals", [{}]*int(num_w))[i].get("start_year", 1) if loaded_inputs and "withdrawals" in loaded_inputs and i < len(loaded_inputs["withdrawals"]) else 1), key=f"wstart_{i}")
        withdrawals.append({"type": wtype, "amount": float(wamount), "start_year": int(wstart)})

# Inflation toggle
st.sidebar.markdown("---")
use_inflation = st.sidebar.checkbox("Show real values (inflation-adjusted)?", value=bool(d("use_inflation", False)))
annual_inflation = 0.0
if use_inflation:
    annual_inflation = st.sidebar.number_input("Annual inflation rate (%)", min_value=0.0, value=float(d("annual_inflation", 2.0)), step=0.01)

# Income / expenses growth toggles
st.sidebar.markdown("---")
use_income_growth = st.sidebar.checkbox("Apply income growth?", value=bool(d("use_income_growth", False)))
income_growth_rate = 0.0
if use_income_growth:
    income_growth_rate = st.sidebar.number_input("Annual income growth (%)", min_value=0.0, value=float(d("income_growth_rate", 0.0)), step=0.01)

use_expenses_growth = st.sidebar.checkbox("Apply expenses growth?", value=bool(d("use_expenses_growth", False)))
expenses_growth_rate = 0.0
if use_expenses_growth:
    expenses_growth_rate = st.sidebar.number_input("Annual expenses growth (%)", min_value=0.0, value=float(d("expenses_growth_rate", 0.0)), step=0.01)

# ---------------------
# Save scenario button (download using user-chosen filename)
# ---------------------
st.sidebar.markdown("---")
scenario_dict = {
    "initial_investment": initial_investment,
    "monthly_income": monthly_income,
    "monthly_expenses": monthly_expenses,
    "annual_growth_rate": annual_growth_rate,
    "projection_years": projection_years,
    "use_contributions": use_contributions,
    "monthly_contribution": monthly_contribution,
    "contribution_timing": contribution_timing,
    "use_withdrawals": use_withdrawals,
    "withdrawals": withdrawals,
    "use_inflation": use_inflation,
    "annual_inflation": annual_inflation,
    "use_income_growth": use_income_growth,
    "income_growth_rate": income_growth_rate,
    "use_expenses_growth": use_expenses_growth,
    "expenses_growth_rate": expenses_growth_rate,
}
scenario_json = json.dumps(scenario_dict, indent=2)
st.sidebar.download_button(label="💾 Save scenario (download JSON)", data=scenario_json, file_name=scenario_filename, mime="application/json")

# ---------------------
# Core accurate monthly simulation
# ---------------------
def simulate_monthly_model(
    initial_investment,
    monthly_income,
    monthly_expenses,
    annual_growth_rate,
    projection_years,
    use_contributions,
    monthly_contribution,
    contribution_timing,
    withdrawals,
    use_inflation,
    annual_inflation,
    use_income_growth,
    income_growth_rate,
    use_expenses_growth,
    expenses_growth_rate
):
    """
    Accurate monthly model:
    - monthly rate uses nominal APR / 12 (monthly_rate = annual% / 12)
    - contribution timing: start = annuity-due, end = ordinary annuity
    - interest computed monthly after start-deposit if applicable
    - income/expenses applied at end of month
    - withdrawals applied at end of month (monthly recurring or lump sums)
    - returns a DataFrame with:
        Year, Yearly Deposits, Yearly Interest, Cumulative Deposits, Cumulative Interest, Yearly Withdrawals, End Balance (nominal), End Balance Real (if inflation)
    """
    months = int(projection_years) * 12
    balance = float(initial_investment)
    monthly_rate = float(annual_growth_rate) / 100.0 / 12.0   # IMPORTANT: nominal APR / 12
    cumulative_inflation = 1.0
    cum_deposits = 0.0
    cum_interest = 0.0

    rows = []
    # iterate year-by-year but process month loop inside to capture monthly compounding precisely
    for year in range(1, int(projection_years) + 1):
        year_interest = 0.0
        year_deposits = 0.0
        year_withdrawals = 0.0

        # monthly loop for this year
        for m in range(12):
            # contribution at start if configured
            if use_contributions and contribution_timing.startswith("Start"):
                balance += monthly_contribution
                year_deposits += monthly_contribution
                cum_deposits += monthly_contribution

            # monthly interest based on nominal APR/12
            interest = balance * monthly_rate
            balance += interest
            year_interest += interest
            cum_interest += interest

            # income and expenses applied at month-end (allowing annual growth year-by-year)
            monthly_income_val = monthly_income * ((1 + income_growth_rate/100.0) ** (year - 1)) if use_income_growth else monthly_income
            monthly_expenses_val = monthly_expenses * ((1 + expenses_growth_rate/100.0) ** (year - 1)) if use_expenses_growth else monthly_expenses
            balance += (monthly_income_val - monthly_expenses_val)

            # withdrawals (monthly or lump)
            if withdrawals:
                for w in withdrawals:
                    if w["type"] == "Monthly" and year >= int(w["start_year"]):
                        balance -= float(w["amount"])
                        year_withdrawals += float(w["amount"])
                    if w["type"] == "Lump Sum" and year == int(w["start_year"]) and m == 11:
                        # m == 11 -> last month of the year so we take the lump in that year
                        balance -= float(w["amount"])
                        year_withdrawals += float(w["amount"])

            # contribution at end if configured
            if use_contributions and contribution_timing.startswith("End"):
                balance += monthly_contribution
                year_deposits += monthly_contribution
                cum_deposits += monthly_contribution

        # end-of-year: update inflation factor and compute displayed values
        if use_inflation:
            cumulative_inflation *= (1.0 + float(annual_inflation) / 100.0)
        display_factor = cumulative_inflation if use_inflation else 1.0

        rows.append({
            "Year": year,
            "Yearly Deposits": round(year_deposits, 2),
            "Yearly Interest": round(year_interest, 2),
            "Cumulative Deposits": round(cum_deposits / display_factor, 2),
            "Cumulative Interest": round(cum_interest / display_factor, 2),
            "Yearly Withdrawals": round(year_withdrawals, 2),
            "End Balance (nominal)": round(balance, 2),
            "End Balance (real)": round(balance / display_factor, 2) if use_inflation else None
        })

    return pd.DataFrame(rows)

# ---------------------
# Run model with current inputs
# ---------------------
df = simulate_monthly_model(
    initial_investment=float(initial_investment),
    monthly_income=float(monthly_income),
    monthly_expenses=float(monthly_expenses),
    annual_growth_rate=float(annual_growth_rate),
    projection_years=int(projection_years),
    use_contributions=bool(use_contributions),
    monthly_contribution=float(monthly_contribution),
    contribution_timing=str(contribution_timing),
    withdrawals=withdrawals,
    use_inflation=bool(use_inflation),
    annual_inflation=float(annual_inflation) if use_inflation else 0.0,
    use_income_growth=bool(use_income_growth),
    income_growth_rate=float(income_growth_rate),
    use_expenses_growth=bool(use_expenses_growth),
    expenses_growth_rate=float(expenses_growth_rate)
)

# ---------------------
# Display results (table + plot)
# ---------------------
st.subheader("Projection (yearly)")
st.dataframe(df.fillna("N/A"), use_container_width=True)

# Prepare plot: yearly deposits + yearly interest stacked, yearly withdrawals as separate bars, overlay End Balance
fig = go.Figure()

# Stack deposits and interest as stacked bars for each year
fig.add_trace(go.Bar(x=df["Year"], y=df["Yearly Deposits"], name="Yearly Deposits", marker_color="#2a9d8f"))
fig.add_trace(go.Bar(x=df["Year"], y=df["Yearly Interest"], name="Yearly Interest", marker_color="#457b9d"))

# Withdrawals (show as bars with different color)
fig.add_trace(go.Bar(x=df["Year"], y=df["Yearly Withdrawals"], name="Yearly Withdrawals", marker_color="#e76f51"))

# End balance overlay (choose real or nominal for the line depending on inflation toggle)
end_balance_series = df["End Balance (real)"] if use_inflation else df["End Balance (nominal)"]
fig.add_trace(go.Scatter(x=df["Year"], y=end_balance_series, mode="lines+markers", name="End Balance", line=dict(color="black", width=3)))

fig.update_layout(barmode="stack", title="Yearly Contributions / Interest / Withdrawals (stacked) and End Balance", xaxis_title="Year", yaxis_title="£", template="plotly_white", height=600)
st.plotly_chart(fig, use_container_width=True)

# CSV export of the table
csv_bytes = df.to_csv(index=False).encode("utf-8")
st.download_button(label="Download results as CSV", data=csv_bytes, file_name="cashflow_results.csv", mime="text/csv")

# Quick modelling notes for user
st.markdown("**Notes**")
st.markdown("- Monthly nominal rate = Annual % / 12 (this matches standard compound interest calculators).")
st.markdown("- Contribution timing (start/end) follows annuity-due (start) or ordinary (end).")
st.markdown("- Interest calculated monthly; income & expenses applied at month-end; withdrawals applied at month-end.")
st.markdown("- If 'Show real values' is checked, displayed cumulative fields and end balance are divided by cumulative inflation to show purchasing-power EUR (real £).")

