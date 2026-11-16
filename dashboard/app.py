# ============================================================
# AquaInsight — Interactive Dashboard
#
# Day 10 — Complete Code Through Task 10.20
#
# Architecture:
# PostgreSQL → FastAPI → Streamlit
#
# Data source:
# BarentsWatch Fishhealth API
#
# Reporting period:
# 2015–2025
# ============================================================


# ============================================================
# 1. IMPORT LIBRARIES
# ============================================================

import requests
import pandas as pd
import streamlit as st
import plotly.express as px


# ============================================================
# 2. DASHBOARD CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="AquaInsight",
    page_icon="🐟",
    layout="wide",
)

API_BASE_URL = "http://127.0.0.1:8000"


# ============================================================
# 3. REUSABLE API REQUEST FUNCTION
# ============================================================

def fetch_api_data(endpoint):
    """
    Retrieve JSON data from the AquaInsight FastAPI backend.

    Parameters
    ----------
    endpoint : str
        API endpoint, e.g. /api/v1/annual-summary.

    Returns
    -------
    dict or None
        Parsed JSON response, or None if the request fails.
    """

    url = f"{API_BASE_URL}{endpoint}"

    try:
        response = requests.get(
            url,
            timeout=10,
        )

        response.raise_for_status()

        return response.json()

    except requests.exceptions.RequestException as error:
        st.error(f"API request failed: {error}")
        return None

    except ValueError:
        st.error("The API returned invalid JSON.")
        return None


# ============================================================
# 4. DASHBOARD HEADER
# ============================================================

st.title("🐟 AquaInsight")

st.subheader("Norwegian Aquaculture Health Analytics")

st.write(
    "Explore weekly Norwegian aquaculture health observations "
    "from 2015 to 2025."
)


# ============================================================
# 5. VERIFY FASTAPI CONNECTION
# ============================================================

health_response = fetch_api_data("/api/v1/health")

if health_response and health_response.get("status") == "ok":
    st.success("FastAPI connection: Online")
else:
    st.error("FastAPI connection: Offline")
    st.stop()


# ============================================================
# 6. RETRIEVE ANNUAL STATISTICS
# ============================================================

annual_response = fetch_api_data("/api/v1/annual-summary")

if annual_response is None:
    st.stop()

if annual_response.get("status") != "success":
    st.error("Unable to retrieve annual statistics.")
    st.stop()

annual_records = annual_response.get("data", [])

if not annual_records:
    st.warning("No annual statistics available.")
    st.stop()


# ============================================================
# 7. CONVERT ANNUAL JSON INTO A PANDAS DATAFRAME
# ============================================================

df = pd.DataFrame(annual_records)

df = df.sort_values("year").reset_index(drop=True)


# ============================================================
# 8. CALCULATE NATIONAL KPIs
# ============================================================

total_observations = int(
    df["total_observations"].sum()
)

total_eligible = int(
    df["eligible_compliance_observations"].sum()
)

total_exceedances = int(
    df["lice_exceedances"].sum()
)

# Weighted overall exceedance rate
overall_exceedance_rate = (
    (total_exceedances / total_eligible) * 100
    if total_eligible > 0
    else None
)


# ============================================================
# 9. DISPLAY NATIONAL KPI CARDS
# ============================================================

reporting_start = int(df["year"].min())
reporting_end = int(df["year"].max())

st.header(
    f"National Overview ({reporting_start}–{reporting_end})"
)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="Total Observations",
        value=f"{total_observations:,}",
    )

with col2:
    st.metric(
        label="Eligible Observations",
        value=f"{total_eligible:,}",
    )

with col3:
    st.metric(
        label="Lice Exceedances",
        value=f"{total_exceedances:,}",
    )

with col4:
    st.metric(
        label="Overall Exceedance Rate",
        value=(
            f"{overall_exceedance_rate:.2f}%"
            if overall_exceedance_rate is not None
            else "N/A"
        ),
    )

st.info(
    "Exceedance percentage is calculated using eligible "
    "compliance observations, not all reported observations."
)


# ============================================================
# 10. PREPARE ANNUAL STATISTICS TABLE
# ============================================================

st.header("Annual Sea-Lice Statistics")

