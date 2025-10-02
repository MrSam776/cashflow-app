# cashflow_app3.py
# Streamlit cashflow modeller - corrected monthly simulation, multiple withdrawals,
# contribution timing (start/end), inflation-adjusted display, save/load JSON.
#
# Comments are included inline to explain logic and important modelling choices.

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
from io import BytesIO

st.set_page_config(page_title="Cashflow & Compound Growth (Corrected)", layout="wide")
st.title("💰 Cashflow & Compound Growth (Accurate Monthly Model)")

# -------------------------
# Helper: load defaults or session_state
# -------------------------
def _get_default(key, default):
    """Return from session_state if present otherwise default."""
    return st.session_state.get(key, default)

# -------------------------
# Sidebar: core inputs (always shown)
# Use 'key' arguments so we can programmatically set values on load.
# -------------------------
with st.sidebar:
    st.header("Core inputs (keep it simple)")

    st.number_input("Initial investment (£)", min_value=0.0, value= _get_default("initial_investment", 0.0),
                    step=100.0, key="initial_investment")
    st.number_input("Monthly income (£)", min_value=0.0, value= _get_default("monthly_income", 0.0),
                    step=50.0, key="monthly_income")
    st.number_input("Monthly expenses (£)", min_value=0.0, value= _get_default("monthly_expenses", 0.0),
                    step=50.0, key="monthly_expenses")
    st.number_input("Annual growth rate (%)", min_value= -50.0, value=_get_default("annual_growth_rate", 6.0),
                    step=0.1, key="annual_growth_rate")
    st.number_input("Projection years", min_value=1, max_value=100,
                    value=_get_default("projection_years", 30), step=1, key="projection_years")

    st.markdown("---")
    st.markdown("**Optional features (toggle to show inputs)**")

    # Contributions toggle
    st.checkbox("Enable monthly contributions", value=_get_default("use_contributions", True), key="use_contributions")
    if st.session_state["use_contributions"]:
        st.number_input("Monthly contribution (£)", min_value=0.0, value=_get_default("monthly_contribution", 800.0),
                        step=50.0, key="monthly_contribution")
        st.selectbox("Contribution timing", options=["Start of Month", "End of Month"],
                     index=0 if _get_default("contribution_timing","Start of Month").startswith("Start") else 1,
                     key="contribution_timing")

    # Withdrawals toggle: allow multiple entries
    st.checkbox("Enable withdrawals (multiple)", value=_get_default("use_withdrawals", False), key="use_withdrawals")
    withdrawals_list = []
    if st.session_state["use_withdrawals"]:
        st.markdown("**Define withdrawals** (add 1..n entries)")
        # number of entries
        num_w = st.number_input("Number of withdrawal entries", min_value=1, max_value=10,
                                value=_get_default("num_withdrawals", 1), key="num_withdrawals")
        # Create a list of withdrawals via dynamic keys
        for i in range(int(st.session_state["num_withdrawals"])):
            st.markdown(f"**Withdrawal #{i+1}**")
            wtype = st.selectbox(f"Type (#{i+1})", options=["Monthly", "Lump Sum"],
                                 key=f"w_type_{i}", index=0)
            wamount = st.number_input(f"Amount (£) (#{i+1})", min_value=0.0,
                                      value=_get_default(f"w_amount_{i}", 0.0), step=50.0, key=f"w_amount_{i}")
            wstart = st.number_input(f"Start year (#{i+1})", min_value=1,
                                     max_value=st.session_state["projection_years"],
                                     value=_get_default(f"w_start_{i}", 1), step=1, key=f"w_start_{i}")
            withdrawals_list.append({"type": wtype, "amount": float(wamount), "start_year": int(wstart)})

    # Inflation (optional)
    st.checkbox("Include inflation (adjust display to real £)", value=_get_default("use_inflation", False), key="use_inflation")
    if st.session_state["use_inflation"]:
        st.number_input("Annual inflation rate (%)", min_value=0.0, value=_get_default("annual_inflation", 2.0),
                        step=0.1, key="annual_inflation")

    # Income growth (optional)
    st.checkbox("Income growth (optional)", value=_get_default("use_income_growth", False), key="use_income_growth")
    if st.session_state["use_income_growth"]:
        st.number_input("Annual income growth (%)", min_value=0.0, value=_get_default("income_growth_rate", 0.0),
                        step=0.1, key="income_growth_rate")

    # Expenses growth (optional)
    st.checkbox("Expenses growth (optional)", value=_get_default("use_expenses_growth", False), key="use_expenses_growth")
    if st.session_state["use_expenses_growth"]:
        st.number_input("Annual expenses growth (%)", min_value=0.0, value=_get_default("expenses_growth_rate", 0.0),
                        step=0.1, key="expenses_growth_rate")

    st.markdown("---")
    # Save / Load UI (download/upload JSON)
    st.subheader("Save / load scenario")
    # Build current scenario dict for saving
    def build_scenario_from_state():
        sc = {
            "initial_investment": float(st.session_state["initial_investment"]),
            "monthly_income": float(st.session_state["monthly_income"]),
            "monthly_expenses": float(st.session_state["monthly_expenses"]),
            "annual_growth_rate": float(st.session_state["annual_growth_rate"]),
            "projection_years": int(st.session_state["projection_years"]),
            "use_contributions": bool(st.session_state.get("use_contributions", False)),
            "monthly_contribution": float(st.session_state.get("monthly_contribution", 0.0)),
            "contribution_timing": st.session_state.get("contribution_timing", "Start of Month"),
            "use_withdrawals": bool(st.session_state.get("use_withdrawals", False)),
            "withdrawals": withdrawals_list,
            "use_inflation": bool(st.session_state.get("use_inflation", False)),
            "annual_inflation": float(st.session_state.get("annual_inflation", 0.0)),
            "use_income_growth": bool(st.session_state.get("use_income_growth", False)),
            "income_growth_rate": float(st.session_state.get("income_growth_rate", 0.0)),
            "use_expenses_growth": bool(st.session_state.get("use_expenses_growth", False)),
            "expenses_growth_rate": float(st.session_state.get("expenses_growth_rate", 0.0)),
        }
        return sc

    scenario_json = json.dumps(build_scenario_from_state(), indent=2)
    st.download_button(label="💾 Download current scenario (JSON)", data=scenario_json,
                       file_name="cashflow_scenario.json", mime="application/json")

    uploaded = st.file_uploader("Upload scenario JSON to load (choose file)", type=["json"])
    if uploaded is not None:
        # Load and write into session_state, then rerun to populate widgets
        try:
            loaded = json.load(uploaded)
            # set only keys we expect (defensive)
            for k, v in loaded.items():
                # map keys to session state names used above
                if k in ["initial_investment","monthly_income","monthly_expenses","annual_growth_rate",
                         "projection_years","monthly_contribution","contribution_timing","use_inflation",
                         "annual_inflation","use_contributions","use_withdrawals","use_income_growth",
                         "income_growth_rate","use_expenses_growth","expenses_growth_rate"]:
                    st.session_state[k] = v
            # special: withdrawals
            if "withdrawals" in loaded:
                # clear previous keys for withdrawal count & entries
                st.session_state["num_withdrawals"] = len(loaded["withdrawals"])
                for i, w in enumerate(loaded["withdrawals"]):
                    st.session_state[f"w_type_{i}"] = w.get("type","Monthly")
                    st.session_state[f"w_amount_{i}"] = w.get("amount",0.0)
                    st.session_state[f"w_start_{i}"] = w.get("start_year",1)
            st.experimental_rerun()
        except Exception as e:
            st.error("Failed to load scenario: " + str(e))


