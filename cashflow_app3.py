# cashflow_app3.py
# Streamlit Cashflow modeller - Save/Load/Reset fixes, no experimental_rerun dependency.
# Accurate monthly model retained (nominal APR/12, contribution timing, multiple withdrawals).

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json

st.set_page_config(page_title="Cashflow Modeller (Save/Load stable)", layout="wide")
st.title("💷 Cashflow Modeller — Save/Load & Reset (stable)")

# ---------------------
# DEFAULTS (single source)
# ---------------------
DEFAULTS = {
    "initial_investment": 0.0,
    "monthly_income": 0.0,
    "monthly_expenses": 0.0,
    "annual_growth_rate": 6.0,
    "projection_years": 30,
    "use_contributions": False,
    "monthly_contribution": 0.0,
    "contribution_timing": "Start of Month",
    "use_withdrawals": False,
    "num_withdrawals": 0,
    "withdrawals": [],
    "use_inflation": False,
    "annual_inflation": 2.0,
    "use_income_growth": False,
    "income_growth_rate": 0.0,
    "use_expenses_growth": False,
    "expenses_growth_rate": 0.0
}

# ---------------------
# Upload (before widgets if possible)
# ---------------------
st.sidebar.header("Scenario — Upload / Save / Reset")

uploaded = st.sidebar.file_uploader("Upload scenario JSON (optional)", type=["json"])
uploaded_parsed = None
if uploaded is not None:
    try:
        uploaded_parsed = json.loads(uploaded.getvalue().decode("utf-8"))
        st.sidebar.success("Scenario parsed. Click 'Apply uploaded scenario' below to replace inputs.")
    except Exception as e:
        st.sidebar.error("Failed to parse uploaded JSON: " + str(e))
        uploaded_parsed = None

# Save-as name (user types scenario name, we append .json automatically)
save_name = st.sidebar.text_input("Scenario name (no extension)", value="my_scenario")

# ---------------------
# Function: set default session_state keys (do not delete keys on reset)
# ---------------------
def ensure_session_defaults():
    for k, v in DEFAULTS.items():
        if k not in st.session_state:
            st.session_state[k] = v
    # ensure per-withdrawal keys exist if num_withdrawals > 0
    n = int(st.session_state.get("num_withdrawals", 0))
    for i in range(n):
        if f"w_type_{i}" not in st.session_state:
            st.session_state[f"w_type_{i}"] = "Monthly"
        if f"w_amount_{i}" not in st.session_state:
            st.session_state[f"w_amount_{i}"] = 0.0
        if f"w_start_{i}" not in st.session_state:
            st.session_state[f"w_start_{i}"] = 1

ensure_session_defaults()

# ---------------------
# "Apply uploaded scenario" button (safe method to overwrite current inputs)
# ---------------------
if uploaded_parsed is not None:
    if st.sidebar.button("Apply uploaded scenario"):
        # Map allowed keys into session_state (defensive)
        for k, v in uploaded_parsed.items():
            if k == "withdrawals":
                # set withdrawal list and count, and per-entry defaults
                st.session_state["withdrawals"] = v
                st.session_state["num_withdrawals"] = len(v)
                for i, w in enumerate(v):
                    st.session_state[f"w_type_{i}"] = w.get("type", "Monthly")
                    st.session_state[f"w_amount_{i}"] = float(w.get("amount", 0.0))
                    st.session_state[f"w_start_{i}"] = int(w.get("start_year", 1))
            elif k in DEFAULTS:
                st.session_state[k] = v
        st.sidebar.success("Uploaded scenario applied to inputs. (Widgets updated.)")

# ---------------------
# Save / Download scenario JSON (append .json automatically)
# ---------------------
def build_scenario_dict():
    # collect withdrawal entries from session_state
    n = int(st.session_state.get("num_withdrawals", 0))
    ws = []
    for i in range(n):
        ws.append({
            "type": st.session_state.get(f"w_type_{i}", "Monthly"),
            "amount": float(st.session_state.get(f"w_amount_{i}", 0.0)),
            "start_year": int(st.session_state.get(f"w_start_{i}", 1))
        })
    sc = {
        "initial_investment": float(st.session_state.get("initial_investment", DEFAULTS["initial_investment"])),
        "monthly_income": float(st.session_state.get("monthly_income", DEFAULTS["monthly_income"])),
        "monthly_expenses": float(st.session_state.get("monthly_expenses", DEFAULTS["monthly_expenses"])),
        "annual_growth_rate": float(st.session_state.get("annual_growth_rate", DEFAULTS["annual_growth_rate"])),
        "projection_years": int(st.session_state.get("projection_years", DEFAULTS["projection_years"])),
        "use_contributions": bool(st.session_state.get("use_contributions", DEFAULTS["use_contributions"])),
        "monthly_contribution": float(st.session_state.get("monthly_contribution", DEFAULTS["monthly_contribution"])),
        "contribution_timing": st.session_state.get("contribution_timing", DEFAULTS["contribution_timing"]),
        "use_withdrawals": bool(st.session_state.get("use_withdrawals", DEFAULTS["use_withdrawals"])),
        "num_withdrawals": n,
        "withdrawals": ws,
        "use_inflation": bool(st.session_state.get("use_inflation", DEFAULTS["use_inflation"])),
        "annual_inflation": float(st.session_state.get("annual_inflation", DEFAULTS["annual_inflation"])),
        "use_income_growth": bool(st.session_state.get("use_income_growth", DEFAULTS["use_income_growth"])),
        "income_growth_rate": float(st.session_state.get("income_growth_rate", DEFAULTS["income_growth_rate"])),
        "use_expenses_growth": bool(st.session_state.get("use_expenses_growth", DEFAULTS["use_expenses_growth"])),
        "expenses_growth_rate": float(st.session_state.get("expenses_growth_rate", DEFAULTS["expenses_growth_rate"]))
    }
    return sc

