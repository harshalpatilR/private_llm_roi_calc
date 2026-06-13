import re

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

# Update in calculations.py
# GL calculations
# [365,25 (days) * 24 (hours)] / 12 (months)] = 730,50 Hours/Month

def calculate_required_gpus(model_instances, private_llm_benchmarks, precision, gpu_type):
    """Calculates total GPUs required based on model instance counts."""
    prec_suffix = "16" if "16" in precision else "8"
    tp_col = f"{gpu_type}_tp_{prec_suffix}"
    
    total_gpus = 0
    for i, model in enumerate(private_llm_benchmarks):
        instances = model_instances[i]
        if instances > 0:
            tp_val = float(model.get(tp_col, 0))
            total_gpus += (instances * tp_val)
            # --- START CHANGE 20001: DEBUG LOGGING ---
            if DEBUG_MODE:
                print(f"  > Model {model.get('model')}: {instances} instances * {tp_val} TP = {instances * tp_val} GPUs")
            # --- END CHANGE 20001 ---
    
    # --- START CHANGE 20002: TOTAL DEBUG LOGGING ---
    if DEBUG_MODE:
        print(f"  >> Total Required GPUs for {gpu_type}: {total_gpus}")
    # --- END CHANGE 20002 ---
    
    return total_gpus


# # --- START OF GREENLAKE CALCULATION ENGINE ---
# def calculate_greenlake_metrics(tshirt_row, committed_pct, 
#                                gpu_commit_rate, gpu_burst_rate, 
#                                storage_commit_rate, total_monthly_tokens_million=0):

# --- START CHANGE 26001: FULL REFINED GREENLAKE ENGINE ---
def calculate_greenlake_metrics(tshirt_row, model_instances, committed_pct, 
                               gpu_commit_rate, gpu_burst_rate, 
                               storage_commit_rate, storage_burst_rate,
                               precision, private_llm_benchmarks, total_monthly_tokens_million=0):
    """
    Full GreenLake metric engine. Derives required GPU capacity dynamically
    from model_instances and global PRIVATE_LLMS model data.
    """
    if DEBUG_MODE:
        print(f"\n--- DEBUG: GL CALC START | Instances: {model_instances} ---")

    # 1. Hardware Base
    gpu_info = tshirt_row.get("GPU Type / Qty", "2x Unknown")
    gpu_qty = float(gpu_info.split('x')[0])
    gpu_type = "rtx" if "RTX" in gpu_info else "h200"
    
    # 2. Derive GPU requirements using global PRIVATE_LLMS
    # Matches index of model_instances to index of PRIVATE_LLMS
    prec_str = str(precision)
    prec_suffix = "16" if "16" in prec_str else "8"
    tp_col = f"{gpu_type}_tp_{prec_suffix}"
    
    required_gpus = 0
    for idx, instances in enumerate(model_instances):
        if instances > 0 and idx < len(private_llm_benchmarks):
            tp_val = float(private_llm_benchmarks[idx].get(tp_col, 1))
            required_gpus += (instances * tp_val)
            if DEBUG_MODE:
                print(f"  > Model {private_llm_benchmarks[idx]['model']}: {instances} inst * {tp_val} TP = {instances*tp_val} GPUs")
            
    # 3. Consumption Logic
    committed_baseline = gpu_qty * (float(committed_pct) / 100.0)
    billable_gpus = min(max(required_gpus, committed_baseline), gpu_qty)
    
    if DEBUG_MODE:
        print(f"  > Required GPUs: {required_gpus} | Committed Baseline: {committed_baseline} | Billable: {billable_gpus}")

    # 4. Financial Calculation (B = 730.5 hours/month)
    hours = 730.5
    committed_gpu_hours = committed_baseline * hours
    burst_gpu_hours = max(0, (billable_gpus - committed_baseline) * hours)
    
    total_gpu_cost = (committed_gpu_hours * float(gpu_commit_rate)) + (burst_gpu_hours * float(gpu_burst_rate))
    
    # Storage Calculation
    storage_info = tshirt_row.get("Storage", "20 TB")
    match = re.search(r"(\d+(\.\d+)?)", storage_info)
    storage_val = float(match.group(1)) if match else 0.0

    # Apply TB conversion
    if "TB" in storage_info.upper():
        storage_gb = storage_val * 1000.0
    else:
        storage_gb = storage_val

    if DEBUG_MODE:
        print(f"DEBUG: Storage Parsing | Raw: '{storage_info}' | Extracted: {storage_val} | Final GB: {storage_gb}")

    #storage_gb = float(storage_info.replace("TB", "").strip()) * 1000.0 if "TB" in storage_info else float(storage_info.replace("GB", "").strip())
    billable_storage_gb = storage_gb * (float(committed_pct) / 100.0)
    total_storage_cost = billable_storage_gb * float(storage_commit_rate)
    
    total_monthly_gl_cost = total_gpu_cost + total_storage_cost
    
    # CPM
    tokens_m = float(total_monthly_tokens_million) if total_monthly_tokens_million else 0.0
    # tokens million is per day
    gl_cost_per_million_tokens = (total_monthly_gl_cost / (tokens_m * 365/12)) if tokens_m > 0 else 0.0
    
    # --- START DEBUG: CPM DERIVATION ---
    if DEBUG_MODE:
        print(f"DEBUG: CPM Calc | Total Cost: ${total_monthly_gl_cost:,.2f} | Tokens (M): {tokens_m:,.2f} | CPM: ${gl_cost_per_million_tokens:,.4f}")

    if DEBUG_MODE:
        print(f"--- DEBUG: GL CALC END | Total Cost: ${total_monthly_gl_cost:,.2f} ---\n")

    return {
        "required_gpus": round(required_gpus, 1), # ADD THIS
        "gpus_used": round(committed_baseline, 1), # make it Committed GPUs always
        #"gpus_used": round(billable_gpus, 1),
        "storage_tb_used": round(storage_gb / 1000.0, 1),
        "billable_storage_tb": round(billable_storage_gb / 1000.0, 1),
        "total_gpu_hours": round((billable_gpus * hours), 2),
        "committed_gpu_hours": round(committed_gpu_hours, 2),
        "burst_gpu_hours": round(burst_gpu_hours, 2),
        "total_gpu_cost": round(total_gpu_cost, 2),
        "total_storage_cost": round(total_storage_cost, 2),
        "total_monthly_gl_cost": round(total_monthly_gl_cost, 2),
        "gl_cost_per_million_tokens": round(gl_cost_per_million_tokens, 4)
    }
