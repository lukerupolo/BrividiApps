# strategy.py

def generate_strategy(objective, investment, metrics, ai_categories, influencer_data, owned_channel_data):
    """
    Generates strategic advice and calculated benchmarks based on a detailed
    event profile, including investment, influencers, and owned channels.

    Args:
        objective (str): The primary campaign goal.
        investment (str): The campaign's investment level.
        metrics (list): A list of the user's selected metrics.
        ai_categories (dict): A dictionary mapping metrics to their AI-generated category.
        influencer_data (list): A list of dictionaries, each containing data for an influencer.
        owned_channel_data (dict): A dictionary containing data for owned channels.

    Returns:
        dict: A dictionary containing prioritized metrics, considerations, and calculated outputs.
    """

    # --- Part 1: Calculate Investment Weighting Factor ---
    investment_map = {
        "Low (<$50k)": 1.0,
        "Medium ($50k - $250k)": 1.25,
        "High ($250k - $1M)": 1.6,
        "Major (>$1M)": 2.0
    }
    investment_weighting_factor = investment_map.get(investment, 1.0)

    # --- Part 2: Calculate Influencer Metrics ---
    total_potential_reach = 0
    total_projected_engaged_audience = 0
    total_cpv = 0
    influencer_count = 0
    if influencer_data:
        for influencer in influencer_data:
            followers = influencer.get("follower_count", 0)
            engagement_rate = influencer.get("engagement_rate", 0) / 100.0  # Convert from % to decimal
            average_views = influencer.get("average_views", 0)
            cost_per_video = influencer.get("cost_per_video", 0)
            
            total_potential_reach += followers
            total_projected_engaged_audience += followers * engagement_rate
            
            # Calculate CPV (Cost Per Views) for this influencer
            if average_views > 0:
                cpv = cost_per_video / average_views
                total_cpv += cpv
                influencer_count += 1

    # --- Part 3: Consolidate Calculated Outputs ---
    # Calculate average CPV
    average_cpv = total_cpv / influencer_count if influencer_count > 0 else 0
    
    calculated_outputs = {
        "Investment Weighting Factor": f"{investment_weighting_factor}x",
        "Total Potential Influencer Reach": f"{total_potential_reach:,.0f}",
        "Total Projected Engaged Audience": f"{total_projected_engaged_audience:,.0f}",
        "Average CPV (Cost Per Views)": f"${average_cpv:.4f}" if average_cpv > 0 else "N/A",
        "Owned Channel Avg. Reach": f"{owned_channel_data.get('avg_reach', 0):,.0f}",
        "Owned Channel Avg. Engagement": f"{owned_channel_data.get('avg_engagement', 0)}%"
    }

    # --- Part 4: Prioritize Metrics based on Objective (Original Logic) ---
    prioritized_metrics = []
    priority_map = {
        "Brand Awareness / Reach":      {"Reach": "High", "Depth": "Medium", "Action": "Low"},
        "Audience Engagement / Depth":  {"Depth": "High", "Reach": "Medium", "Action": "Low"},
        "Conversion / Action":          {"Action": "High", "Depth": "Medium", "Reach": "Low"}
    }
    current_priority_scheme = priority_map.get(objective, {})

    for metric in metrics:
        category = ai_categories.get(metric, "Uncategorized")
        priority = current_priority_scheme.get(category, "Medium")
        prioritized_metrics.append({
            "Metric": metric,
            "Category": category,
            "Priority": priority
        })

    # --- Part 5: Generate Strategic Considerations (Original Logic, can be enhanced later) ---
    considerations = []
    high_cost_metrics = ["Press UMV (unique monthly views)", "Social Impressions"]

    if investment == 'Low (<$50k)':
        costly_metrics_selected = [m for m in metrics if m in high_cost_metrics]
        if costly_metrics_selected:
            considerations.append({
                "type": "Warning",
                "text": f"With a 'Low' investment, achieving high performance for costly metrics like {', '.join(costly_metrics_selected)} can be challenging. Focus on organic growth and efficiency."
            })

    if objective == 'Conversion / Action' and not any(p['Category'] == 'Action' for p in prioritized_metrics):
        considerations.append({
                "type": "Warning",
                "text": "Your objective is 'Conversion / Action', but no 'Action' metrics are selected. Ensure you add metrics that directly measure your conversion goals (e.g., sign-ups, downloads)."
            })

    # --- Final Return Object ---
    return {
        "calculated_outputs": calculated_outputs,
        "prioritized_metrics": prioritized_metrics,
        "strategic_considerations": considerations,
    }
