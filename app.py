import gradio as gr
import base64
import csv
from modules.calculations import calculate_cloud_costs, format_token_label, calculate_pcai_costs, format_large_number, calculate_greenlake_metrics
from ui.styling import HPE_COLORS, CUSTOM_CSS, get_theme
import pandas as pd 


# GLOBALS for passing values
GLOBAL_TOKENS_PER_DAY = 0
GLOBAL_FINAL_RESULTS_REGISTRY = {
    "public_cloud": {"tokens": 0, "cost": 0, "cpm": 0, "gpus_used": 0, "total_gpus": 0, "commit_gpus": 0 },
    "pcai_capex": {"tokens": 0, "cost": 0, "cpm": 0, "gpus_used": 0, "total_gpus": 0, "commit_gpus": 0 },
    "pcai_greenlake": {"tokens": 0, "cost": 0, "cpm": 0, "gpus_used": 0, "total_gpus": 0, "commit_gpus": 0 }
}

# --- START CHANGE 4001: CSV DATA LOADER ---
def load_models_from_csv(filepath="public_models.csv"):
    models = []
    try:
        with open(filepath, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, skipinitialspace=True)

            for row in reader:
                print(row)
                models.append({
                    "name": row['name'],
                    "in": float(row['in']),
                    "out": float(row['out']),
                    "weight": int(row['weight'])
                })
    except FileNotFoundError:
        # Fallback to empty list if file is missing
        return []
    return models

DEFAULT_MODELS = load_models_from_csv()