# -------------------------
# Core monthly-simulation function (reference-correct)
# This is the accurate monthly-step model used for all outputs.
# -------------------------
def simulate_monthly(
    initial_investment: float,
    monthly_income: float,
    monthly_expenses: float,
    annual_growth_rate: float,
    projection_years: int,
    use_contributions: bool,
    monthly_contribution: float,
    contribution_timing: str,  # "Start of Month" or "End of Month"
    withdrawals: list,
    use_inflation: bool,
    annual_inflation: float,
    use_income_growth: bool,
    income_growth_rate: float,
    use_expenses_growth: bool,
    expenses_growth_rate: float
):
    """
    Monthly simulation with precise ordering:
      - If contribution timing = Start: add contribution at start of month (annuity-due)
      - Compute monthly interest on current balance
      - Add interest
      - Apply income - expenses (monthly, with annual growth applied at year boundaries)
      - Apply withdrawals (monthly or lump sum) at month end
      - If contribution timing = End: add contribution at month end
    Returns a DataFrame with yearly rows and inflation-adjusted display if requested.
    """
    months = int(projection_years) * 12
    balance = float(initial_investment)
    cum_deposits = 0.0
    cum_interest = 0.0
    records = []
    monthly_rate = (1.0 + float(annual_growth_rate)/100.0) ** (1.0/12.0) - 1.0
    cumulative_inflation = 1.0

    for month in range(1, months+1):
        year = (month-1) // 12 + 1

        # compute monthly income/expenses with annual growth applied year-on-year
        monthly_income_val = float(monthly_income) * ((1.0 + float(income_growth_rate)/100.0) ** (year-1)) if use_income_growth else float(monthly_income)
        monthly_expenses_val = float(monthly_expenses) * ((1.0 + float(expenses_growth_rate)/100.0) ** (year-1)) if use_expenses_growth else float(monthly_expenses)

        # contribution at start-of-month
        if use_contributions and contribution_timing == "Start of Month":
            balance += monthly_contribution
            cum_deposits += monthly_contribution

        # monthly interest on current balance
        interest = balance * monthly_rate
        balance += interest
        cum_interest += interest

        # apply income & expenses at end of month (net)
        balance += (monthly_income_val - monthly_expenses_val)

        # apply withdrawals (monthly or lump sum) at end-of-month
        if withdrawals:
            for w in withdrawals:
                # monthly recurring withdrawals (start year inclusive)
                if w["type"] == "Monthly" and year >= int(w["start_year"]):
                    balance -= float(w["amount"])
                # lump sum: trigger on the exact month that equals start_year * 12
                if w["type"] == "Lump Sum" and month == int(w["start_year"]) * 12:
                    balance -= float(w["amount"])

        # contribution at end-of-month
        if use_contributions and contribution_timing == "End of Month":
            balance += monthly_contribution
            cum_deposits += monthly_contribution

        # end of year: record aggregated values
        if month % 12 == 0:
            # compute year totals for display
            # yearly income and expenses are last computed monthly values *12
            yearly_income = monthly_income_val * 12.0
            yearly_expenses = monthly_expenses_val * 12.0
            # total withdrawals in that year (sum of monthly recurring + any lump sums in that year)
            total_withdrawals = 0.0
            if withdrawals:
                for w in withdrawals:
                    if w["type"] == "Monthly" and year >= int(w["start_year"]):
                        total_withdrawals += float(w["amount"]) * 12.0
                    if w["type"] == "Lump Sum" and year == int(w["start_year"]):
                        total_withdrawals += float(w["amount"])

            # update cumulative inflation factor (we report real values dividing by this factor)
            if use_inflation:
                cumulative_inflation *= (1.0 + float(annual_inflation)/100.0)
            factor = cumulative_inflation if use_inflation else 1.0

            records.append({
                "Year": year,
                "Income": round(yearly_income / factor, 2),
                "Expenses": round(yearly_expenses / factor, 2),
                "Contributions": round(cum_deposits / factor, 2),
                "Withdrawals": round(total_withdrawals / factor, 2),
                "End Balance": round(balance / factor, 2)
            })

    return pd.DataFrame(records)

