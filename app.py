import streamlit as st
from io import BytesIO
from datetime import datetime
import pandas as pd

# --- Local Imports from our other files ---
from style import STYLE_PRESETS
from ui import render_sidebar
# Updated import to include get_ai_metric_categories
from data_processing import process_scorecard_data, calculate_all_benchmarks, get_ai_metric_categories
from powerpoint import create_presentation
from excel import create_excel_workbook
# New import for the strategy logic
from strategy import generate_strategy

# ================================================================================
# 1) App State Initialization
# ================================================================================
st.set_page_config(page_title="Event Marketing Scorecard", layout="wide")

# Version updated to reflect the new feature
APP_VERSION = "4.2.1" # Version updated for form fix

if 'app_version' not in st.session_state or st.session_state.app_version != APP_VERSION:
    api_key = st.session_state.get('openai_api_key')

    # Clear all keys from the session state
    for key in list(st.session_state.keys()):
        del st.session_state[key]

    # Initialize all keys to their default values
    st.session_state.app_version = APP_VERSION
    st.session_state.api_key_entered = True if api_key else False
    st.session_state.openai_api_key = api_key
    st.session_state.metrics_confirmed = False
    st.session_state.strategy_complete = False
    st.session_state.benchmark_flow_complete = False
    st.session_state.scorecard_ready = False
    st.session_state.show_ppt_creator = False
    st.session_state.metrics = []
    st.session_state.ai_categories = {}
    st.session_state.strategy_profile = {}
    st.session_state.benchmark_choice = "No, I will enter benchmarks manually later."
    st.session_state.benchmark_df = pd.DataFrame()
    st.session_state.sheets_dict = None
    st.session_state.presentation_buffer = None
    st.session_state.proposed_benchmarks = {}
    st.session_state.avg_actuals = {}
    st.session_state.saved_moments = {}
    # --- NEW STATE VARIABLES FOR STRATEGY ---
    if 'influencers' not in st.session_state:
        st.session_state.influencers = []


st.title("Event Marketing Scorecard & Presentation Generator")
render_sidebar()

# ================================================================================
# Step 0: API Key Entry
# ================================================================================
if not st.session_state.api_key_entered:
    st.header("Step 0: Enter Your OpenAI API Key")
    with st.form("api_key_form"):
        api_key_input = st.text_input("🔑 OpenAI API Key", type="password")
        if st.form_submit_button("Submit API Key"):
            if api_key_input:
                st.session_state.openai_api_key = api_key_input
                st.session_state.api_key_entered = True
                st.rerun()
            else:
                st.error("Please enter a valid OpenAI API key.")

# ================================================================================
# Step 1: Metric Selection
# ================================================================================
elif not st.session_state.metrics_confirmed:
    st.header("Step 1: Metric Selection")

    if 'current_metrics' not in st.session_state:
        st.session_state.current_metrics = ["Video views (Franchise)", "Social Impressions"]

    st.info("Select metrics from the dropdown, or add your own below. Press Enter to add a custom metric.")

    predefined_metrics = [
        "Video views (Franchise)", "Social Impressions", "Press UMV (unique monthly views)",
        "Social Conversation Volume", "Views trailer", "UGC Views",
        "Social Impressions-Posts with trailer (FB, IG, X)", "Social Impressions-All posts",
        "Nb. press articles", "Social Sentiment (Franchise)", "Trailer avg % viewed (Youtube)",
        "Email Open Rate (OR)", "Email Click Through Rate (CTR)", "Labs program sign-ups",
        "Discord channel sign-ups", "% Trailer views from Discord (Youtube)",
        "Labs sign up click-through Web", "Sessions", "DAU", "Hours Watched (Streams)",
        "CPV (Cost Per View)"
    ]

    all_possible_metrics = sorted(list(set(predefined_metrics + st.session_state.current_metrics)))

    def update_selections():
        st.session_state.current_metrics = st.session_state.multiselect_key

    st.multiselect(
        "Select metrics:",
        options=all_possible_metrics,
        default=st.session_state.current_metrics,
        key="multiselect_key",
        on_change=update_selections
    )

    def add_custom_metric():
        custom_metric = st.session_state.custom_metric_input.strip()
        if custom_metric and custom_metric not in st.session_state.current_metrics:
            st.session_state.current_metrics.append(custom_metric)
        st.session_state.custom_metric_input = ""

    st.text_input(
        "✍️ Add Custom Metric (and press Enter)",
        key="custom_metric_input",
        on_change=add_custom_metric
    )

    st.markdown("---")

    if st.button("Confirm Metrics & Proceed →", type="primary"):
        if not st.session_state.current_metrics:
            st.error("Please select at least one metric.")
        else:
            st.session_state.metrics = st.session_state.current_metrics
            with st.spinner("Using AI to categorize your metrics..."):
                st.session_state.ai_categories = get_ai_metric_categories(
                    st.session_state.metrics,
                    st.session_state.openai_api_key
                )
            st.session_state.metrics_confirmed = True
            del st.session_state.current_metrics
            st.rerun()