annual_columns = {
    "year": "Year",
    "total_observations": "Total Observations",
    "unique_localities": "Unique Localities",
    "valid_lice_measurements": "Valid Measurements",
    "missing_lice_measurements": "Missing Measurements",
    "average_adult_female_lice": "Average Adult Female Lice",
    "lice_exceedances": "Lice Exceedances",
    "eligible_compliance_observations": "Eligible Observations",
    "exceedance_percentage": "Exceedance (%)",
}

annual_display = df[
    list(annual_columns.keys())
].rename(columns=annual_columns)


# ============================================================
# 11. DISPLAY ANNUAL STATISTICS TABLE
# ============================================================

st.dataframe(
    annual_display,
    use_container_width=True,
    hide_index=True,
)

st.caption(
    f"Reporting years: {annual_response['total_years']} | "
    "Source: BarentsWatch Fishhealth"
)


# ============================================================
# 12. HISTORICAL SEA-LICE EXCEEDANCE TREND
# ============================================================

st.header("Historical Sea-Lice Exceedance Trends")

st.write(
    "Annual percentage of eligible observations "
    "exceeding the applicable sea-lice threshold."
)

fig = px.line(
    df,
    x="year",
    y="exceedance_percentage",
    markers=True,
    title=(
        "Sea-Lice Exceedance Rate in Norway "
        f"({reporting_start}–{reporting_end})"
    ),
    labels={
        "year": "Year",
        "exceedance_percentage": "Exceedance Rate (%)",
    },
)

fig.update_layout(
    xaxis=dict(
        tickmode="linear",
        dtick=1,
    ),
    yaxis=dict(
        rangemode="tozero",
        ticksuffix="%",
    ),
    hovermode="x unified",
)

st.plotly_chart(
    fig,
    use_container_width=True,
)


# ============================================================
# 13. PRODUCTION-AREA ANALYSIS
# ============================================================

st.header("Production-Area Analysis")

st.write(
    "Select a reporting year to explore sea-lice statistics "
    "across Norwegian aquaculture production areas."
)


# ============================================================
# 14. RETRIEVE AVAILABLE REPORTING YEARS
# ============================================================

years_response = fetch_api_data("/api/v1/available-years")

if years_response is None:
    st.stop()

if years_response.get("status") != "success":
    st.error("Unable to retrieve available reporting years.")
    st.stop()

available_years = years_response.get("years", [])

if not available_years:
    st.warning("No reporting years are available.")
    st.stop()


# ============================================================
# 15. CREATE INTERACTIVE YEAR SELECTOR
# ============================================================

selected_year = st.selectbox(
    label="Select Reporting Year",
    options=sorted(available_years, reverse=True),
    index=0,
)

st.info(
    f"You selected {selected_year} for production-area analysis."
)


# ============================================================
# 16. RETRIEVE PRODUCTION-AREA STATISTICS
# ============================================================

production_response = fetch_api_data(
    f"/api/v1/production-areas/{selected_year}"
)

if production_response is None:
    st.stop()

if production_response.get("status") != "success":
    st.error("Unable to retrieve production-area statistics.")
    st.stop()


# ============================================================
# 17. CONVERT PRODUCTION-AREA JSON INTO DATAFRAME
# ============================================================

production_records = production_response.get("data", [])

if not production_records:
    st.warning(
        f"No production-area data available for {selected_year}."
    )
    st.stop()

production_df = pd.DataFrame(production_records)


# ============================================================
# 18. PREPARE PRODUCTION-AREA STATISTICS TABLE
# ============================================================

production_columns = {
    "production_area_id": "Area ID",
    "production_area": "Production Area",
    "unique_localities": "Unique Localities",
    "eligible_observations": "Eligible Observations",
    "exceedance_observations": "Exceedances",
    "exceedance_percentage": "Exceedance (%)",
}

production_display = production_df[
    list(production_columns.keys())
].rename(columns=production_columns)


# ============================================================
# 19. DISPLAY PRODUCTION-AREA STATISTICS
# ============================================================

st.subheader(
    f"Production-Area Statistics — {selected_year}"
)

st.dataframe(
    production_display,
    use_container_width=True,
    hide_index=True,
)