# -------------------------
# Gather current inputs (from session_state)
# -------------------------
inputs = {
    "initial_investment": float(st.session_state.get("initial_investment", 0.0)),
    "monthly_income": float(st.session_state.get("monthly_income", 0.0)),
    "monthly_expenses": float(st.session_state.get("monthly_expenses", 0.0)),
    "annual_growth_rate": float(st.session_state.get("annual_growth_rate", 6.0)),
    "projection_years": int(st.session_state.get("projection_years", 30)),
    "use_contributions": bool(st.session_state.get("use_contributions", False)),
    "monthly_contribution": float(st.session_state.get("monthly_contribution", 0.0)),
    "contribution_timing": st.session_state.get("contribution_timing", "Start of Month"),
    "withdrawals": withdrawals_list if st.session_state.get("use_withdrawals", False) else [],
    "use_inflation": bool(st.session_state.get("use_inflation", False)),
    "annual_inflation": float(st.session_state.get("annual_inflation", 0.0)),
    "use_income_growth": bool(st.session_state.get("use_income_growth", False)),
    "income_growth_rate": float(st.session_state.get("income_growth_rate", 0.0)),
    "use_expenses_growth": bool(st.session_state.get("use_expenses_growth", False)),
    "expenses_growth_rate": float(st.session_state.get("expenses_growth_rate", 0.0)),
}

