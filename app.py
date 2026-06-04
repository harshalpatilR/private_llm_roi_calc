import gradio as gr
import base64
import csv
from modules.calculations import calculate_cloud_costs, format_token_label, calculate_pcai_costs, format_large_number
from ui.styling import HPE_COLORS, CUSTOM_CSS, get_theme

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


# --- START CHANGE 34001: RESTORED HTML FORMATTING ---

def update_pcai_ui(*args):
    """
    Inputs: [selected_tshirt_idx (int), precision_radio, work_hours, work_days, 
             capex_price, capex_years] + pcai_model_sliders
    """
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
    results = calculate_pcai_costs(
        target_ts, model_instances, precision, work_hours, work_days, 
        capex_val, capex_years, PRIVATE_LLMS
    )
    total_tokens_annual, cpm, breakdown, error_msg, used_gpu, avail_gpu = results

    # 5. Format Metric Strings
    # Calculate tokens_per_day specifically for the primary UI display
    total_tps = sum(b['total_tps'] for b in breakdown)
    tokens_per_day = total_tps * 3600 * work_hours
    
    token_str = format_large_number(tokens_per_day)
    cpm_str = f"${cpm:,.2f} / M tokens"
    
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

    # 7. Generate Detailed Metric Table HTML
    table_html = f"<div style='color:#FF4B4B; margin-bottom:10px; font-weight:bold;'>{error_msg}</div>" if error_msg else ""
    table_html += """<table style='width:100%; font-size:0.85rem; border-collapse:collapse; color: white;'>
        <thead>
            <tr style='border-bottom:2px solid #01A982; text-align:left;'>
                <th style='padding:10px 5px;'>Model</th>
                <th style='padding:10px 5px;'>TP</th>
                <th style='padding:10px 5px;'>Inst.</th>
                <th style='padding:10px 5px;'>GPUs</th>
                <th style='padding:10px 5px;'>TPS</th>
            </tr>
        </thead>
        <tbody>"""
    
    for b in breakdown:
        table_html += f"""
            <tr style='border-bottom: 1px solid #2A3F5C;'>
                <td style='padding:8px 5px;'>{b['name']}</td>
                <td style='padding:8px 5px;'>{b['tp']}</td>
                <td style='padding:8px 5px;'>{int(b['instances'])}</td>
                <td style='padding:8px 5px;'>{b['total_gpus']}</td>
                <td style='padding:8px 5px;'>{b['total_tps']:,.0f}</td>
            </tr>"""
            
    table_html += f"""
        </tbody>
        <tfoot>
            <tr style='background: rgba(1, 169, 130, 0.1); font-weight: bold;'>
                <td style='padding:10px 5px;'>TOTAL</td>
                <td style='padding:10px 5px;'>-</td>
                <td style='padding:10px 5px;'>-</td>
                <td style='padding:10px 5px;'>{used_gpu} / {avail_gpu}</td>
                <td style='padding:10px 5px;'>{total_tps:,.0f}</td>
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
    
    # Format labels
    cost_str = f"${total_cost:,.0f}"
    cpm_str = f"${cpm:,.2f} / M tokens"
    
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
                        label="Total Tokens (Annualized Scale)", 
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
                        cpm_out = gr.Markdown("$0.00 / M tokens", elem_classes="green-text")
                    
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
                    
                    with gr.Row():
                        tshirt_buttons = []
                        for idx, ts in enumerate(TSHIRTS):
                            with gr.Column(min_width=150):
                                # Create label from CSV data (image_4fb085.png)
                                btn_label = f"{ts['size_name']}\n{ts.get('GPU Type / Qty', '')}"
                                btn = gr.Button(
                                    btn_label, 
                                    variant="primary" if idx == 0 else "secondary"
                                )
                                # When clicked, update the hidden Number component
                                btn.click(lambda i=idx: i, None, selected_tshirt_idx)
                                tshirt_buttons.append(btn)

                    gr.Markdown("### 2. Private LLM Model Selection")
                    pcai_model_sliders = []
                    for i in range(6):
                        if i < len(PRIVATE_LLMS):
                            m_name = PRIVATE_LLMS[i]['model']
                            with gr.Row():
                                s = gr.Slider(0, 16, value=1, step=1, label=f"{m_name}", scale=3)
                                n = gr.Number(value=1, precision=0, scale=1, show_label=False)
                                # Sync slider/number
                                s.change(lambda x: x, s, n)
                                n.change(lambda x: x, n, s)
                                pcai_model_sliders.append(s)
                        else:
                            gr.Slider(label="Empty Slot", interactive=False)
                    
                    with gr.Row():
                        with gr.Column():
                            gr.Markdown("### 3. Precision")
                            precision_radio = gr.Radio(["16 bit", "8 bit", "4 bit (Future)"], value="16 bit", label="Weight Quantization")
                        with gr.Column():
                            gr.Markdown("### 4. Utilization")
                            with gr.Row():
                                work_hours = gr.Number(24, label="Hours / Day")
                                work_days = gr.Number(365, label="Days / Period")

                    gr.Markdown("### 5. System Pricing")
                    with gr.Row():
                        capex_price = gr.Number(250000, label="Capex Price ($)")
                        capex_years = gr.Number(3, label="Amortization Years")
                    
                    with gr.Accordion("GreenLake Consumption (Future)", open=False):
                        gr.Number(label="Monthly Base", interactive=False)
                        gr.Slider(label="Commit %", interactive=False)

                with gr.Column(scale=2):
                    gr.Markdown("### PCAI Results")
                    with gr.Group():
                        pcai_total_tokens = gr.Markdown("## 0", elem_classes="stat-card")
                        pcai_cpm = gr.Markdown("$0.00 / M tokens", elem_classes="green-text")
                    
                    pcai_breakdown_viz = gr.HTML()
                    with gr.Accordion("Sizing Details", open=False):
                        pcai_sizing_table = gr.HTML()

            
        with gr.Tab("Compare"):
            gr.Markdown("### TCO Comparison\n*Section under development*")

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
    global_inputs = all_inputs + pcai_inputs
    global_outputs = all_outputs + pcai_outputs

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

    def refresh_all_tabs(*data):
        """
        *data receives all 27+ inputs as a flat tuple from Gradio.
        We then use your pre-defined lists to map those values back to 
        the specific components each tab logic expects.
        """
        # 1. Create a lookup dictionary: {Component_Object: Current_Value}
        # zip() pairs your global_inputs list with the live data from the browser
        data_map = {comp: val for comp, val in zip(global_inputs, data)}
        
        # 2. Extract values for Tab 1 (Cloud API)
        # This rebuilds the exact list order update_ui() expects
        cloud_vals = [data_map[comp] for comp in all_inputs]
        
        # 3. Extract values for Tab 2 (Private Cloud AI)
        # This rebuilds the exact list order update_pcai_ui() expects
        pcai_vals = [data_map[comp] for comp in pcai_inputs]
        
        # 4. Execute both logic functions
        cloud_results = update_ui(*cloud_vals)
        pcai_results = update_pcai_ui(*pcai_vals)
        
        # 5. Return one unified tuple of results to Gradio
        # Order matches: [cloud_outputs...] + [pcai_outputs...]
        return (*cloud_results, *pcai_results)

    # # 4. Set the trigger
    # refresh_btn.click(
    #     fn=refresh_all_tabs,
    #     inputs=global_inputs,
    #     outputs=global_outputs
    # )

    # --- END CHANGE 21001 ---

    # 3. Update the Global Refresh Button
    refresh_btn.click(
        refresh_all_tabs,
        inputs=global_inputs,
        outputs=global_outputs
    )

# --- END CHANGE 17001 ---


if __name__ == "__main__":
    demo.launch(theme=get_theme(), css=CUSTOM_CSS, allowed_paths=["./images"])