st.caption(
    "Production-area groups returned: "
    f"{production_response['total_production_areas']}"
)


# ============================================================
# 20. INTERACTIVE PRODUCTION-AREA COMPARISON
# ============================================================

st.subheader(
    "Sea-Lice Exceedance Rates by Production Area "
    f"— {selected_year}"
)

# Exclude records without a valid area name or rate.
# Keep the original production_df unchanged.
chart_df = production_df.dropna(
    subset=[
        "production_area",
        "exceedance_percentage",
    ]
).copy()

chart_df = chart_df.sort_values(
    "exceedance_percentage",
    ascending=True,
)

if chart_df.empty:
    st.warning(
        "No production-area exceedance rates are available "
        "for the selected year."
    )

else:
    fig_area = px.bar(
        chart_df,
        x="exceedance_percentage",
        y="production_area",
        orientation="h",
        title=f"Production-Area Comparison ({selected_year})",
        labels={
            "exceedance_percentage": "Exceedance Rate (%)",
            "production_area": "Production Area",
        },
        hover_data={
            "eligible_observations": True,
            "exceedance_observations": True,
            "unique_localities": True,
            "exceedance_percentage": ":.2f",
        },
    )

    fig_area.update_layout(
        height=650,
        xaxis=dict(
            rangemode="tozero",
            range=[
                0,
                max(
                    chart_df["exceedance_percentage"].max() * 1.20,
                    1,
                ),
            ],
        ),
        yaxis_title=None,
        margin=dict(r=90),
    )

    # Display percentages beside each bar.
    # This also shows 0.00% for areas with zero exceedances.
    fig_area.update_traces(
        text=chart_df["exceedance_percentage"].map(
            lambda value: f"{value:.2f}%"
        ),
        textposition="outside",
        cliponaxis=False,
    )

    st.plotly_chart(
        fig_area,
        use_container_width=True,
    )

# ============================================================
# DATA-QUALITY API INTEGRATION
# Day 10 — Task 10.43
# ============================================================

# Retrieve annual reporting-quality statistics from FastAPI
quality_response = fetch_api_data("/api/v1/data-quality")

# Stop if the API request fails
if quality_response is None:
    st.stop()

# Validate the response status
if quality_response.get("status") != "success":
    st.error("Unable to retrieve data-quality statistics.")
    st.stop()

# Extract annual records
quality_records = quality_response.get("data", [])

if not quality_records:
    st.warning("No data-quality statistics are available.")
    st.stop()

# Convert JSON records into a pandas DataFrame
quality_df = pd.DataFrame(quality_records)

# Sort records chronologically
quality_df = quality_df.sort_values("year").reset_index(drop=True)
# ============================================================
# Day 10 — Task 10.47
# Reporting-status breakdown
# ============================================================

st.subheader("Reporting-Status Breakdown (2015–2025)")

# Total observations probably without fish,
# where sea lice were not counted
without_fish_not_counted = int(
    quality_df["probably_without_fish_not_counted"].sum()
)

# Total observations not flagged as without fish,
# where sea lice were not counted
other_not_counted = int(
    quality_df["fish_status_false_not_counted"].sum()
)

# Total observations where sea lice were counted
lice_counted_total = int(
    quality_df["lice_counted_observations"].sum()
)

# Total reporting conflicts
conflicts_total = int(
    quality_df["reporting_conflicts"].sum()
)
# ============================================================
# Day 10 — Task 10.49
# Validate reporting-status reconciliation
# ============================================================

categorized_total = (
    without_fish_not_counted
    + other_not_counted
    + lice_counted_total
)

uncategorized_total = total_observations - categorized_total

if uncategorized_total < 0:
    st.error(
        "Data-quality error: Reporting categories exceed "
        "the total number of observations."
    )

elif uncategorized_total > 0:
    st.warning(
        f"{uncategorized_total:,} observations have "
        "unclassified reporting statuses."
    )

else:
    st.success(
        "Data-quality reconciliation passed: "
        f"All {total_observations:,} observations are accounted for."
    )
# Build a summary table
reporting_summary = pd.DataFrame({
    "Reporting Status": [
        "Probably without fish — lice not counted",
        "Not flagged as without fish — lice not counted",
        "Lice counted"
    ],
    "Observations": [
        without_fish_not_counted,
        other_not_counted,
        lice_counted_total
    ]
})