# -------------------------
# Run the simulation (correct monthly model)
# -------------------------
df = simulate_monthly(**inputs)

# -------------------------
# Display results
# -------------------------
st.subheader("Projection table (yearly)")
st.dataframe(df, use_container_width=True)

# Stacked area + line: contributions vs growth vs withdrawals/expenses (we show stacked bars + line)
fig = go.Figure()

# Stacked bars: Contributions, Interest (we only have cumulative contributions and cumulative interest not broken out yearly interest here)
# For simplicity and clarity we will stack Income/Expenses/Contributions/Withdrawals as bars and overlay End Balance.
# (If you prefer an area decomposition of contribution vs growth we can compute yearly interest separately.)
fig.add_trace(go.Bar(x=df["Year"], y=df["Contributions"], name="Contributions", marker=dict(color="#2a9d8f")))
fig.add_trace(go.Bar(x=df["Year"], y=df["Income"], name="Income", marker=dict(color="#457b9d")))
fig.add_trace(go.Bar(x=df["Year"], y=df["Expenses"], name="Expenses", marker=dict(color="#e76f51")))
fig.add_trace(go.Bar(x=df["Year"], y=df["Withdrawals"], name="Withdrawals", marker=dict(color="#f4a261")))

# Net balance line
fig.add_trace(go.Scatter(x=df["Year"], y=df["End Balance"], mode="lines+markers", name="End Balance",
                         line=dict(color="black", width=3)))

fig.update_layout(title="Cashflow Projection (yearly stacked)",
                  xaxis_title="Year", yaxis_title="£",
                  barmode="stack", template="plotly_white", height=620)
st.plotly_chart(fig, use_container_width=True)

st.markdown("**Notes on modelling decisions (short)**:")
st.markdown("""
- Monthly contributions can be set to occur at the **start** (annuity-due) or **end** (ordinary annuity) of each month.
- Interest is computed monthly (monthly compounding).
- Income and expenses are applied at **month-end** in this model.
- Withdrawals can be multiple: monthly recurring (starting in a given year) or one-off lump sums (triggered in a particular year).
- If 'Include inflation' is checked the displayed numbers are **inflation-adjusted (real £)** using the provided inflation rate; the model computes monthly interest on nominal balances but divides displayed results by cumulative inflation for clarity.
""")
