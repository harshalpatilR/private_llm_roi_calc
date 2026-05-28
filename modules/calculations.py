# def format_token_label(val):
#     if val >= 1e12: return f"{val/1e12:g}T"
#     if val >= 1e9: return f"{val/1e9:g}B"
#     if val >= 1e6: return f"{val/1e6:g}M"
#     return str(val)

def calculate_cloud_costs(total_tokens, in_pct, out_pct, models):
    # --- START CHANGE 6001: PURE MATH ISOLATION ---
    total_weight = sum(m['weight'] for m in models)
    
    # Use 1 as default to prevent math collapse if sliders are at 0
    norm_factor = (100 / total_weight) if total_weight > 0 else 1
    
    total_input_tokens = total_tokens * (in_pct / 100)
    total_output_tokens = total_tokens * (out_pct / 100)
    
    total_cost = 0
    breakdown = []
    
    for m in models:
        # Simplified: Multiplication naturally handles the zero-case
        norm_weight = m['weight'] * norm_factor
        
        m_in_tokens = total_input_tokens * (norm_weight / 100)
        m_out_tokens = total_output_tokens * (norm_weight / 100)
        
        m_cost = (m_in_tokens / 1e6 * m['input_price']) + (m_out_tokens / 1e6 * m['output_price'])
        total_cost += m_cost
        
        # Package all raw data for the UI to handle table rendering
        breakdown.append({
            "name": m['name'],
            "cost": m_cost,
            "weight": m['weight'],
            "norm_weight": norm_weight,
            "in_tokens": m_in_tokens,
            "out_tokens": m_out_tokens,
            "in_price": m['input_price'],
            "out_price": m['output_price'],
            "model_total_cost": m_cost  # ADDED: Explicit total cost for this model
        })
            
    cpm = (total_cost / (total_tokens / 1e6)) if total_tokens > 0 else 0
    
    for b in breakdown:
        # Relative % of the final wallet spend
        b['pct_of_total_spend'] = (b['model_total_cost'] / total_cost * 100) if total_cost > 0 else 0
    
    return total_cost, cpm, breakdown
    # --- END CHANGE 6001 ---

def format_token_label(index):
    labels = ["10M", "50M", "100M", "500M", "1B", "5B", "10B", "50B", "100B", "1T"]
    try: return labels[int(index)]
    except: return "N/A"

# def calculate_cloud_costs(total_tokens, input_pct, output_pct, models_data):
#     """
#     models_data: List of dicts {name, input_price, output_price, weight}
#     """
#     # 1. Normalize Model Mix
#     total_weight = sum(m['weight'] for m in models_data)
#     if total_weight == 0:
#         return 0, 0, []

#     results = []
#     grand_total_cost = 0

#     for m in models_data:
#         norm_pct = m['weight'] / total_weight
#         model_tokens = total_tokens * norm_pct
        
#         in_tokens = model_tokens * (input_pct / 100)
#         out_tokens = model_tokens * (output_pct / 100)
        
#         in_cost = (in_tokens / 1_000_000) * m['input_price']
#         out_cost = (out_tokens / 1_000_000) * m['output_price']
#         model_cost = in_cost + out_cost
        
#         grand_total_cost += model_cost
#         results.append({
#             "name": m['name'],
#             "cost": model_cost,
#             "pct_of_total": 0 # Calculated after loop
#         })

#     # Calculate percentages for the breakdown
#     for r in results:
#         if grand_total_cost > 0:
#             r['pct_of_total'] = (r['cost'] / grand_total_cost) * 100

#     avg_cpm = (grand_total_cost / total_tokens) * 1_000_000 if total_tokens > 0 else 0
    
#     return grand_total_cost, avg_cpm, results