# Calculate percentage of all observations
reporting_summary["Percentage (%)"] = (
    reporting_summary["Observations"]
    / total_observations
    * 100
).round(2)

# Display the table
st.dataframe(
    reporting_summary,
    hide_index=True,
    use_container_width=True
)
# ============================================================
# Day 10 — Task 10.48
# Reporting-status distribution chart
# ============================================================

# Sort categories by observation count
reporting_chart_df = reporting_summary.sort_values(
    "Observations",
    ascending=True
)

# Create horizontal bar chart
fig_reporting = px.bar(
    reporting_chart_df,
    x="Observations",
    y="Reporting Status",
    orientation="h",
    title="Aquaculture Reporting-Status Distribution (2015–2025)",
    text="Percentage (%)",
    hover_data={
        "Observations": ":,",
        "Percentage (%)": ":.2f"
    }
)

# Format percentage labels
fig_reporting.update_traces(
    texttemplate="%{text:.2f}%",
    textposition="outside",
    cliponaxis=False
)

# Improve chart layout
fig_reporting.update_layout(
    height=400,
    xaxis_title="Number of Observations",
    yaxis_title=None,
    xaxis=dict(rangemode="tozero"),
    margin=dict(l=300, r=100)
)

# Display chart
st.plotly_chart(
    fig_reporting,
    use_container_width=True
)
# Display reporting conflicts separately
st.metric(
    label="Potential Reporting Conflicts",
    value=f"{conflicts_total:,}"
)

st.caption(
    "Reporting conflicts are a separate quality flag and "
    "are already included in the reporting-status categories."
)
# Verify data-quality API integration
st.success(
    f"Data-quality API connected: {len(quality_df)} annual records loaded."
)
# ============================================================
# 21. DATA QUALITY — OVERALL MISSING MEASUREMENTS
# ============================================================

total_missing = int(
    df["missing_lice_measurements"].sum()
)

missing_percentage = (
    (total_missing / total_observations) * 100
    if total_observations > 0
    else None
)

st.header("Data Quality")

st.write(
    "Explore missing adult female lice measurements "
    "across Norwegian aquaculture reporting years."
)

st.metric(
    label="Missing Adult Female Lice Measurements",
    value=f"{total_missing:,}",
    delta=(
        f"{missing_percentage:.2f}% of all observations"
        if missing_percentage is not None
        else None
    ),
    delta_color="off",
)

st.caption(
    "A missing lice measurement does not necessarily indicate "
    "a reporting failure. Some localities may have no fish "
    "or may not have performed lice counts."
)


# ============================================================
# 22. CALCULATE ANNUAL MISSING-MEASUREMENT PERCENTAGES
# ============================================================

df["missing_percentage"] = (
    df["missing_lice_measurements"]
    / df["total_observations"].replace(0, float("nan"))
    * 100
)


# ============================================================
# 23. INTERACTIVE ANNUAL MISSING-DATA TREND
# ============================================================

st.subheader("Missing Lice Measurements by Year")

fig_missing = px.line(
    df,
    x="year",
    y="missing_percentage",
    markers=True,
    title="Annual Missing Adult Female Lice Measurements",
    labels={
        "year": "Year",
        "missing_percentage": "Missing Measurements (%)",
    },
)

fig_missing.update_layout(
    xaxis=dict(
        tickmode="linear",
        dtick=1,
    ),
    yaxis=dict(
        rangemode="tozero",
        ticksuffix="%",
    ),
    hovermode="x unified",
)

st.plotly_chart(
    fig_missing,
    use_container_width=True,
)


# ============================================================
# 24. DATA-QUALITY SUMMARY
# ============================================================

st.caption(
    "Data-quality statistics are calculated from the "
    "annual summaries returned by the AquaInsight FastAPI backend."
)

st.info(
    "Missing measurements and compliance eligibility are "
    "different concepts. Missing values should be investigated "
    "using the underlying reporting-status fields before "
    "drawing conclusions about reporting quality."
)


# ============================================================
# END — DAY 10, TASK 10.20
# ============================================================