# ================================================================================
# MODIFIED Step 2: Campaign & Investment Profile
# ================================================================================
elif not st.session_state.strategy_complete:
    st.header("Step 2: Campaign & Investment Profile")
    st.info("Provide details about your campaign's strategy and investments to generate a detailed profile and inform your benchmarks.")

    # --- Part B: Influencer Management (MOVED OUTSIDE THE FORM) ---
    with st.expander("Part B: Influencer Investment & Reach"):
        st.write("Add or remove influencers for the campaign. The data is saved as you type.")
        # Display input fields for each influencer in the list
        for i, influencer in enumerate(st.session_state.influencers):
            st.markdown(f"--- \n ##### Influencer {i+1}")
            cols = st.columns([2,1,1,1,1,1])
            st.session_state.influencers[i]['name'] = cols[0].text_input("Name/Handle", value=influencer.get('name',''), key=f"inf_name_{i}")
            st.session_state.influencers[i]['follower_count'] = cols[1].number_input("Followers", min_value=0, value=influencer.get('follower_count',0), key=f"inf_followers_{i}")
            st.session_state.influencers[i]['engagement_rate'] = cols[2].number_input("Engagement %", min_value=0.0, max_value=100.0, value=influencer.get('engagement_rate',0.0), format="%.2f", key=f"inf_eng_{i}")
            st.session_state.influencers[i]['average_views'] = cols[3].number_input("Avg Views", min_value=0, value=influencer.get('average_views',0), key=f"inf_views_{i}")
            st.session_state.influencers[i]['cost_per_video'] = cols[4].number_input("Cost/Video ($)", min_value=0.0, value=influencer.get('cost_per_video',0.0), format="%.2f", key=f"inf_cost_{i}")
            # The remove button is a regular button and works fine here
            if cols[5].button(f"Remove", key=f"inf_remove_{i}"):
                st.session_state.influencers.pop(i)
                st.rerun()

    # The "Add Influencer" button is now outside the form
    if st.button("Add Influencer"):
        st.session_state.influencers.append({})
        st.rerun()
    
    st.markdown("---")

    # The form now only contains the other inputs and the final submit button
    with st.form("strategy_form"):
        # --- Part A: Core Strategy ---
        with st.expander("Part A: Core Strategy", expanded=True):
            objective = st.selectbox(
                "Primary Objective:",
                options=["Brand Awareness / Reach", "Audience Engagement / Depth", "Conversion / Action"],
                key="strategy_objective"
            )
            investment = st.selectbox(
                "Campaign Investment Level:",
                options=["Low (<$50k)", "Medium ($50k - $250k)", "High ($250k - $1M)", "Major (>$1M)"],
                key="strategy_investment"
            )

        # --- Part C: Owned Organic Channel Performance ---
        with st.expander("Part C: Owned Organic Channel Performance", expanded=True):
            st.write("Provide the baseline performance for your own social media or content channels.")
            owned_avg_reach = st.number_input("Average Historical Reach (per major post)", min_value=0, key="owned_reach")
            owned_avg_engagement = st.number_input("Average Historical Engagement Rate (%)", min_value=0.0, max_value=100.0, format="%.2f", key="owned_engagement")

        # --- Form Submission ---
        submitted = st.form_submit_button("Generate Strategy Profile & Proceed →", type="primary")
        if submitted:
            owned_channel_data = {
                "avg_reach": owned_avg_reach,
                "avg_engagement": owned_avg_engagement
            }
            # Note: We read st.session_state.influencers directly here
            strategy_profile = generate_strategy(
                objective,
                investment,
                st.session_state.metrics,
                st.session_state.ai_categories,
                st.session_state.influencers,
                owned_channel_data
            )
            st.session_state.strategy_profile = strategy_profile
            st.session_state.strategy_complete = True
            st.rerun()

    # This part remains to display the results after submission
    if st.session_state.get("strategy_complete"):
        profile = st.session_state.strategy_profile
        st.markdown("---")
        st.subheader("Your Strategic Recommendation")

        if profile.get("calculated_outputs"):
             st.markdown("#### Calculated Profile Outputs")
             df_outputs = pd.DataFrame([profile["calculated_outputs"]])
             st.dataframe(df_outputs, use_container_width=True, hide_index=True)

        if profile.get("prioritized_metrics"):
            st.markdown("#### Metric Prioritization")
            st.dataframe(pd.DataFrame(profile["prioritized_metrics"]), use_container_width=True)

        if profile.get("strategic_considerations"):
            st.markdown("#### Strategic Considerations")
            for item in profile["strategic_considerations"]:
                if item['type'] == 'Warning': st.warning(item['text'])
                else: st.info(item['text'])

        st.markdown("---")
        if st.button("Proceed to Benchmark Calculation →", type="primary"):
            st.rerun()

