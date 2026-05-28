import gradio as gr
import base64
from modules.calculations import calculate_cloud_costs, format_token_label
from ui.styling import HPE_COLORS, CUSTOM_CSS, get_theme

# Initial Data
DEFAULT_MODELS = [
    {"name": "Claude Opus 4", "in": 15.00, "out": 75.00, "weight": 86},
    {"name": "Claude Sonnet 4.5", "in": 3.00, "out": 15.00, "weight": 12},
    {"name": "Claude Haiku 3.5", "in": 0.80, "out": 4.00, "weight": 2},
    {"name": "GPT-4o", "in": 2.50, "out": 10.00, "weight": 0},
    {"name": "Gemini 2.0 Pro", "in": 7.00, "out": 21.00, "weight": 0},
    {"name": "Gemini 2.0 Flash", "in": 0.10, "out": 0.40, "weight": 0},
]

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

    with gr.Tabs():
        with gr.Tab("Cloud API"):
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


        with gr.Tab("Private Cloud AI"):
            gr.Markdown("### PCAI Configurator\n*Section under development*")
            
        with gr.Tab("Compare"):
            gr.Markdown("### TCO Comparison\n*Section under development*")

    # Footer
    gr.Markdown("""
    <div class='hpe-footer'>
    Rates are indicative. Actual costs vary by region, contract, and workload profile. 
    GPU throughput: vLLM community benchmarks. PCAI specs: HPE datasheets June 2025.
    </div>
    """)

    # Reactivity
    all_inputs = [token_slider, in_pct, out_pct] + weight_sliders + visible_prices
    all_outputs = [total_cost_out, cpm_out, breakdown_out, details_table_out]
    
    # Sync label
    token_slider.change(lambda x: f"**Current: {format_token_label(x)} Tokens**", token_slider, token_display)
    # --- CHANGE 3: ADD MAPPING FUNCTION & UPDATE REACTIVITY ---

    def map_token_step(index):
        """Maps slider index (0-9) to actual value and label"""
        val = TOKEN_STEPS[int(index)]
        label = TOKEN_LABELS[int(index)]
        return val, f"**Current: {label} Tokens**"

    # Connect the index slider to the mapping function
    token_slider.change(
        map_token_step, 
        inputs=[token_slider], 
        outputs=[raw_token_count, token_display]
    )

    # Update your 'all_inputs' list to use the hidden raw_token_count for calculations
    # Replace token_slider with raw_token_count in the list below:
    all_inputs = [raw_token_count, in_pct, out_pct] + weight_sliders + visible_prices


    # Continuous updates
    for inp in all_inputs:
        inp.change(update_ui, inputs=all_inputs, outputs=all_outputs)

    # --- START CHANGE 2001: LINKED SLIDERS ---
    
    def sync_output_pct(input_val):
        """Automatically sets output to the remainder of 100"""
        return 100 - input_val

    # When Input % changes, update Output %
    in_pct.change(
        sync_output_pct,
        inputs=[in_pct],
        outputs=[out_pct]
    )
    
    # --- END CHANGE 2001 ---


if __name__ == "__main__":
    demo.launch(theme=get_theme(), css=CUSTOM_CSS, allowed_paths=["./images"])