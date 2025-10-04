# cashflow_app3.py
# Personal Cashflow Modeller — Save/Load fixed, Save-as filename, Reset defaults, accurate monthly model.

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json

st.set_page_config(page_title="Cashflow Modeller (Save/Load fixed)", layout="wide")
st.title("💷 Cashflow Modeller — Save/Load & Reset fixes")

# -----------------------
# Defaults
# -----------------------
DEFAULTS = {
    "initial_investment": 0.0,
    "monthly_income": 0.0,
    "monthly_expenses": 0.0,
    "annual_growth_rate": 6.0,   # % APR
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
    "expenses_growth_rate": 0.0,
}

# -----------------------
# Sidebar: Upload first (so its values are applied BEFORE widget creation)
# -----------------------
st.sidebar.header("Scenario: Load / Save / Reset")

uploaded = st.sidebar.file_uploader("Upload scenario JSON (overwrites current inputs)", type=["json"])
# Keep track of last uploaded filename to avoid re-applying on every rerun
last_uploaded = st.session_state.get("_last_uploaded_name", None)
if uploaded is not None and uploaded.name != last_uploaded:
    try:
        parsed = json.loads(uploaded.getvalue().decode("utf-8"))
        # Map loaded keys into session_state BEFORE widgets created
        # Only set keys we expect (defensive)
        for k, v in parsed.items():
            if k == "withdrawals":
                # store withdrawals list and num_withdrawals
                st.session_state["withdrawals"] = v
                st.session_state["num_withdrawals"] = len(v)
                # populate template keys for each withdrawal entry
                for i, w in enumerate(v):
                    st.session_state[f"w_type_{i}"] = w.get("type", "Monthly")
                    st.session_state[f"w_amount_{i}"] = float(w.get("amount", 0.0))
                    st.session_state[f"w_start_{i}"] = int(w.get("start_year", 1))
            else:
                st.session_state[k] = v
        st.session_state["_last_uploaded_name"] = uploaded.name
        # force a rerun so widgets use the new session_state defaults
        st.experimental_rerun()
    except Exception as e:
        st.sidebar.error("Failed to load scenario JSON: " + str(e))

# Save-as filename input (no extension visible — extension appended automatically)
scenario_name_input = st.sidebar.text_input("Scenario name (no extension)", value="my_scenario")

# Download (save) button: auto-add .json to filename, browser prompts Save As
def build_scenario_dict():
    # build current scenario dict from session_state / defaults
    def get_state(k):
        return st.session_state.get(k, DEFAULTS.get(k))
    # collect withdrawals from session_state
    withdrawals_collect = []
    n_w = int(st.session_state.get("num_withdrawals", 0))
    for i in range(n_w):
        withdrawals_collect.append({
            "type": st.session_state.get(f"w_type_{i}", "Monthly"),
            "amount": float(st.session_state.get(f"w_amount_{i}", 0.0)),
            "start_year": int(st.session_state.get(f"w_start_{i}", 1))
        })
    scenario = {
        "initial_investment": float(get_state("initial_investment")),
        "monthly_income": float(get_state("monthly_income")),
        "monthly_expenses": float(get_state("monthly_expenses")),
        "annual_growth_rate": float(get_state("annual_growth_rate")),
        "projection_years": int(get_state("projection_years")),
        "use_contributions": bool(get_state("use_contributions")),
        "monthly_contribution": float(get_state("monthly_contribution")),
        "contribution_timing": get_state("contribution_timing"),
        "use_withdrawals": bool(get_state("use_withdrawals")),
        "num_withdrawals": n_w,
        "withdrawals": withdrawals_collect,
        "use_inflation": bool(get_state("use_inflation")),
        "annual_inflation": float(get_state("annual_inflation")),
        "use_income_growth": bool(get_state("use_income_growth")),
        "income_growth_rate": float(get_state("income_growth_rate")),
        "use_expenses_growth": bool(get_state("use_expenses_growth")),
        "expenses_growth_rate": float(get_state("expenses_growth_rate")),
    }
    return scenario

# Prepare JSON bytes for download - will be updated live
scenario_json = json.dumps(build_scenario_dict(), indent=2)
download_filename = (scenario_name_input.strip() or "cashflow_scenario") + ".json"
st.sidebar.download_button("💾 Save scenario (download .json)", data=scenario_json, file_name=download_filename, mime="application/json")