# --- START CHANGE 15001: PCAI UI & DATA LOADERS ---
def load_tshirts(filepath="t-shirts.csv"):
    try:
        with open(filepath, mode='r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            header = next(reader) # Feature, Dev, Small...
            rows = list(reader)
            
            tshirts = []
            for col_idx in range(1, len(header)):
                ts = {"size_name": header[col_idx]}
                for row in rows:
                    ts[row[0]] = row[col_idx]
                print(ts)
                tshirts.append(ts)
            return tshirts
    except: return []

# --- START CHANGE 27001: FIX CONSUMED ITERATOR ---

def load_private_llms(filepath="private-llm.csv"):
    try:
        with open(filepath, mode='r', encoding='utf-8-sig') as f:
            # 1. Convert to a list immediately and store it
            all_rows = list(csv.DictReader(f))
            
            # 2. Print from the stored list
            print(all_rows[:6])
            
            # 3. Return from the stored list
            return all_rows[:6]
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        return []

# --- END CHANGE 27001 ---

TSHIRTS = load_tshirts()
PRIVATE_LLMS = load_private_llms()


# Unchanged top line reference:
# DEFAULT_MODELS = load_models_from_csv()

# Unchanged top line reference from your app.py:
# LOGO_DATA = get_base64_img("./images/hpe-element-color.png")

# --- START OF GREENLAKE INCREMENTAL UI CONTROLLER PATCH ---
#from modules.calculations import calculate_greenlake_metrics

def update_greenlake_ui(*args):
    # args mapping:
    # gl_hidden_tshirt_idx (1) + gl_hidden_model_sliders (6) + gl_committed_pct (1) + 4 rates (4) = 12 total

    global GLOBAL_TOKENS_PER_DAY
    global GLOBAL_FINAL_RESULTS_REGISTRY

    if len(args) < 6:
        return "$0.0000", "<p style='color:#6B8099;'>Waiting for data...</p>"

    try:
        # 1. Fixed parameters
        selected_idx = int(args[0])
        committed_pct = args[1]
        gpu_commit_rate = args[2]
        gpu_burst_rate = args[3]
        storage_commit_rate = args[4]
        storage_burst_rate = args[5]
        precision    = args[6] ## added
        
        # 2. Variable model instances (The last 6 items)
        model_instances = list(args[7:]) 
        
    except Exception as e:
        print(f"DEBUG: GreenLake Init Error: {e}")
        return "$0.0000", f"<p style='color:red;'>Init Error: {e}</p>"

    # Safe T-Shirt data context resolution
    if 0 <= selected_idx < len(TSHIRTS):
        target_ts = TSHIRTS[selected_idx]
    else:
        return "$0.0000", "<p style='color:#6B8099;'>Please select an active platform node</p>"

    # Capture token velocity dynamically based on model parameter sliders
    # Mirrors the exact backend parsing order used in calculate_pcai_costs
    total_tps = 0
    gpu_info = target_ts.get("GPU Type / Qty", "0x Unknown")
    gpu_type = "rtx" if "RTX" in gpu_info else "h200"
    tps_col = f"{gpu_type}_tps_16" # Baseline context lookup

    for idx, model in enumerate(PRIVATE_LLMS):
        if idx < len(model_instances):
            instances = model_instances[idx]
            if instances > 0:
                tp_val = float(model.get(f"{gpu_type}_tp_16", 1))
                tps_val = float(model.get(tps_col, 0))
                total_tps += (instances * tp_val) * tps_val

    # Convert operational TPS to true monthly transaction volume (30.4375 days average scale)
    tokens_per_month_million = GLOBAL_TOKENS_PER_DAY


    #(total_tps * 3600 * 24 * 30.4375) / 1e6

    # # Execute financial calculations via our specialized metrics core
    # gl_data = calculate_greenlake_metrics(
    #     tshirt_row=target_ts,
    #     committed_pct=committed_pct,
    #     gpu_commit_rate=gpu_commit_rate,
    #     gpu_burst_rate=gpu_burst_rate,
    #     storage_commit_rate=storage_commit_rate,
    #     total_monthly_tokens_million=tokens_per_month_million
    # )

    gl_data = calculate_greenlake_metrics(
        tshirt_row=target_ts,
        model_instances=model_instances,
        committed_pct=committed_pct,
        gpu_commit_rate=gpu_commit_rate,
        gpu_burst_rate=gpu_burst_rate,
        storage_commit_rate=storage_commit_rate,
        storage_burst_rate=storage_burst_rate, # Ensure your signature matches
        precision=precision,                   # INJECTED PATCH
        private_llm_benchmarks=PRIVATE_LLMS, # <--- Add this
        total_monthly_tokens_million=(GLOBAL_TOKENS_PER_DAY/1e6)
    )

    #cpm_str = f"${gl_data['gl_cost_per_million_tokens']:,.4f} <span class='unit-text'>/ M tokens</span>"
    #cpm_str = f"<div class='green-text'>${gl_data['gl_cost_per_million_tokens']:,.2f} <span class='unit-text'>/ M tokens</span></div>"
    cpm_str = f"${gl_data['gl_cost_per_million_tokens']:,.2f} <span class='unit-text'>/ M tokens</span>"

    total_gpus_pcai_ui = GLOBAL_FINAL_RESULTS_REGISTRY["pcai_greenlake"]["total_gpus"]

    GLOBAL_FINAL_RESULTS_REGISTRY["pcai_greenlake"] = {
            "tokens": tokens_per_month_million * 365/12, # the value is tokens per day
            "cost": gl_data['total_gpu_cost'] + gl_data['total_storage_cost'], # monthly cost
            "cpm": gl_data['gl_cost_per_million_tokens'],
            #"gpus_used": gl_data['required_gpus'], #take from pcai_ui workload
            #"total_gpus": 0, #take from pcai_ui workload
            "commit_gpus": gl_data['gpus_used']
        }


    # Formulate interactive layout template matrix
    breakdown_html = f"""
    <div style="overflow-x: auto; width: 100%;">
        <table style="width:100%; font-size:0.85rem; border-collapse:collapse; color: white; background-color: #1A2744; border-radius: 4px;">
            <thead>
                <tr style="border-bottom:2px solid #01A982; text-align:left;">
                    <th style="padding:10px 8px; background-color: #1A2744; color: #01A982; font-weight:600; white-space: nowrap;">Allocated Resource Parameter</th>
                    <th style="padding:10px 8px; background-color: #1A2744; color: #01A982; font-weight:600; text-align:right; white-space: nowrap;">Calculated Configuration Value</th>
                </tr>
            </thead>
            <tbody>
                <tr style="border-bottom: 1px solid #2A3F5C;">
                    <td style="padding:8px 10px; background-color: #1A2744; color: #CCD2D8; white-space: nowrap;">Required Compute Capacity</td>
                    <td style="padding:8px 10px; background-color: #1A2744; text-align:right; color: white;">{gl_data['required_gpus']} GPUs</td>
                </tr>
                <tr style="border-bottom: 1px solid #2A3F5C;">
                    <td style="padding:8px 10px; background-color: #1A2744; color: #CCD2D8; white-space: nowrap;">Physical Compute Footprint</td>
                    <td style="padding:8px 10px; background-color: #1A2744; text-align:right; color: white;">{gl_data['gpus_used']} GPUs</td>
                </tr>
                <tr style="border-bottom: 1px solid #2A3F5C;">
                    <td style="padding:8px 10px; background-color: #1A2744; color: #CCD2D8; white-space: nowrap;">Total Monthly Allocated GPU-Hours</td>
                    <td style="padding:8px 10px; background-color: #1A2744; text-align:right; color: white;">{gl_data['total_gpu_hours']:,} Hours</td>
                </tr>
                <tr style="border-bottom: 1px solid #2A3F5C;">
                    <td style="padding:8px 10px; background-color: #1A2744; color: #CCD2D8; white-space: nowrap;">Committed Volume GPU-Hours ({committed_pct}%)</td>
                    <td style="padding:8px 10px; background-color: #1A2744; text-align:right; color: white;">{gl_data['committed_gpu_hours']:,} Hours</td>
                </tr>
                <tr style="border-bottom: 1px solid #2A3F5C;">
                    <td style="padding:8px 10px; background-color: #1A2744; color: #CCD2D8; white-space: nowrap;">Burst Volume GPU-Hours</td>
                    <td style="padding:8px 10px; background-color: #1A2744; text-align:right; color: white;">{gl_data['burst_gpu_hours']:,} Hours</td>
                </tr>
                <tr style="border-bottom: 1px solid #2A3F5C;">
                    <td style="padding:8px 10px; background-color: #1A2744; color: #CCD2D8; white-space: nowrap;">Committed Storage Footprint ({committed_pct}%)</td>
                    <td style="padding:8px 10px; background-color: #1A2744; text-align:right; color: white;">{gl_data['billable_storage_tb']} TB / {gl_data['storage_tb_used']} TB Total</td>
                </tr>
                <tr style="border-bottom: 1px solid #2A3F5C;">
                    <td style="padding:8px 10px; background-color: #1A2744; color: #CCD2D8; white-space: nowrap;">Calculated Total GPU Cost / Month</td>
                    <td style="padding:8px 10px; background-color: #1A2744; text-align:right; color: white;">${gl_data['total_gpu_cost']:,}</td>
                </tr>
                <tr style="border-bottom: 1px solid #2A3F5C;">
                    <td style="padding:8px 10px; background-color: #1A2744; color: #CCD2D8; white-space: nowrap;">Calculated Storage Cost / Month (No Burst)</td>
                    <td style="padding:8px 10px; background-color: #1A2744; text-align:right; color: white;">${gl_data['total_storage_cost']:,}</td>
                </tr>
                <tr style="border-bottom: 2px solid #01A982; background: rgba(1, 169, 130, 0.1);">
                    <td style="padding:10px 8px; background-color: #1E2E45; font-weight:600; color: #01A982; white-space: nowrap;">Total GreenLake System Charge / Month</td>
                    <td style="padding:10px 8px; background-color: #1E2E45; text-align:right; color: #01A982; font-weight: 700;">${gl_data['total_monthly_gl_cost']:,}</td>
                </tr>
            </tbody>
        </table>
    </div>
    """
    return cpm_str, breakdown_html
# --- END OF GREENLAKE INCREMENTAL UI CONTROLLER PATCH ---

# Unchanged line following the insertion point:
# with gr.Blocks() as demo:



# Unchanged bottom line reference:
# with gr.Blocks(theme=get_theme(), css=CUSTOM_CSS) as demo:


# --- START CHANGE 34001: RESTORED HTML FORMATTING ---

def update_pcai_ui(*args):
    """
    Inputs: [selected_tshirt_idx (int), precision_radio, work_hours, work_days, 
             capex_price, capex_years] + pcai_model_sliders
    """
    global GLOBAL_TOKENS_PER_DAY
    global GLOBAL_FINAL_RESULTS_REGISTRY

    try:
        # 1. Unpack Fixed Positions (Index 0-5)
        # Using the index from the button click logic
        selected_idx = int(args[0])  
        precision    = args[1]
        work_hours   = args[2] 
        work_days    = args[3]
        capex_val    = args[4]
        capex_years  = args[5]
        
        # 2. Unpack Variable Positions (Index 6 onwards)
        model_instances = list(args[6:])
    except (ValueError, IndexError, TypeError):
        return "Initialization Error", "$0.00", "", ""

    # 3. Direct Data Lookup from TSHIRTS
    if 0 <= selected_idx < len(TSHIRTS):
        target_ts = TSHIRTS[selected_idx]
    else:
        return "Select System", "$0.00", "", ""

    # 4. Perform Calculation using imported calculate.py function
    # Return order: total_tokens_annual, cpm, breakdown, error_msg, used_gpu, avail_gpu
    # results = calculate_pcai_costs(
    #     target_ts, model_instances, precision, work_hours, work_days, 
    #     capex_val, capex_years, PRIVATE_LLMS
    # )
    
    # fixed 24 hours and 365 days
    results = calculate_pcai_costs(
    target_ts, model_instances, precision, 24, 365, 
    capex_val, capex_years, PRIVATE_LLMS)

    total_tokens_annual, cpm, breakdown, error_msg, used_gpu, avail_gpu = results


    # 5. Format Metric Strings
    # Calculate tokens_per_day specifically for the primary UI display
    total_tps = sum(b['total_tps'] for b in breakdown)
    tokens_per_day = total_tps * 3600 * work_hours
    
    token_str = format_large_number(tokens_per_day)
    token_str = f"{format_large_number(tokens_per_day)} <span class='unit-text'>tokens per day</span>"
    
    #cpm_str = f"${cpm:,.2f} / M tokens"

    # assign global
    GLOBAL_TOKENS_PER_DAY = tokens_per_day
    GLOBAL_FINAL_RESULTS_REGISTRY["pcai_capex"] = {
    "tokens": tokens_per_day * 365/12,  # tokens per month
    "cost": (capex_val / (capex_years * 12)), # amortized cost per month
    "cpm": cpm,
    "gpus_used": used_gpu, 
    "total_gpus": avail_gpu, 
    "commit_gpus": 0 
    }

    # assign gpu workload in greenlake also
    GLOBAL_FINAL_RESULTS_REGISTRY["pcai_greenlake"] = {
    "gpus_used": used_gpu, 
    "total_gpus": avail_gpu, 
    }
    cpm_str = f"${cpm:,.2f} <span class='unit-text'>/ M tokens</span>"
    
    #formatted_tokens = format_large_number(tokens_per_day)
    #token_str = f"<div class='stat-card'>{formatted_tokens}</div>"

    #cpm_str = f"<div class='green-text'>${cpm:,.2f} <span class='unit-text'>/ M tokens</span></div>"

    # 6. Generate Visual Breakdown HTML
    breakdown_html = "<div style='display: flex; flex-direction: column; gap: 12px;'>"
    for b in breakdown:
        pct = (b['total_gpus'] / used_gpu * 100) if used_gpu > 0 else 0
        m_tokens_day = b['total_tps'] * 3600 * work_hours
        
        breakdown_html += f"""
            <div style='margin-bottom: 4px;'>
                <div style='display:flex; justify-content:space-between; font-size: 0.85rem; color: white; margin-bottom: 4px;'>
                    <span style='font-weight: 500;'>{b['name']} ({int(b['instances'])} inst)</span>
                    <span style='color: #6B8099;'>{format_large_number(m_tokens_day)} tokens/day</span>
                </div>
                <div style='background: #2A3F5C; width: 100%; height: 8px; border-radius: 4px;'>
                    <div style='background: #01A982; width: {pct}%; height: 100%; border-radius: 4px;'></div>
                </div>
            </div>
        """
    breakdown_html += "</div>"

    # 7. Sizing Details Table (Right-Justified & Proper English)
    table_html = f"<div style='color:#FF4B4B; margin-bottom:10px; font-weight:bold;'>{error_msg}</div>" if error_msg else ""
    table_html += """<table style='width:100%; font-size:0.85rem; border-collapse:collapse; color: white;'>
        <thead>
            <tr style='border-bottom:2px solid #01A982; text-align:left;'>
                <th style='padding:10px 5px;'>Model Name</th>
                <th style='padding:10px 5px; text-align:right;'>Tensor Parallel</th>
                <th style='padding:10px 5px; text-align:right;'>Model Instances</th>
                <th style='padding:10px 5px; text-align:right;'>GPU(s) Used</th>
                <th style='padding:10px 5px; text-align:right;'>Tokens Per Second</th>
            </tr>
        </thead>
        <tbody>"""
    
    for b in breakdown:
        table_html += f"""
            <tr style='border-bottom: 1px solid #2A3F5C;'>
                <td style='padding:8px 5px;'>{str(b['name']).title()}</td>
                <td style='padding:8px 5px; text-align:right;'>{b['tp']:.1f}</td>
                <td style='padding:8px 5px; text-align:right;'>{int(b['instances']):.1f}</td>
                <td style='padding:8px 5px; text-align:right;'>{b['total_gpus']:.1f}</td>
                <td style='padding:8px 5px; text-align:right;'>{b['total_tps']:,.0f}</td>
            </tr>"""
            
    table_html += f"""
        </tbody>
        <tfoot>
            <tr style='background: rgba(1, 169, 130, 0.1); font-weight: bold;'>
                <td style='padding:10px 5px;'>Total System</td>
                <td style='padding:10px 5px; text-align:right;'>-</td>
                <td style='padding:10px 5px; text-align:right;'>-</td>
                <td style='padding:10px 5px; text-align:right;'>{used_gpu:.1f} / {avail_gpu:.1f}</td>
                <td style='padding:10px 5px; text-align:right;'>{total_tps:,.0f}</td>
            </tr>
        </tfoot>
    </table>"""


    return token_str, cpm_str, breakdown_html, table_html

# ---

def get_base64_img(path):
    try:
        with open(path, "rb") as f:
            data = base64.b64encode(f.read()).decode("utf-8")
        return f"data:image/png;base64,{data}"
    except:
        return "" # Returns empty if file missing

# Convert your logo to a string once at startup
LOGO_DATA = get_base64_img("./images/hpe-element-color.png")

# --- CHANGE 1: ADD LABELS TO MATCH STEPS ---
TOKEN_STEPS = [1e7, 5e7, 1e8, 5e8, 1e9, 5e9, 1e10, 5e10, 1e11, 1e12]
TOKEN_LABELS = ["10M", "50M", "100M", "500M", "1B", "5B", "10B", "50B", "100B", "1T"]

def update_ui(*args):
    global GLOBAL_FINAL_RESULTS_REGISTRY

# Safety check: if inputs are missing, return default strings
    if args[0] is None:
        return "$0", "$0.00 / M tokens", "", ""

    total_tokens = args[0]
    in_pct = args[1]
    out_pct = args[2]
    
    # Reconstruct model list from variable args
    # Index 3 onwards contains the weights and then the prices
    models = []
    idx = 3
    for i, m in enumerate(DEFAULT_MODELS):
        models.append({
            "name": m['name'],
            "weight": args[idx + i],
            "input_price": args[idx + 6 + (i * 2)], 
            "output_price": args[idx + 6 + (i * 2) + 1]
        })


    total_cost, cpm, breakdown = calculate_cloud_costs(total_tokens, in_pct, out_pct, models)
    
    # update for summary tab3
    GLOBAL_FINAL_RESULTS_REGISTRY["public_cloud"] = {
        "tokens": total_tokens, 
        "cost": total_cost, 
        "cpm": cpm
    }

    # Format labels
    cost_str = f"${total_cost:,.0f}"
    #cpm_str = f"${cpm:,.2f} / M tokens"
    cpm_str = f"${cpm:,.2f} <span class='unit-text'>/ M tokens</span>"

    # LOOP 1: Generates the "Cost Breakdown by Model" visual bars (Side Column)
    # Generate simple HTML breakdown
    html_breakdown = "<div style='display: flex; flex-direction: column; gap: 10px;'>"

    for b in breakdown:
        if b['weight'] > 0:
            html_breakdown += f"""
            <div>
                <div style='display:flex; justify-content:space-between; font-size: 0.9rem;'>
                    <span>{b['name']}</span><span>${b['model_total_cost']:,.2f}</span>
                </div>
                <div style='background: #2A3F5C; width: 100%; height: 8px; border-radius: 4px;'>
                    <div style='background: {HPE_COLORS['green']}; width: {b['pct_of_total_spend']}%; height: 100%; border-radius: 4px;'></div>
                </div>
            </div>
            """
    html_breakdown += "</div>"

    # LOOP 2: Generates the "Detailed Calculation Breakdown" itemized table (Accordion)
    # Generate Detailed Table
    table_html = """
    <div style='overflow-x: auto;'>
        <table style='width: 100%; border-collapse: collapse; text-align: left;'>
            <thead>
                <tr style='border-bottom: 2px solid #01A982;'>
                    <th style='padding: 8px; font-weight: 600;'>Model</th>
                    <th style='padding: 8px; font-weight: 600; text-align: right;'>Mix %</th>
                    <th style='padding: 8px; font-weight: 600; text-align: right;'>In Tokens</th>
                    <th style='padding: 8px; font-weight: 600; text-align: right;'>Out Tokens</th>
                    <th style='padding: 8px; font-weight: 600; text-align: right;'>In $/M</th>
                    <th style='padding: 8px; font-weight: 600; text-align: right;'>Out $/M</th>
                    <th style='padding: 8px; font-weight: 600; text-align: right;'>Total</th>
                </tr>
            </thead>
            <tbody>
    """

    for b in breakdown:
        if b['weight'] > 0:
            table_html += f"""
                <tr style='border-bottom: 1px solid #2A3F5C;'>
                    <td style='padding: 8px;'>{b['name']}</td>
                    <td style='padding: 8px; text-align: right;'>{b['norm_weight']:.1f}%</td>
                    <td style='padding: 8px; text-align: right; color: #CCD2D8;'>{int(b['in_tokens']):,}</td>
                    <td style='padding: 8px; text-align: right; color: #CCD2D8;'>{int(b['out_tokens']):,}</td>
                    <td style='padding: 8px; text-align: right;'>${b['in_price']:.2f}</td>
                    <td style='padding: 8px; text-align: right;'>${b['out_price']:.2f}</td>
                    <td style='padding: 8px; text-align: right; font-weight: 600; color: #01A982;'>${b['model_total_cost']:,.2f}</td>
                </tr>
            """

    table_html += "</tbody></table></div>"
    # --- END CHANGE 1301 ---

    # Return 4 values now including the table string
    return cost_str, cpm_str, html_breakdown, table_html    

### Tab3

# def get_tab3_comparison():
#     global GLOBAL_FINAL_RESULTS_REGISTRY
    
#     # CSS: Matching your GreenLake table style precisely
#     html = """
#     <div style="overflow-x: auto; width: 100%;">
#         <table style="width: 100%; font-size: 16px; border-collapse: collapse; color: white; background-color: #1A2744; border-radius: 4px;">
#             <thead>
#                 <tr style="border-bottom: 2px solid #01A982; text-align: left;">
#                     <th style="padding: 12px; background-color: #1A2744; color: #01A982; font-weight: 600;">Consumption Model</th>
#                     <th style="padding: 12px; background-color: #1A2744; color: #01A982; font-weight: 600; text-align: right;">Monthly Tokens</th>
#                     <th style="padding: 12px; background-color: #1A2744; color: #01A982; font-weight: 600; text-align: right;">Monthly Cost</th>
#                     <th style="padding: 12px; background-color: #1A2744; color: #01A982; font-weight: 600; text-align: right;">CPM</th>
#                 </tr>
#             </thead>
#             <tbody>
#     """
    
#     for key, val in GLOBAL_FINAL_RESULTS_REGISTRY.items():
#         name = key.replace("_", " ").title().replace("Pcai", "PCAI")
#         formatted_tokens = format_large_number(val['tokens'])
#         cpm_str = f"<span style='color: #01A982; font-weight: 700;'>${val['cpm']:,.2f}</span> <span style='font-size: 0.85em; color: #CCD2D8;'>/ M tokens</span>"
        
#         html += f"""
#         <tr style="border-bottom: 1px solid #2A3F5C;">
#             <td style="padding: 12px; background-color: #1A2744; color: white; font-weight: 500;">{name}</td>
#             <td style="padding: 12px; background-color: #1A2744; text-align: right; color: #CCD2D8;">{formatted_tokens}</td>
#             <td style="padding: 12px; background-color: #1A2744; text-align: right; color: white;">${val['cost']:,.0f}</td>
#             <td style="padding: 12px; background-color: #1A2744; text-align: right;">{cpm_str}</td>
#         </tr>
#         """
        
#     html += "</tbody></table></div>"
#     return html


# --- START CHANGE: TAB 3 GPU COLUMNS ---

def get_tab3_comparison():
    global GLOBAL_FINAL_RESULTS_REGISTRY
    
    # 1. Extract reference values
    capex_data = GLOBAL_FINAL_RESULTS_REGISTRY.get("pcai_capex", {})
    ref_used = capex_data.get('gpus_used', 0)
    ref_total = capex_data.get('total_gpus', 0)
    
    greenlake_data = GLOBAL_FINAL_RESULTS_REGISTRY.get("pcai_greenlake", {})
    gl_commit = greenlake_data.get('commit_gpus', 0)
    
    html = """
    <div style="overflow-x: auto; width: 100%;">
        <table style="width: 100%; font-size: 16px; border-collapse: collapse; color: white; background-color: #1A2744; border-radius: 4px;">
            <thead>
                <tr style="border-bottom: 2px solid #01A982; text-align: left;">
                    <th style="padding: 12px; background-color: #1A2744; color: #01A982; font-weight: 600;">Consumption Model</th>
                    <th style="padding: 12px; background-color: #1A2744; color: #01A982; font-weight: 600; text-align: right;">Monthly Tokens</th>
                    <th style="padding: 12px; background-color: #1A2744; color: #01A982; font-weight: 600; text-align: right;">Monthly Cost</th>
                    <th style="padding: 12px; background-color: #1A2744; color: #01A982; font-weight: 600; text-align: right;">GPUs (Used/Total)</th>
                    <th style="padding: 12px; background-color: #1A2744; color: #01A982; font-weight: 600; text-align: right;">CPM</th>
                </tr>
            </thead>
            <tbody>
    """
    
    for key, val in GLOBAL_FINAL_RESULTS_REGISTRY.items():
        name = key.replace("_", " ").title().replace("Pcai", "PCAI")
        formatted_tokens = format_large_number(val.get('tokens', 0))
        
        # GPU Column logic
        if key == "public_cloud":
            gpu_str = " - "
        elif key in ["pcai_capex", "pcai_greenlake"]:
            gpu_str = f"{ref_used:.1f} / {ref_total:.1f}"
            if key == "pcai_greenlake":
                # Increased font size for Committed label
                gpu_str += f"<br><span style='font-size: 1.0em; color: #01A982;'>Committed: {gl_commit:.1f}</span>"
        else:
            gpu_str = "-"
            
        # Increased font size for CPM (18px)
        cpm_str = f"<span style='color: #01A982; font-weight: 700; font-size: 18px;'>${val.get('cpm', 0):,.2f}</span> <span style='font-size: 0.9em; color: #CCD2D8;'>/ M tokens</span>"
        
        html += f"""
        <tr style="border-bottom: 1px solid #2A3F5C;">
            <td style="padding: 12px; background-color: #1A2744; color: white; font-weight: 500;">{name}</td>
            <td style="padding: 12px; background-color: #1A2744; text-align: right; color: #CCD2D8;">{formatted_tokens}</td>
            <td style="padding: 12px; background-color: #1A2744; text-align: right; color: white;">${val.get('cost', 0):,.0f}</td>
            <td style="padding: 12px; background-color: #1A2744; text-align: right; color: white;">{gpu_str}</td>
            <td style="padding: 12px; background-color: #1A2744; text-align: right;">{cpm_str}</td>
        </tr>
        """
        
    html += "</tbody></table></div>"
    return html



###### Main UI page


with gr.Blocks() as demo:
    # Header
    with gr.Row(elem_classes="hpe-header"):
        with gr.Column(scale=4):
                gr.HTML(f"""
                    <div style="display: flex; align-items: center; gap: 15px;">
                        <img src="{LOGO_DATA}" style="height: 32px; width: auto; display: block;">
                        <div style="display: flex; flex-direction: column;">
                            <h1 style="color: white; margin: 0; font-size: 1.4rem; font-weight: 600; line-height: 1.2;">
                                HPE | AI Inference Cost Calculator
                            </h1>
                            <p style="color: #6B8099; margin: 0; font-size: 0.9rem; font-weight: 400;">
                                Private Cloud AI • APAC Presales
                            </p>
                        </div>
                    </div>
                """)

            # gr.Image("./images/hpe-element-color.png",
            # show_label=False, 
            # width=100, 
            # container=False,
            # interactive=False,
            # buttons=[]      # Disables the hover menu entirely
            # )
                #gr.Markdown(f"## HPE | AI Inference Cost Calculator\n**Private Cloud AI · APAC Presales**")
    with gr.Column(scale=1):
            gr.Markdown("Internal use only\n**by HPE PCAI Sales Engineering**")

            # refresh on demand
            refresh_btn = gr.Button(
                    "🔄 Update Results", 
                    variant="primary", 
                    elem_id="global-refresh-btn"
                )

    with gr.Tabs():
        with gr.Tab("Cloud API") as cloud_tab:
            with gr.Row():
                # LEFT INPUTS
                with gr.Column(scale=3):
                    gr.Markdown("### 1. Token Volume")
                    # --- CHANGE 2: REPLACE LINEAR SLIDER WITH INDEXED SLIDER ---
                    token_slider = gr.Slider(
                        minimum=0, 
                        maximum=len(TOKEN_STEPS) - 1, 
                        step=1, 
                        value=4, # Default to 1B (index 4)
                        label="Total Tokens (Monthly Scale)", 
                        info="Slide to select volume from 10M to 1T"
                    )
                    # This hidden component will store the actual number (e.g., 1000000000) for the math
                    raw_token_count = gr.Number(value=1e9, visible=False)
                    token_display = gr.Markdown("**Current: 1B Tokens**")
                    
                    gr.Markdown("### 2. Token Type Distribution")
                    with gr.Row():
                        in_pct = gr.Slider(0, 100, 50, label="Input %")
                        out_pct = gr.Slider(0, 100, 50, label="Output %")

                    gr.Markdown("### 3. Model Mix (%)")
                    weight_sliders = []
                    price_inputs = [] # For the "hidden" editors
                    
                    for m in DEFAULT_MODELS:
                        with gr.Row():
                            w = gr.Slider(0, 100, m['weight'], label=m['name'], scale=3)
                            # Hidden price fields for the calculation logic
                            p_in = gr.Number(m['in'], visible=False)
                            p_out = gr.Number(m['out'], visible=False)
                            weight_sliders.append(w)
                            price_inputs.append(p_in)
                            price_inputs.append(p_out)
                    
                    # Manual price overrides (simplified version of the ✏ edit button)
                    with gr.Accordion("Advanced: Edit Unit Pricing ($/M Tokens)", open=False):
                        visible_prices = []
                        for m in DEFAULT_MODELS:
                            with gr.Row():
                                pi = gr.Number(m['in'], label=f"{m['name']} Input")
                                po = gr.Number(m['out'], label=f"{m['name']} Output")
                                visible_prices.extend([pi, po])

                # RIGHT OUTPUTS
                with gr.Column(scale=2):
                    gr.Markdown("### Results")
                    with gr.Group():
                        total_cost_out = gr.Markdown("## $0", elem_classes="stat-card")
                        cpm_out = gr.Markdown("$0.00 / M tokens", elem_classes=["stat-card","green-text"])
                    
                    gr.Markdown("#### Cost Breakdown by Model")
                    breakdown_out = gr.HTML("Select distribution to see breakdown")
                # --- NEW MODIFICATION: ADD EXPANDABLE BREAKDOWN TABLE BELOW BREAKDOWN ---
                    with gr.Accordion("Detailed Calculation Breakdown", open=False, elem_id="calc-accordion"):
                        details_table_out = gr.HTML("<p style='color: #6B8099;'>Adjust parameters to generate itemized ledger.</p>")
            
            # # Trigger update ONLY when this tab is selected/clicked
            #     # 1. Define input/output groups
            # all_inputs = [raw_token_count, in_pct, out_pct] + weight_sliders + visible_prices
            # all_outputs = [total_cost_out, cpm_out, breakdown_out, details_table_out]
            # cloud_tab.select(update_ui, inputs=all_inputs, outputs=all_outputs)

        with gr.Tab("Private Cloud AI") as pcai_tab:
            #gr.Markdown("### PCAI Configurator\n*Section under development*")
        #with gr.Tab("Private Cloud AI") as pcai_tab:
            with gr.Row():
                with gr.Column(scale=3):
                    gr.Markdown("### 1. Select HPE PCAI System")
                    
                    # This hidden component holds the state of which button was clicked
                    selected_tshirt_idx = gr.Number(value=0, visible=False)
                    gl_hidden_tshirt_idx = gr.Number(value=0, visible=False)
                    gl_hidden_precision = gr.Number(value=16, visible=False)
                    tshirt_buttons = []


                    def create_click_handler(idx):
                        def handler():
                            # Generate updates for buttons
                            updates = [gr.update(variant="primary" if i == idx else "secondary") for i in range(len(TSHIRTS))]
                            # Return updates + the raw integer index for the number components
                            return updates + [idx, idx]
                        return handler

                    def on_tshirt_click(idx):
                        """
                        Updates button variants and returns raw index values for hidden Number components.
                        """
                        # 1. Create a list of updates for your buttons (one per T-shirt)
                        # This generates a list like: [gr.update(variant='secondary'), gr.update(variant='primary'), ...]
                        button_updates = [
                            gr.update(variant="primary" if i == idx else "secondary") 
                            for i in range(len(TSHIRTS))
                        ]
                        
                        # 2. Return the button updates + the raw integer index for the two Number components.
                        # IMPORTANT: We do NOT use gr.update() for the Number components.
                        # Just return the integer value directly so Gradio sets the value correctly.
                        return button_updates + [idx, idx]

                    with gr.Row():
                    # Function to update button appearances

                        for idx, ts in enumerate(TSHIRTS):
                            with gr.Column(min_width=150):
                                # Create label from CSV data (image_4fb085.png)
                                btn_label = f"{ts['size_name']}\n{ts.get('GPU Type / Qty', '')}"
                                btn = gr.Button(
                                    btn_label, 
                                    variant="primary" if idx == 0 else "secondary",
                                    elem_classes=["system-tile"]  # Ensure this matches your CSS class name
                                )
                                # When clicked, update the hidden Number component
                                #btn.click(lambda i=idx: i, None, selected_tshirt_idx)
                                tshirt_buttons.append(btn)
                                
                                # Set up clicks to trigger the visual update
                                for idx, btn in enumerate(tshirt_buttons):
                                    btn.click(
                                        fn=create_click_handler(idx),
                                        inputs=None, # gr.State(idx) Pass the index of the clicked button
                                        outputs=tshirt_buttons + [selected_tshirt_idx, gl_hidden_tshirt_idx]
                                    )


                    gr.Markdown("### 2. Private LLM Model Selection")
                    pcai_model_sliders = []
                    gl_hidden_model_sliders = []

                    for i in range(6):
                        if i < len(PRIVATE_LLMS):
                            m_name = PRIVATE_LLMS[i]['model']
                            with gr.Row():
                                s = gr.Slider(0, 16, value=1, step=1, label=f"{m_name}", scale=3)
                                n = gr.Number(value=1, precision=0, scale=1, show_label=False)
                                gl_slider = gr.Number(value=1, visible=False)
                                
                                # Sync slider/number
                                s.change(lambda x: x, s, n)
                                n.change(lambda x: x, n, s)
                                s.change(lambda x: x, s, gl_slider)

                                pcai_model_sliders.append(s)
                                gl_hidden_model_sliders.append(gl_slider)
                        else:
                            gr.Slider(label="Empty Slot", interactive=False)
                    
                    with gr.Row():
                        with gr.Column():
                            gr.Markdown("### 3. Precision")
                            precision_radio = gr.Radio(["16 bit", "8 bit"], value="16 bit", label="Weight Quantization") #, "4 bit (Future)"]
                        with gr.Column():
                            gr.Markdown("### 4. Utilization")
                            with gr.Row():
                                work_hours = gr.Number(24, label="Hours / Day")
                                work_days = gr.Number(365, label="Days / Period")

                    gr.Markdown("### 5. System Pricing")
                    with gr.Row():
                        capex_price = gr.Number(1500000, label="Capex Price ($)")
                        capex_years = gr.Number(3, label="Amortization Years")
                    # Unchanged top lines inside Tab 2 layout:
# capex_years_input = gr.Slider(label="Capex Amortization Period (Years)", minimum=1, maximum=5, step=1, value=3)
# --- START OF GREENLAKE CONFIGURE FIELDS PATCH ---
                    gr.HTML("<hr style='border: 1px solid #2A3F5C; margin: 25px 0;'>")
                    gr.Markdown("### HPE GreenLake Consumption Pricing Parameters")
                    
                    with gr.Row():
                        gl_committed_pct = gr.Slider(
                            label="Committed Hardware Utilization %",
                            minimum=60, maximum=100, step=5, value=80,
                            interactive=True
                        )
                    
                    with gr.Row():
                        with gr.Column(scale=1):
                            gr.Markdown("<span style='color: #01A982; font-weight:600;'>Committed Base Rates</span>")
                            gl_gpu_commit_rate = gr.Number(label="GPU Commit Rate ($/GPU-Hour)", value=11.31, interactive=True)
                            gl_storage_commit_rate = gr.Number(label="Storage Commit Rate ($/GB-Month)", value=0.7533, interactive=True)
                            
                        with gr.Column(scale=1):
                            gr.Markdown("<span style='color: #6B8099; font-weight:600;'>Burst Capacity Rates</span>")
                            gl_gpu_burst_rate = gr.Number(label="GPU Burst Rate ($/GPU-Hour)", value=11.31, interactive=True)
                            gl_storage_burst_rate = gr.Number(label="Storage Burst Rate ($/GB-Month)", value=0.7533, interactive=True)

                    # Auto-Sync Hooks: Binds burst rates to equal committed values by default
                    gl_gpu_commit_rate.change(lambda v: v, inputs=[gl_gpu_commit_rate], outputs=[gl_gpu_burst_rate])
                    gl_storage_commit_rate.change(lambda v: v, inputs=[gl_storage_commit_rate], outputs=[gl_storage_burst_rate])
# --- END OF GREENLAKE CONFIGURE FIELDS PATCH ---
# Unchanged bottom lines inside Tab 2 layout:
# with gr.Column():
#     gr.Markdown("### 📈 Sizing Results")

                    # with gr.Accordion("GreenLake Consumption (Future)", open=False):
                    #     gr.Number(label="Monthly Base", interactive=False)
                    #     gr.Slider(label="Commit %", interactive=False)

                    # Replace the GreenLake Accordion with this Model Reference section
                    # with gr.Accordion("Private LLM Reference Data", open=False):
                    #     gr.Markdown("Below are the model parameters loaded that are used for sizing calculations.")
                    #     # Display the loaded PRIVATE_LLMS list as a table
                    #     gr.Dataframe(
                    #         value=PRIVATE_LLMS,
                    #         interactive=False,
                    #         label="Loaded Private Model Library"
                    #     )
                    with gr.Accordion("Private LLM Reference Data", open=False):
                        gr.Markdown("Below are the model parameters loaded that are used for sizing calculations.")
                        # Construct a raw HTML Table string with doubled curly braces for Python string safety
                        table_html = """
                            <div style="overflow-x: auto; width: 100%;">
                                <table style="width:100%; font-size:0.75rem; border-collapse:collapse; color: #01A982; background-color: #1A2744; border-radius: 4px; table-layout: auto;">
                                    <thead>
                                        <tr style="border-bottom:2px solid #01A982; text-align:left;">
                                            <th style="padding:8px 10px; background-color: #1A2744; color: #01A982; font-weight:600; white-space: nowrap;">Model</th>
                                            <th style="padding:8px 10px; background-color: #1A2744; color: #01A982; font-weight:600; text-align:right; white-space: nowrap;">RTX TPS (16-bit)</th>
                                            <th style="padding:8px 10px; background-color: #1A2744; color: #01A982; font-weight:600; text-align:right; white-space: nowrap;">RTX TPS (8-bit)</th>
                                            <th style="padding:8px 10px; background-color: #1A2744; color: #01A982; font-weight:600; text-align:right; white-space: nowrap;">RTX TP (16-bit)</th>
                                            <th style="padding:8px 10px; background-color: #1A2744; color: #01A982; font-weight:600; text-align:right; white-space: nowrap;">RTX TP (8-bit)</th>
                                            <th style="padding:8px 10px; background-color: #1A2744; color: #01A982; font-weight:600; text-align:right; white-space: nowrap;">H200 TPS (16-bit)</th>
                                            <th style="padding:8px 10px; background-color: #1A2744; color: #01A982; font-weight:600; text-align:right; white-space: nowrap;">H200 TPS (8-bit)</th>
                                            <th style="padding:8px 10px; background-color: #1A2744; color: #01A982; font-weight:600; text-align:right; white-space: nowrap;">H200 TP (16-bit)</th>
                                            <th style="padding:8px 10px; background-color: #1A2744; color: #01A982; font-weight:600; text-align:right; white-space: nowrap;">H200 TP (8-bit)</th>
                                        </tr>
                                    </thead>
                                    <tbody>"""
                                    
                        for m in PRIVATE_LLMS:
                            table_html += f"""
                                    <tr style="border-bottom: 1px solid #2A3F5C;">
                                        <td style="padding:8px 10px; background-color: #1A2744; font-weight:600; color: #01A982; white-space: nowrap;">{m.get('model', 'N/A')}</td>
                                        <td style="padding:8px 10px; background-color: #1A2744; text-align:right; color: #01A982;">{m.get('rtx_tps_16', '0')}</td>
                                        <td style="padding:8px 10px; background-color: #1A2744; text-align:right; color: #01A982;">{m.get('rtx_tps_8', '0')}</td>
                                        <td style="padding:8px 10px; background-color: #1A2744; text-align:right; color: #01A982;">{m.get('rtx_tp_16', '0')}</td>
                                        <td style="padding:8px 10px; background-color: #1A2744; text-align:right; color: #01A982;">{m.get('rtx_tp_8', '0')}</td>
                                        <td style="padding:8px 10px; background-color: #1A2744; text-align:right; color: #01A982;">{m.get('h200_tps_16', '0')}</td>
                                        <td style="padding:8px 10px; background-color: #1A2744; text-align:right; color: #01A982;">{m.get('h200_tps_8', '0')}</td>
                                        <td style="padding:8px 10px; background-color: #1A2744; text-align:right; color: #01A982;">{m.get('h200_tp_16', '0')}</td>
                                        <td style="padding:8px 10px; background-color: #1A2744; text-align:right; color: #01A982;">{m.get('h200_tp_8', '0')}</td>
                                    </tr>"""
                                    
                        table_html += """
                                </tbody>
                            </table>
                        </div>"""
                        
                        gr.HTML(table_html)


                with gr.Column(scale=2):
                    gr.Markdown("### PCAI Results")
                    with gr.Group():
                        pcai_total_tokens = gr.Markdown("## 0", elem_classes="stat-card")
                        pcai_cpm = gr.Markdown("$0.00 / M tokens", elem_classes=["stat-card", "green-text"])
                        #pcai_total_tokens = gr.HTML("<div class='stat-card'>0</div>")
                        #pcai_cpm = gr.HTML("<div class='green-text'>$0.00 <span class='unit-text'>/ M tokens</span></div>")
                    
                    # --- START OF GREENLAKE DISPLAY PANEL PATCH ---
                    #with gr.Row(elem_classes=["metric-card-row"]):
                        # gl_token_cost_output = gr.Number(
                        #     label="HPE GreenLake Cost / Million Tokens ($)", 
                        #     precision=4, 
                        #     interactive=False
                        # )
                        #gl_cpm_output = gr.Markdown(value="$0.00 / M tokens", elem_classes=["stat-card", "green-text"])
            

                    pcai_breakdown_viz = gr.HTML()
                    with gr.Accordion("Sizing Details", open=False):
                        pcai_sizing_table = gr.HTML()

# --- START OF GREENLAKE OUTPUT VISUALS PATCH ---
                    gr.Markdown("### GreenLake Consumption Results")
                    with gr.Group():
                        #gl_cpm_output = gr.HTML("<div class='green-text'>$0.00 <span class='unit-text'>/ M tokens</span></div>")
                        gl_cpm_output = gr.Markdown(value="$0.00 / M tokens", elem_classes=["stat-card", "green-text"])
                    with gr.Accordion("Detailed GreenLake Calculation Parameter Breakdown", open=True):
                        detailed_gl_calc_breakdown = gr.HTML()
# --- END OF GREENLAKE OUTPUT VISUALS PATCH ---


            
        with gr.Tab("Compare"):
            #gr.Markdown("### TCO Comparison\n*Section under development*")
            with gr.Tab("Monthly Comparison"):
                comparison_table = gr.HTML(
                value=get_tab3_comparison(),
                label="TCO & Efficiency Comparison"
            )

    # Footer
    gr.Markdown("""
    <div class='hpe-footer'>
    Rates are indicative. Actual costs vary by region, contract, and workload profile. 
    GPU throughput: vLLM community benchmarks. PCAI specs: HPE datasheets June 2025.
    </div>
    """)

# --- START CHANGE 11001: CLEAN TAB-STABLE REACTIVITY ---
    # 1. Define input/output groups
    all_inputs = [raw_token_count, in_pct, out_pct] + weight_sliders + visible_prices
    all_outputs = [total_cost_out, cpm_out, breakdown_out, details_table_out]
    
    # 2. Map Slider Index to Raw Count (Instant local update)
    def map_token_step(index):
        val = TOKEN_STEPS[int(index)]
        label = TOKEN_LABELS[int(index)]
        return val, f"**Current: {label} Tokens**"

    token_slider.change(
        map_token_step, 
        inputs=[token_slider], 
        outputs=[raw_token_count, token_display]
    )

    # 3. Slider Sync (Input % -> Output %)
    in_pct.change(lambda x: 100 - x, inputs=[in_pct], outputs=[out_pct])

    # 4. Trigger UI Updates
    # We only trigger when a slider actually moves. 
    # This keeps the app idle (and the tabs fast) until the user interacts.
    main_triggers = [raw_token_count, in_pct, out_pct] + weight_sliders
    
    for trigger in main_triggers:
        trigger.change(
            update_ui, 
            inputs=all_inputs, 
            outputs=all_outputs
        )

    # 5. Price Updates (Using .blur to prevent keystroke-lag)
    for price_ctrl in visible_prices:
        price_ctrl.blur(update_ui, inputs=all_inputs, outputs=all_outputs)

    # NO demo.load HERE - This prevents the startup freeze.
    # 4. THE GLOBAL TRIGGER
    # This button is outside the tabs, so it works from anywhere.
    # refresh_btn.click(
    #     update_ui,
    #     inputs=all_inputs,
    #     outputs=all_outputs
    # )
    # --- END CHANGE 11001 ---
    # Reactivity for Tab 2
    # --- FIX: MOVED SLIDERS TO THE END ---
    pcai_inputs = [
        selected_tshirt_idx, # Index 0
        precision_radio,     # Index 1
        work_hours,          # Index 2
        work_days,           # Index 3
        capex_price,         # Index 4
        capex_years          # Index 5
    ] + pcai_model_sliders   # Index 6 onwards


    #pcai_inputs = [selected_tshirt_idx] + pcai_model_sliders + [precision_radio, work_hours, work_days, capex_price, capex_years]
    pcai_outputs = [pcai_total_tokens, pcai_cpm, pcai_breakdown_viz, pcai_sizing_table]

    # 1. Combined Master Lists
    #global_inputs = all_inputs + pcai_inputs
    #global_outputs = all_outputs + pcai_outputs

    # --- START CHANGE 28001: FIX PCAI RADIO INTERACTIVITY ---

    # # 1. Update when the T-Shirt selection changes
    # selected_tshirt_idx.change(
    #     fn=update_pcai_ui,
    #     inputs=pcai_inputs,
    #     outputs=pcai_outputs
    # )

    # # 2. Update when any PCAI model slider changes
    # for slider in pcai_model_sliders:
    #     slider.change(
    #         fn=update_pcai_ui,
    #         inputs=pcai_inputs,
    #         outputs=pcai_outputs
    #     )

    # # 3. Add other PCAI triggers (Precision, Hours, etc.)
    # other_pcai_triggers = [precision_radio, work_hours, work_days]
    # for trigger in other_pcai_triggers:
    #     trigger.change(
    #         fn=update_pcai_ui,
    #         inputs=pcai_inputs,
    #         outputs=pcai_outputs
    #     )

    # --- END CHANGE 28001 ---
    for component in pcai_inputs:
        component.change(
            fn=update_pcai_ui,
            inputs=pcai_inputs,
            outputs=pcai_outputs
        )


    # --- START CHANGE 21001: CLEAN IDENTITY MAPPING ---
    # working tab2 - capex
    # def refresh_all_tabs(*data):
    #     """
    #     *data receives all 27+ inputs as a flat tuple from Gradio.
    #     We then use your pre-defined lists to map those values back to 
    #     the specific components each tab logic expects.
    #     """
    #     # 1. Create a lookup dictionary: {Component_Object: Current_Value}
    #     # zip() pairs your global_inputs list with the live data from the browser
    #     data_map = {comp: val for comp, val in zip(global_inputs, data)}
        
    #     # 2. Extract values for Tab 1 (Cloud API)
    #     # This rebuilds the exact list order update_ui() expects
    #     cloud_vals = [data_map[comp] for comp in all_inputs]
        
    #     # 3. Extract values for Tab 2 (Private Cloud AI)
    #     # This rebuilds the exact list order update_pcai_ui() expects
    #     pcai_vals = [data_map[comp] for comp in pcai_inputs]
        
    #     # 4. Execute both logic functions
    #     cloud_results = update_ui(*cloud_vals)
    #     pcai_results = update_pcai_ui(*pcai_vals)
        
    #     # 5. Return one unified tuple of results to Gradio
    #     # Order matches: [cloud_outputs...] + [pcai_outputs...]
    #     return (*cloud_results, *pcai_results)

    # # 4. Set the trigger
    # refresh_btn.click(
    #     fn=refresh_all_tabs,
    #     inputs=global_inputs,
    #     outputs=global_outputs
    # )

# --- START OF GREENLAKE EVENT DEPENDENCY REGISTRATION PATCH ---
 
    # greenlake_interactive_inputs = [
    #     gl_hidden_tshirt_idx,
    # ] + gl_hidden_model_sliders + [
    #     gl_committed_pct, 
    #     gl_gpu_commit_rate, 
    #     gl_gpu_burst_rate, 
    #     gl_storage_commit_rate, 
    #     gl_storage_burst_rate,
    #     gl_hidden_precision # Add this here to pass it into *args
    # ]
    
    greenlake_ui_outputs = [
        gl_cpm_output, 
        detailed_gl_calc_breakdown
    ]

    # 2. Update Master Tracking Lists
    # Fixed parameters first, variable lists last
    greenlake_fixed_params = [gl_committed_pct, gl_gpu_commit_rate, gl_gpu_burst_rate, gl_storage_commit_rate, gl_storage_burst_rate, gl_hidden_precision]

    # MUST match this sequence EXACTLY in the unpacker below
    greenlake_interactive_inputs = [gl_hidden_tshirt_idx] + greenlake_fixed_params + gl_hidden_model_sliders
    
    global_inputs = all_inputs + pcai_inputs + greenlake_interactive_inputs
    global_outputs = all_outputs + pcai_outputs + greenlake_ui_outputs + [comparison_table]


# 3. Bind changes to immediately run calculations for the GreenLake Tab
    # Update when visible PCAI components are adjusted
    selected_tshirt_idx.change(
        fn=update_greenlake_ui,
        inputs=greenlake_interactive_inputs,
        outputs=greenlake_ui_outputs
    )
    for component in pcai_model_sliders:
        component.change(
            fn=update_greenlake_ui,
            inputs=greenlake_interactive_inputs,
            outputs=greenlake_ui_outputs
        )

    # Update when native GreenLake inputs are adjusted
    gl_native_inputs = [
        gl_committed_pct, 
        gl_gpu_commit_rate, 
        gl_gpu_burst_rate, 
        gl_storage_commit_rate, 
        gl_storage_burst_rate,
        gl_hidden_precision
    ]
    for component in gl_native_inputs:
        component.change(
            fn=update_greenlake_ui,
            inputs=greenlake_interactive_inputs,
            outputs=greenlake_ui_outputs
        )

# --- START CHANGE 29002: SYNC RADIO TO HIDDEN ---
    precision_radio.change(
        fn=lambda x: x, 
        inputs=[precision_radio], 
        outputs=[gl_hidden_precision]
    )


# --- END OF GREENLAKE EVENT DEPENDENCY REGISTRATION PATCH ---


# --- END OF GREENLAKE EVENT DEPENDENCY REGISTRATION PATCH ---
# --- START CHANGE: RECONCILED MULTI-TAB REFRESH SYSTEM ---
    DEBUG_REFRESH_TABS = False  # Set to False later to turn off terminal logs

    def refresh_all_tabs(*data):
        """
        *data receives all inputs as a flat tuple from Gradio.
        Instead of looking up components by variable identity (which fails due to duplicates),
        this steps through the incoming *data tuple sequentially in the exact order of global_inputs.
        """
        if DEBUG_REFRESH_TABS:
            print("\n=== 🔍 DEBUG START: refresh_all_tabs ===")
            print(f"Total elements received from frontend (*data): {len(data)}")
        
        # Track our position in the flat incoming data tuple sequentially
        data_idx = 0
        
        # 1. Extract values for Tab 1 (Cloud API)
        cloud_vals = []
        for comp in all_inputs:
            cloud_vals.append(data[data_idx])
            data_idx += 1
            
        # 2. Extract values for Tab 2 (Private Cloud AI)
        pcai_vals = []
        for comp in pcai_inputs:
            pcai_vals.append(data[data_idx])
            data_idx += 1


        # 3. Extract values for Tab 3 (GreenLake Consumption)
        greenlake_vals = []
        for comp in greenlake_interactive_inputs:
            greenlake_vals.append(data[data_idx])
            data_idx += 1

        if DEBUG_REFRESH_TABS:
            print(f"Sequential Unpack -> Cloud: {len(cloud_vals)} | PCAI: {len(pcai_vals)} | GreenLake: {len(greenlake_vals)}")
            print("Executing update_ui()...")
            
        # 4. Execute all three backend calculation logic blocks
        cloud_results = update_ui(*cloud_vals)
        
        if DEBUG_REFRESH_TABS:
            print(f"Returned from update_ui(): {len(cloud_results)} metrics")
            print("Executing update_pcai_ui()...")
            
        pcai_results = update_pcai_ui(*pcai_vals)

        if DEBUG_REFRESH_TABS:
            print(f"Returned from update_pcai_ui(): {len(pcai_results)} metrics")
            print("Executing update_greenlake_ui()...")
        
        if DEBUG_REFRESH_TABS:
            print(f"--- DEBUG: Hand-off ---")
            print(f"PCAI Tokens (M) extracted: {GLOBAL_TOKENS_PER_DAY:,.2f}")
            print(f"Passing to GreenLake UI...")  

        greenlake_results = update_greenlake_ui(*greenlake_vals)
        
        if DEBUG_REFRESH_TABS:
            print(f"Returned from update_greenlake_ui(): {len(greenlake_results)} metrics")
        

        new_table_data = get_tab3_comparison()


        # 5. Return one unified tuple of all 10 results back to Gradio layout targets
        final_out = (*cloud_results, *pcai_results, *greenlake_results, new_table_data)
        
        if DEBUG_REFRESH_TABS:
            print(f"Total outputs ready to return to Gradio: {len(final_out)}")
            print("=== 🔍 DEBUG END: refresh_all_tabs ===\n")
        
        return final_out

# # Simulate the click automatically 500ms after the page finishes loading


    # 3. Update the Global Refresh Button
    refresh_btn.click(
        refresh_all_tabs,
        inputs=global_inputs,
        outputs=global_outputs
    )

# --- END CHANGE 17001 ---


# 1. Trigger when PCAI inputs change
    for component in pcai_inputs:
        component.change(
            fn=refresh_all_tabs,
            inputs=global_inputs,
            outputs=global_outputs
        )
        
    # 2. Trigger when Cloud inputs change (optional, but recommended for consistency)
    for trigger in main_triggers:
        trigger.change(
            fn=refresh_all_tabs,
            inputs=global_inputs,
            outputs=global_outputs
        )

# Simulate the click automatically 500ms after the page finishes loading
    demo.load(
        None, 
        inputs=None, 
        outputs=None, 
        js="() => { setTimeout(() => { document.getElementById('global-refresh-btn').click(); }, 500); }"
    )


if __name__ == "__main__":
    demo.launch(theme=get_theme(), css=CUSTOM_CSS, allowed_paths=["./images"])