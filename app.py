import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta
from google.oauth2 import service_account
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest, DateRange, Dimension,
    Metric, Filter, FilterExpression
)

# ---------------- PAGE CONFIG ---------------- #
st.set_page_config(page_title="GA4 Category Report", layout="wide")
st.title("📊 GA4 Monthly Category Report")

# ---------------- PROPERTY MAPPING ---------------- #
view_id_name_mapping = {
    "424738282": "DNA English",
    "424752920": "DNA Hindi",
    "424754635": "ICOM Hindi",
    "424788272": "ICOM English",
    "424733916": "Zee Bengali",
    "424734706": "Zee Odisha",
    "424737620": "Zee PHH",
    "424740324": "Zee Rajasthan",
    "424747120": "Zee Salaam",
    "424748591": "Zee Gujarati",
    "424751136": "Zee Hindustan",
    "424751758": "Zee English",
    "424752916": "Zee Telugu",
    "424755684": "Zee UP UK",
    "424756835": "Zee Hindi",
    "424807672": "Delhi NCR Harayana",
    "424807363": "Zee Bihar Jharkhand",
    "424803703": "Zee MP CG",
    "424803190": "Zee Tamil",
    "424802051": "Zee Malayalam",
    "424797141": "Zee Marathi",
    "424784463": "Zee Kannada",
    "449141964": "WION",
    "424815185": "Zee Biz English",
    "424771953": "Zee Biz Hindi",
    "425235134": "HealthSite English",
    "425228038": "HealthSite Hindi",
    "379536469": "Screenbox",
    "425234014": "Bollywood Life English",
    "425220388": "Bollywood Life Hindi",
    "425245314": "CricketCountry English",
    "425237720": "CricketCountry Hindi",
    "425228771": "Techlusive English",
    "425219576": "Techlusive Hindi",
    "374981587": "MyLord",
    "432213368": "Petuz",
    "429575403": "Travel by India"
}

# ---------------- SIDEBAR ---------------- #
st.sidebar.header("🔐 Authentication")
cred_file = st.sidebar.file_uploader(
    "Upload GA4 Service Account JSON",
    type=["json"]
)

st.sidebar.header("📅 Date Range")
start_date = st.sidebar.date_input("Start Date", datetime(2024, 8, 1))
end_date = st.sidebar.date_input(
    "End Date", datetime.today() - timedelta(days=1)
)

st.sidebar.header("🌐 GA4 Sites")
selected_sites = st.sidebar.multiselect(
    "Select Properties",
    options=list(view_id_name_mapping.keys()),
    format_func=lambda x: f"{view_id_name_mapping[x]} ({x})"
)

st.sidebar.header("🔎 PagePath Regex")
regex_input = st.sidebar.text_area(
    "One regex per line",
    height=180,
    placeholder=".*(/mp/).*\n.*(/politics/).*"
)

fetch_btn = st.sidebar.button("🚀 Fetch GA4 Data")

# ---------------- GA4 FUNCTION ---------------- #
def fetch_ga4_data(client, property_id, site_name, regex, start_date, end_date):
    request = RunReportRequest(
        property=f"properties/{property_id}",
        date_ranges=[
            DateRange(
                start_date=start_date.strftime("%Y-%m-%d"),
                end_date=end_date.strftime("%Y-%m-%d")
            )
        ],
        dimensions=[Dimension(name="year"), Dimension(name="month")],
        metrics=[Metric(name="totalUsers"), Metric(name="screenPageViews")],
        dimension_filter=FilterExpression(
            filter=Filter(
                field_name="pagePath",
                string_filter=Filter.StringFilter(
                    match_type=Filter.StringFilter.MatchType.FULL_REGEXP,
                    value=regex
                )
            )
        )
    )

    response = client.run_report(request)
    rows = []

    for row in response.rows:
        rows.append({
            "Site": site_name,
            "Year_Month": f"{row.dimension_values[0].value}-{row.dimension_values[1].value.zfill(2)}",
            "Total_Users": int(row.metric_values[0].value),
            "Pageviews": int(row.metric_values[1].value),
            "Regex": regex
        })

    return rows

# ---------------- MAIN ---------------- #
if fetch_btn:
    if not cred_file:
        st.error("❌ Upload GA4 Service Account JSON")
    elif not selected_sites:
        st.error("❌ Select at least one site")
    elif not regex_input.strip():
        st.error("❌ Enter at least one regex")
    else:
        with st.spinner("Fetching GA4 data..."):
            service_account_info = json.loads(
                cred_file.getvalue().decode("utf-8")
            )

            credentials = service_account.Credentials.from_service_account_info(
                service_account_info,
                scopes=["https://www.googleapis.com/auth/analytics.readonly"]
            )

            client = BetaAnalyticsDataClient(credentials=credentials)
            regex_list = [r.strip() for r in regex_input.splitlines() if r.strip()]

            final_data = []

            for property_id in selected_sites:
                site_name = view_id_name_mapping[property_id]
                for regex in regex_list:
                    final_data.extend(
                        fetch_ga4_data(
                            client,
                            property_id,
                            site_name,
                            regex,
                            start_date,
                            end_date
                        )
                    )

            if final_data:
                df = pd.DataFrame(final_data)
                st.success(f"✅ Data fetched: {len(df)} rows")

                st.dataframe(df, use_container_width=True)

                csv = df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "⬇️ Download CSV",
                    csv,
                    "ga4_category_report.csv",
                    "text/csv"
                )
            else:
                st.warning("⚠️ No data returned")