# Reset to defaults button
if st.sidebar.button("🔄 Reset to defaults (clear all)"):
    # clear session keys and set to defaults
    for k, v in DEFAULTS.items():
        st.session_state[k] = v
    # remove any dynamic withdrawal keys
    keys_to_remove = [k for k in list(st.session_state.keys()) if k.startswith("w_type_") or k.startswith("w_amount_") or k.startswith("w_start_")]
    for kk in keys_to_remove:
        del st.session_state[kk]
    st.session_state["_last_uploaded_name"] = None
    st.experimental_rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("Tip: upload a previously saved .json to replace inputs. Use Reset to start fresh.")

# -----------------------
# Initialize session_state defaults (only if not already set)
# This makes widgets use the values we have (either loaded or defaults).
# -----------------------
def init_state_if_missing():
    for k, v in DEFAULTS.items():
        if k not in st.session_state:
            st.session_state[k] = v
    # ensure withdrawal-related keys exist
    if "num_withdrawals" not in st.session_state:
        st.session_state["num_withdrawals"] = DEFAULTS["num_withdrawals"]
    n = int(st.session_state["num_withdrawals"])
    # ensure per-withdrawal keys exist with defaults
    for i in range(n):
        if f"w_type_{i}" not in st.session_state:
            st.session_state[f"w_type_{i}"] = "Monthly"
        if f"w_amount_{i}" not in st.session_state:
            st.session_state[f"w_amount_{i}"] = 0.0
        if f"w_start_{i}" not in st.session_state:
            st.session_state[f"w_start_{i}"] = 1

init_state_if_missing()

# -----------------------
# Sidebar: Now create widgets bound to session_state keys (they will reflect loaded or default values)
# -----------------------
st.sidebar.header("Inputs (Core & Advanced)")

st.sidebar.number_input("Initial investment (£)", min_value=0.0, step=100.0, key="initial_investment")
st.sidebar.number_input("Monthly income (£)", min_value=0.0, step=50.0, key="monthly_income")
st.sidebar.number_input("Monthly expenses (£)", min_value=0.0, step=50.0, key="monthly_expenses")
st.sidebar.number_input("Annual growth rate (%)", step=0.01, key="annual_growth_rate")
st.sidebar.number_input("Projection years", min_value=1, max_value=100, step=1, key="projection_years")

# Use expanders to keep UI tidy (closed by default)
with st.sidebar.expander("Contributions (advanced)", expanded=False):
    st.checkbox("Enable monthly contributions", key="use_contributions")
    if st.session_state.get("use_contributions", False):
        st.number_input("Monthly contribution (£)", min_value=0.0, step=10.0, key="monthly_contribution")
        st.selectbox("Contribution timing", options=["Start of Month", "End of Month"], key="contribution_timing")

with st.sidebar.expander("Withdrawals (advanced, multiple entries)", expanded=False):
    st.checkbox("Enable withdrawals", key="use_withdrawals")
    if st.session_state.get("use_withdrawals", False):
        st.number_input("Number of withdrawal entries", min_value=1, max_value=20, step=1, key="num_withdrawals")
        # Ensure per-withdrawal session keys exist for new count
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

# -----------------------
# Build withdrawals list from session_state
# -----------------------
withdrawals = []
if st.session_state.get("use_withdrawals", False):
    n_w = int(st.session_state.get("num_withdrawals", 0))
    for i in range(n_w):
        w = {
            "type": st.session_state.get(f"w_type_{i}", "Monthly"),
            "amount": float(st.session_state.get(f"w_amount_{i}", 0.0)),
            "start_year": int(st.session_state.get(f"w_start_{i}", 1))
        }
        withdrawals.append(w)