scenario_json = json.dumps(build_scenario_dict(), indent=2)
filename = (save_name.strip() or "scenario") + ".json"
st.sidebar.download_button(label="💾 Save scenario (.json) — browser will prompt", data=scenario_json, file_name=filename, mime="application/json")

# ---------------------
# Reset to defaults (safe: write defaults, do not delete keys)
# ---------------------
if st.sidebar.button("🔄 Reset to defaults (safe)"):
    for k, v in DEFAULTS.items():
        st.session_state[k] = v
    # reset per-withdrawal entries
    st.session_state["num_withdrawals"] = DEFAULTS["num_withdrawals"]
    # write default per-withdrawal keys to avoid missing widget keys
    for i in range(0, 20):
        st.session_state[f"w_type_{i}"] = "Monthly"
        st.session_state[f"w_amount_{i}"] = 0.0
        st.session_state[f"w_start_{i}"] = 1
    st.sidebar.success("Reset applied. (Defaults restored)")

# ---------------------
# Now create widgets (they read values from session_state)
# ---------------------
st.sidebar.header("Inputs (Core & Advanced)")

st.sidebar.number_input("Initial investment (£)", min_value=0.0, step=100.0, key="initial_investment")
st.sidebar.number_input("Monthly income (£)", min_value=0.0, step=50.0, key="monthly_income")
st.sidebar.number_input("Monthly expenses (£)", min_value=0.0, step=50.0, key="monthly_expenses")
st.sidebar.number_input("Annual growth rate (%)", step=0.01, key="annual_growth_rate")
st.sidebar.number_input("Projection years", min_value=1, max_value=100, step=1, key="projection_years")

with st.sidebar.expander("Contributions (advanced)", expanded=False):
    st.checkbox("Enable monthly contributions", key="use_contributions")
    if st.session_state.get("use_contributions", False):
        st.number_input("Monthly contribution (£)", min_value=0.0, step=10.0, key="monthly_contribution")
        st.selectbox("Contribution timing", options=["Start of Month", "End of Month"], key="contribution_timing")

with st.sidebar.expander("Withdrawals (advanced)", expanded=False):
    st.checkbox("Enable withdrawals", key="use_withdrawals")
    if st.session_state.get("use_withdrawals", False):
        st.number_input("Number of withdrawal entries", min_value=1, max_value=20, step=1, key="num_withdrawals")
        n_w = int(st.session_state.get("num_withdrawals", 0))
        for i in range(n_w):
            st.markdown(f"**Withdrawal #{i+1}**")
            st.selectbox(f"Type (#{i+1})", ["Monthly", "Lump Sum"], key=f"w_type_{i}")
            st.number_input(f"Amount (£) (#{i+1})", min_value=0.0, step=50.0, key=f"w_amount_{i}")
            st.number_input(f"Start year (#{i+1})", min_value=1, max_value=int(st.session_state.get("projection_years", 30)), step=1, key=f"w_start_{i}")

with st.sidebar.expander("Inflation & Growth (advanced)", expanded=False):
    st.checkbox("Show real values (inflation-adjusted)", key="use_inflation")
    if st.session_state.get("use_inflation", False):
        st.number_input("Annual inflation rate (%)", min_value=0.0, step=0.01, key="annual_inflation")
    st.checkbox("Income growth (advanced)", key="use_income_growth")
    if st.session_state.get("use_income_growth", False):
        st.number_input("Annual income growth (%)", min_value=0.0, step=0.01, key="income_growth_rate")
    st.checkbox("Expenses growth (advanced)", key="use_expenses_growth")
    if st.session_state.get("use_expenses_growth", False):
        st.number_input("Annual expenses growth (%)", min_value=0.0, step=0.01, key="expenses_growth_rate")

# ---------------------
# Build withdrawals list from session_state
# ---------------------
withdrawals = []
if st.session_state.get("use_withdrawals", False):
    n_w = int(st.session_state.get("num_withdrawals", 0))
    for i in range(n_w):
        withdrawals.append({
            "type": st.session_state.get(f"w_type_{i}", "Monthly"),
            "amount": float(st.session_state.get(f"w_amount_{i}", 0.0)),
            "start_year": int(st.session_state.get(f"w_start_{i}", 1))
        })