# --- END CHANGE 26001 ---

# # --- START OF GREENLAKE CALCULATION ENGINE ---
# def calculate_greenlake_metrics(tshirt_row, committed_pct, 
#                                gpu_commit_rate, gpu_burst_rate, 
#                                storage_commit_rate, total_monthly_tokens_million=0):
#     """
#     Calculates GreenLake monthly operating costs and token efficiency profiles.
    
#     Operational Rules (Per HPE Global Sizing Guidelines):
#     - Constant B = 730.5 Hours/Month (Based on 365.25 days/year standard)
#     - Storage Cost = Total Base GB * (Commit % / 100) * Storage Commit Rate
#     - Storage never enters burst states (no burst rate applied on delta)
#     """
#     try:
#         # Extract physical hardware allocations from the selected T-Shirt dictionary block
#         gpu_info = tshirt_row.get("GPU Type / Qty", "2x Unknown")
#         try:
#             gpus = float(gpu_info.split('x')[0])
#         except:
#             gpus = 2.0 # Developer fallback safety

#         # Handle text metrics parsing from storage data rows (e.g. "20 TB" -> 20000 GB)
#         storage_info = tshirt_row.get("Storage", "20 TB")
#         try:
#             if "TB" in storage_info:
#                 storage_gb = float(storage_info.replace("TB", "").strip()) * 1000.0
#             else:
#                 storage_gb = float(storage_info.replace("GB", "").strip())
#         except:
#             storage_gb = 20000.0 # Developer profile base fallback

#         commit_multiplier = (float(committed_pct) if committed_pct else 80.0) / 100.0
        
#         g_commit = float(gpu_commit_rate) if gpu_commit_rate else 0.0
#         g_burst = float(gpu_burst_rate) if gpu_burst_rate else g_commit
#         s_commit = float(storage_commit_rate) if storage_commit_rate else 0.0
        
#         # GPU Monthly Operating Calculus (B = 730.5)
#         hours_per_month = 730.5
#         total_gpu_hours = gpus * hours_per_month
#         committed_gpu_hours = total_gpu_hours * commit_multiplier
#         burst_gpu_hours = total_gpu_hours - committed_gpu_hours
        
#         # Financial Math Execution Layer
#         total_gpu_cost = (committed_gpu_hours * g_commit) + (burst_gpu_hours * g_burst)
        
#         # REFINED: Storage footprint restricted cleanly to committed capacity scaling
#         billable_storage_gb = storage_gb * commit_multiplier
#         total_storage_cost = billable_storage_gb * s_commit
        
#         total_monthly_gl_cost = total_gpu_cost + total_storage_cost
        
#         # Map cost per million if tokens flow natively
#         tokens_m = float(total_monthly_tokens_million) if total_monthly_tokens_million else 0.0
#         gl_cost_per_million_tokens = (total_monthly_gl_cost / tokens_m) if tokens_m > 0 else 0.0
            
#         return {
#             "gpus_used": int(gpus),
#             "storage_tb_used": round(storage_gb / 1000.0, 1),
#             "billable_storage_tb": round(billable_storage_gb / 1000.0, 1),
#             "total_gpu_hours": round(total_gpu_hours, 2),
#             "committed_gpu_hours": round(committed_gpu_hours, 2),
#             "burst_gpu_hours": round(burst_gpu_hours, 2),
#             "total_gpu_cost": round(total_gpu_cost, 2),
#             "total_storage_cost": round(total_storage_cost, 2),
#             "total_monthly_gl_cost": round(total_monthly_gl_cost, 2),
#             "gl_cost_per_million_tokens": round(gl_cost_per_million_tokens, 4)
#         }
#     except Exception:
#         return {
#             "gpus_used": 2, "storage_tb_used": 20.0, "billable_storage_tb": 16.0,
#             "total_gpu_hours": 1461.0, "committed_gpu_hours": 1168.8, "burst_gpu_hours": 292.2,
#             "total_gpu_cost": 0.0, "total_storage_cost": 0.0, "total_monthly_gl_cost": 0.0,
#             "gl_cost_per_million_tokens": 0.0
#         }
# # --- END OF GREENLAKE CALCULATION ENGINE ---