# ================================================================================
# Step 3: Optional Benchmark Calculation
# ================================================================================
elif not st.session_state.benchmark_flow_complete:
    st.header("Step 3: Benchmark Calculation (Optional)")

    benchmark_choice = st.radio(
        "Would you like to calculate proposed benchmark values using historical data?",
        ("No, I will enter benchmarks manually later.", "Yes, calculate benchmarks from past events."),
        key="benchmark_choice_radio"
    )

    if benchmark_choice == "Yes, calculate benchmarks from past events.":
        with st.form("benchmark_data_form"):
            st.info("For each metric, provide its 3-month average from your external tool, then enter the Baseline and Actual values from past events to calculate the expected uplift.")
            historical_inputs = {}
            for metric in st.session_state.metrics:
                st.markdown(f"--- \n #### Data for: **{metric}**")
                three_month_avg = st.number_input(f"3-Month Average (Baseline Method) for '{metric}'", min_value=0.0, format="%.2f", key=f"3m_avg_{metric}")
                df_template = pd.DataFrame([{"Event Name": "Past Event 1", "Baseline (7-day)": None, "Actual (7-day)": None}])
                edited_df = st.data_editor(df_template, key=f"hist_editor_{metric}", num_rows="dynamic", use_container_width=True)
                historical_inputs[metric] = {"historical_df": edited_df, "three_month_avg": three_month_avg}

            if st.form_submit_button("Calculate All Proposed Benchmarks & Proceed →", type="primary"):
                with st.spinner("Analyzing historical data..."):
                    summary_df, proposed_benchmarks, avg_actuals = calculate_all_benchmarks(historical_inputs)
                    st.session_state.benchmark_df = summary_df
                    st.session_state.proposed_benchmarks = proposed_benchmarks
                    st.session_state.avg_actuals = avg_actuals
                    st.session_state.benchmark_flow_complete = True
                st.rerun()
    else:
        if st.button("Proceed to Scorecard Creation →", type="primary"):
            st.session_state.benchmark_flow_complete = True
            st.rerun()