# ---------------------
# Accurate monthly simulator (nominal APR/12)
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
    months = int(projection_years) * 12
    balance = float(initial_investment)
    monthly_rate = float(annual_growth_rate) / 100.0 / 12.0   # nominal APR / 12
    cumulative_inflation = 1.0
    cum_deposits = 0.0
    cum_interest = 0.0

    rows = []
    for year in range(1, int(projection_years) + 1):
        year_interest = 0.0
        year_deposits = 0.0
        year_withdrawals = 0.0
        for m in range(12):
            if use_contributions and contribution_timing.startswith("Start"):
                balance += monthly_contribution
                year_deposits += monthly_contribution
                cum_deposits += monthly_contribution
            interest = balance * monthly_rate
            balance += interest
            year_interest += interest
            cum_interest += interest
            monthly_income_val = monthly_income * ((1 + income_growth_rate/100.0) ** (year - 1)) if use_income_growth else monthly_income
            monthly_expenses_val = monthly_expenses * ((1 + expenses_growth_rate/100.0) ** (year - 1)) if use_expenses_growth else monthly_expenses
            balance += (monthly_income_val - monthly_expenses_val)
            if withdrawals:
                for w in withdrawals:
                    if w["type"] == "Monthly" and year >= int(w["start_year"]):
                        balance -= float(w["amount"])
                        year_withdrawals += float(w["amount"])
                    if w["type"] == "Lump Sum" and year == int(w["start_year"]) and m == 11:
                        balance -= float(w["amount"])
                        year_withdrawals += float(w["amount"])
            if use_contributions and contribution_timing.startswith("End"):
                balance += monthly_contribution
                year_deposits += monthly_contribution
                cum_deposits += monthly_contribution
        if use_inflation:
            cumulative_inflation *= (1.0 + float(annual_inflation)/100.0)
        display_factor = cumulative_inflation if use_inflation else 1.0
        rows.append({
            "Year": year,
            "Yearly Deposits": round(year_deposits, 2),
            "Yearly Interest": round(year_interest, 2),
            "Cumulative Deposits (real)" if use_inflation else "Cumulative Deposits": round(cum_deposits / display_factor, 2),
            "Cumulative Interest (real)" if use_inflation else "Cumulative Interest": round(cum_interest / display_factor, 2),
            "Yearly Withdrawals": round(year_withdrawals, 2),
            "End Balance (nominal)": round(balance, 2),
            "End Balance (real)" if use_inflation else "End Balance (real)": (round(balance / display_factor, 2) if use_inflation else None)
        })
    df = pd.DataFrame(rows)
    if not use_inflation:
        df["End Balance (real)"] = None
    return df

# ---------------------
# Run the model
# ---------------------
df = simulate_monthly_model(
    initial_investment=float(st.session_state.get("initial_investment")),
    monthly_income=float(st.session_state.get("monthly_income")),
    monthly_expenses=float(st.session_state.get("monthly_expenses")),
    annual_growth_rate=float(st.session_state.get("annual_growth_rate")),
    projection_years=int(st.session_state.get("projection_years")),
    use_contributions=bool(st.session_state.get("use_contributions")),
    monthly_contribution=float(st.session_state.get("monthly_contribution")),
    contribution_timing=str(st.session_state.get("contribution_timing")),
    withdrawals=withdrawals,
    use_inflation=bool(st.session_state.get("use_inflation")),
    annual_inflation=float(st.session_state.get("annual_inflation", 0.0)),
    use_income_growth=bool(st.session_state.get("use_income_growth")),
    income_growth_rate=float(st.session_state.get("income_growth_rate", 0.0)),
    use_expenses_growth=bool(st.session_state.get("use_expenses_growth")),
    expenses_growth_rate=float(st.session_state.get("expenses_growth_rate", 0.0))
)

# ---------------------
# Output: table + chart + csv
# ---------------------
st.subheader("Projection table (yearly)")
st.dataframe(df.fillna("N/A"), use_container_width=True)

fig = go.Figure()
fig.add_trace(go.Bar(x=df["Year"], y=df["Yearly Deposits"], name="Yearly Deposits"))
fig.add_trace(go.Bar(x=df["Year"], y=df["Yearly Interest"], name="Yearly Interest"))
fig.add_trace(go.Bar(x=df["Year"], y=df["Yearly Withdrawals"], name="Yearly Withdrawals"))
end_series = df["End Balance (real)"] if st.session_state.get("use_inflation") else df["End Balance (nominal)"]
fig.add_trace(go.Scatter(x=df["Year"], y=end_series, mode="lines+markers", name="End Balance", line=dict(color="black", width=3)))
fig.update_layout(barmode="stack", title="Yearly deposits/interest/withdrawals (stacked) + End Balance", xaxis_title="Year", yaxis_title="£", template="plotly_white", height=640)
st.plotly_chart(fig, use_container_width=True)

csv_bytes = df.to_csv(index=False).encode("utf-8")
st.download_button("Download CSV", data=csv_bytes, file_name="cashflow_results.csv", mime="text/csv")

st.markdown("**Notes**: This model uses nominal APR/12 for monthly compounding. Contribution timing affects when monthly deposits are applied (start = annuity-due). Uploading a scenario will let you apply it to widgets; use Reset to restore defaults.")