# -----------------------
# Accurate monthly simulator (nominal APR/12)
# -----------------------
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
    # simulate month-by-month but collect end-of-year aggregates
    for year in range(1, int(projection_years) + 1):
        year_interest = 0.0
        year_deposits = 0.0
        year_withdrawals = 0.0
        for m in range(12):
            # contribution at start
            if use_contributions and contribution_timing.startswith("Start"):
                balance += monthly_contribution
                year_deposits += monthly_contribution
                cum_deposits += monthly_contribution
            # monthly interest
            interest = balance * monthly_rate
            balance += interest
            year_interest += interest
            cum_interest += interest
            # income & expenses applied at month-end (with annual growth)
            monthly_income_val = monthly_income * ((1 + income_growth_rate/100.0) ** (year - 1)) if use_income_growth else monthly_income
            monthly_expenses_val = monthly_expenses * ((1 + expenses_growth_rate/100.0) ** (year - 1)) if use_expenses_growth else monthly_expenses
            balance += (monthly_income_val - monthly_expenses_val)
            # withdrawals
            if withdrawals:
                for w in withdrawals:
                    if w["type"] == "Monthly" and year >= int(w["start_year"]):
                        balance -= float(w["amount"])
                        year_withdrawals += float(w["amount"])
                    if w["type"] == "Lump Sum" and year == int(w["start_year"]) and m == 11:
                        balance -= float(w["amount"])
                        year_withdrawals += float(w["amount"])
            # contribution at end
            if use_contributions and contribution_timing.startswith("End"):
                balance += monthly_contribution
                year_deposits += monthly_contribution
                cum_deposits += monthly_contribution
        # update inflation factor for display
        if use_inflation:
            cumulative_inflation *= (1.0 + float(annual_inflation) / 100.0)
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
    # normalize rows -> DataFrame
    df = pd.DataFrame(rows)
    # ensure consistent column names for later use: unify end balance column
    if use_inflation:
        # columns contain end balance real column
        pass
    else:
        # ensure End Balance (real) column exists but with None so dataframe is stable
        df["End Balance (real)"] = None
    return df

# -----------------------
# Run simulation using current session_state values
# -----------------------
df = simulate_monthly_model(
    initial_investment=float(st.session_state.get("initial_investment", DEFAULTS["initial_investment"])),
    monthly_income=float(st.session_state.get("monthly_income", DEFAULTS["monthly_income"])),
    monthly_expenses=float(st.session_state.get("monthly_expenses", DEFAULTS["monthly_expenses"])),
    annual_growth_rate=float(st.session_state.get("annual_growth_rate", DEFAULTS["annual_growth_rate"])),
    projection_years=int(st.session_state.get("projection_years", DEFAULTS["projection_years"])),
    use_contributions=bool(st.session_state.get("use_contributions", DEFAULTS["use_contributions"])),
    monthly_contribution=float(st.session_state.get("monthly_contribution", DEFAULTS["monthly_contribution"])),
    contribution_timing=str(st.session_state.get("contribution_timing", DEFAULTS["contribution_timing"])),
    withdrawals=withdrawals,
    use_inflation=bool(st.session_state.get("use_inflation", DEFAULTS["use_inflation"])),
    annual_inflation=float(st.session_state.get("annual_inflation", DEFAULTS["annual_inflation"])),
    use_income_growth=bool(st.session_state.get("use_income_growth", DEFAULTS["use_income_growth"])),
    income_growth_rate=float(st.session_state.get("income_growth_rate", DEFAULTS["income_growth_rate"])),
    use_expenses_growth=bool(st.session_state.get("use_expenses_growth", DEFAULTS["use_expenses_growth"])),
    expenses_growth_rate=float(st.session_state.get("expenses_growth_rate", DEFAULTS["expenses_growth_rate"]))
)

# -----------------------
# Display results
# -----------------------
st.subheader("Projection table (yearly)")
st.dataframe(df.fillna("N/A"), use_container_width=True)

# Plot stacked year bars and balance line
fig = go.Figure()
fig.add_trace(go.Bar(x=df["Year"], y=df["Yearly Deposits"], name="Yearly Deposits", marker_color="#2a9d8f"))
fig.add_trace(go.Bar(x=df["Year"], y=df["Yearly Interest"], name="Yearly Interest", marker_color="#457b9d"))

# withdrawals might be column
fig.add_trace(go.Bar(x=df["Year"], y=df["Yearly Withdrawals"], name="Yearly Withdrawals", marker_color="#e76f51"))

# choose end balance series
end_series = df["End Balance (real)"] if st.session_state.get("use_inflation", False) else df["End Balance (nominal)"]
fig.add_trace(go.Scatter(x=df["Year"], y=end_series, mode="lines+markers", name="End Balance", line=dict(color="black", width=3)))
fig.update_layout(barmode="stack", title="Yearly Deposits / Interest / Withdrawals (stacked) and End Balance", xaxis_title="Year", yaxis_title="£", template="plotly_white", height=640)
st.plotly_chart(fig, use_container_width=True)

# CSV export
csv_bytes = df.to_csv(index=False).encode("utf-8")
st.download_button(label="Download results CSV", data=csv_bytes, file_name="cashflow_results.csv", mime="text/csv")

st.markdown("**Notes:** Model uses monthly compounding with nominal APR/12. Contributions can be start (annuity-due) or end of month. Income/expenses growth and inflation are optional (advanced).")