# ================================================================================
# Step 4 & 5 - Main App Logic
# ================================================================================
else:
    app_config = {
        'openai_api_key': st.session_state.openai_api_key,
        'metrics': st.session_state.metrics,
        'proposed_benchmarks': st.session_state.get('proposed_benchmarks'),
        'avg_actuals': st.session_state.get('avg_actuals')
    }

    st.header("Step 4: Build & Save Scorecard Moments")
    if st.session_state.sheets_dict is None:
        st.session_state.sheets_dict = process_scorecard_data(app_config)

    st.info("Fill in the 'Actuals' and 'Benchmark' columns, give the scorecard a name, and save it as a 'moment'. You can create multiple moments.")
    current_scorecard_df = next(iter(st.session_state.sheets_dict.values()), None)

    if current_scorecard_df is not None:
        edited_df = st.data_editor(current_scorecard_df, key="moment_editor", use_container_width=True, num_rows="dynamic")
        edited_df['Actuals'] = pd.to_numeric(edited_df['Actuals'], errors='coerce')
        edited_df['Benchmark'] = pd.to_numeric(edited_df['Benchmark'], errors='coerce')
        edited_df['% Difference'] = ((edited_df['Actuals'] - edited_df['Benchmark']) / edited_df['Benchmark'].replace(0, pd.NA)).apply(lambda x: f"{x:.1%}" if pd.notna(x) else None)
        
        col1, col2 = st.columns([3, 1])
        moment_name = col1.text_input("Name for this Scorecard Moment", placeholder="e.g., Pre-Reveal, Launch Week")
        
        if col2.button("💾 Save Moment", use_container_width=True, type="primary"):
            if moment_name:
                st.session_state.saved_moments[moment_name] = edited_df
                st.success(f"Saved moment: '{moment_name}'")
                st.session_state.sheets_dict = None
                st.rerun()
            else:
                st.error("Please enter a name for the moment before saving.")

    if st.session_state.saved_moments:
        st.markdown("---")
        st.subheader("Saved Scorecard Moments")
        if st.session_state.benchmark_df is not None and not st.session_stte.benchmark_df.empty:
            with st.expander("View Benchmark Calculation Summary"):
                st.dataframe(st.session_state.benchmark_df.set_index("Metric"), use_container_width=True)
        
        for name, df in st.session_state.saved_moments.items():
            with st.expander(f"View Moment: {name}"):
                st.dataframe(df, use_container_width=True)
        st.session_state.show_ppt_creator = True

    if st.session_state.get('show_ppt_creator'):
        st.markdown("---")
        st.header("Step 5: Create Presentation")
        
        if st.session_state.get("presentation_buffer"):
            st.download_button(label="✅ Download Your Presentation!", data=st.session_state.presentation_buffer, file_name="game_scorecard_presentation.pptx", use_container_width=True)

        with st.form("ppt_form"):
            st.subheader("Presentation Style & Details")
            
            if st.session_state.saved_moments:
                selected_moments = st.multiselect("Select which saved moments to include in the presentation:",
                    options=list(st.session_state.saved_moments.keys()),
                    default=list(st.session_state.saved_moments.keys()))
            else:
                st.warning("No scorecard moments saved yet. Please save at least one moment above.")
                selected_moments = []

            col1, col2 = st.columns(2)
            selected_style_name = col1.radio("Select Style Preset:", options=list(STYLE_PRESETS.keys()), horizontal=True)
            image_region_prompt = col2.text_input("Region for AI Background Image", "Brazil")
            ppt_title = st.text_input("Presentation Title", "Game Scorecard")
            ppt_subtitle = st.text_input("Presentation Subtitle", "A detailed analysis")
            
            submitted = st.form_submit_button("Generate Presentation", use_container_width=True)

            if submitted:
                if not selected_moments:
                    st.error("Please select at least one saved moment to include in the presentation.")
                else:
                    with st.spinner(f"Building presentation with {selected_style_name} style..."):
                        presentation_data = {name: st.session_state.saved_moments[name] for name in selected_moments}
                        style_guide = STYLE_PRESETS[selected_style_name]
                        ppt_buffer = create_presentation(
                            title=ppt_title,
                            subtitle=ppt_subtitle,
                            scorecard_moments=selected_moments,
                            sheets_dict=presentation_data,
                            style_guide=style_guide,
                            region_prompt=image_region_prompt,
                            openai_api_key=st.session_state.openai_api_key 
                        )
                        st.session_state["presentation_buffer"] = ppt_buffer
                        st.rerun()
