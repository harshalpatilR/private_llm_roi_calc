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


# --- START CHANGE 16001: DEBUGGABLE PCAI MATH ---

# Global toggle for console debugging
DEBUG_MODE = True 

def calculate_pcai_costs(tshirt_data, model_instances, precision, hours, days, capex_price, capex_years, private_llm_benchmarks):
    if DEBUG_MODE:
        print("\n--- DEBUG: PCAI CALCULATION START ---")
        print(f"Input: T-Shirt={tshirt_data.get('size_name')}, Precision={precision}")
        print(f"Time: {hours}hrs/day, {days}days/yr | Capex: ${capex_price} over {capex_years}yrs")

    # 1. Parse T-Shirt GPU info
    gpu_info = tshirt_data.get("GPU Type / Qty", "0x Unknown")
    try:
        gpu_qty = int(gpu_info.split('x')[0])
        gpu_type = "rtx" if "RTX" in gpu_info else "h200"
    except:
        gpu_qty = 0
        gpu_type = "rtx"

    prec_suffix = "16" if "16" in precision else "8"
    tps_col = f"{gpu_type}_tps_{prec_suffix}"
    tp_col = f"{gpu_type}_tp_{prec_suffix}"

    if DEBUG_MODE:
        print(f"Logic: Selected GPU={gpu_type.upper()}, Target Columns=[{tps_col}, {tp_col}]")

    total_tps = 0
    total_gpus_used = 0
    breakdown = []

    for i, model in enumerate(private_llm_benchmarks):
        instances = model_instances[i]
        if instances > 0:
            tp_val = float(model.get(tp_col, 0))
            tps_val = float(model.get(tps_col, 0))
            
            m_gpus = instances * tp_val
            # throughput = tokens per GPU-second * total GPUs assigned to this model type
            m_tps = m_gpus * tps_val 
            
            total_tps += m_tps
            total_gpus_used += m_gpus
            
            if DEBUG_MODE:
                print(f"Model [{model['model']}]: {instances} inst * {tp_val} TP = {m_gpus} GPUs | TPS: {m_tps:,.0f}")

            breakdown.append({
                "name": model['model'],
                "instances": instances,
                "tp": tp_val,
                "tps_per_gpu": tps_val,
                "total_gpus": m_gpus,
                "total_tps": m_tps,
                "gpu_type": gpu_info.split(' ')[-1]
            })

    # Token Math
    tokens_per_hour = total_tps * 3600
    tokens_per_day = tokens_per_hour * hours
    total_tokens_annual = tokens_per_day * days
    
    # Cost Math
    total_days = (capex_years * days) if capex_years > 0 else 1
    price_per_day = capex_price / total_days if total_days > 0 else 0
    cpm = (price_per_day / (tokens_per_day / 1e6)) if tokens_per_day > 0 else 0
    
    if DEBUG_MODE:
        print(f"Results: Total Tokens/Day={tokens_per_day:,.0f} | Total GPUs Used={total_gpus_used}/{gpu_qty}")
        print(f"Financials: Price/Day=${price_per_day:,.2f} | CPM=${cpm:,.4f}")
        print("--- DEBUG: PCAI CALCULATION END ---\n")

    error_msg = ""
    if total_gpus_used > gpu_qty:
        error_msg = f"⚠️ Over-provisioned: Using {total_gpus_used} GPUs but system only has {gpu_qty}."

    return total_tokens_annual, cpm, breakdown, error_msg, total_gpus_used, gpu_qty

# --- END CHANGE 16001 ---


def format_large_number(num):
    """Formats large numbers into K, M, or B suffixes for the UI."""
    if num >= 1_000_000_000:
        return f"{num / 1_000_000_000:.1f}B"
    if num >= 1_000_000:
        return f"{num / 1_000_000:.1f}M"
    if num >= 1_000:
        return f"{num / 1_000:.1f}K"
    return str(int(num))

