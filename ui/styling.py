import gradio as gr

HPE_COLORS = {
    'green': '#01A982',
    'teal': '#00E8C0',
    'navy': '#0E1C2F',
    'blue': '#1A2744',
    'card': '#1E2E45',
    'border': '#2A3F5C',
    'muted': '#6B8099',
    'light': '#CCD2D8',
}

def get_theme():
    return gr.themes.Soft(
        primary_hue="teal",
        secondary_hue="green",
        neutral_hue="slate",
    ).set(
        # Page level
        body_background_fill=HPE_COLORS['navy'],
        body_text_color=HPE_COLORS['light'],
        
        # Component level
        block_background_fill=HPE_COLORS['card'],
        block_border_color=HPE_COLORS['border'],
        block_title_text_color="#FFFFFF",

        # --- ADD THESE 3 LINES TO FIX THE TEAL PILL ---
        block_label_background_fill=HPE_COLORS['blue'],
        block_label_text_color="#FFFFFF",
        block_label_border_color=HPE_COLORS['border'],
        
        # Interactive elements
        slider_color=HPE_COLORS['green'],
        button_primary_background_fill=HPE_COLORS['green'],
        button_primary_text_color="#FFFFFF",
        
        # Inputs
        input_background_fill=HPE_COLORS['blue'],
        input_border_color=HPE_COLORS['border']
    )




CUSTOM_CSS = f"""
/* 1. Global Scaling & Branding */
:root {{
    font-size: 18px !important; /* Global multiplier for all text */
}}

body, .gradio-container {{
    font-family: 'HPE Metric Regular', 'HPE Simplified', Arial, sans-serif !important;
}}

/* 2. Slider Info Text Modification (Image image_9edbe5.png) */
/* Targets the 'Slide to select volume...' descriptive text */
.gr-form .gr-block .gr-info-text {{
    font-size: 1.2rem !important; /* Increased for better legibility */
    color: #C3D1DF !important; /* Lighter gray for dark mode visibility */
    margin-top: 6px !important;
    display: block !important;
}}

/* 3. Cost-Per-Million Text Modification (Image image_9edf43.png) */
/* Targets the green text output showing the $/M tokens rate */
.green-text {{ 
    color: {HPE_COLORS['green']} !important; 
    font-weight: bold !important;
    font-size: 2.8rem !important; /* Significantly increased for results visibility */
    font-family: 'HPE Metric Regular', sans-serif !important;    
    padding: 5px 0 !important;
    line-height: 1.1 !important;
    display: block !important;
}}

/* 4. Stat Cards & Totals (Large results display) */
.stat-card {{ 
    background: {HPE_COLORS['blue']}; 
    padding: 20px; 
    border-radius: 8px; 
    border: 1px solid {HPE_COLORS['border']}; 
}}

/* Targets the main total cost figure ($0.00) in the results pane */
.stat-card span, .stat-card div, .stat-card p {{
    font-size: 2.8rem !important; /* Maximum prominence for final totals */
    font-family: 'HPE Metric Regular', sans-serif !important;
    line-height: 1.1 !important;
}}

/* 5. Header & Footer Scaling */
.hpe-header {{ 
    background-color: {HPE_COLORS['blue']}; 
    padding: 25px 20px; 
    border-bottom: 3px solid {HPE_COLORS['green']}; 
}}

.hpe-header h1 {{
    font-size: 2.2rem !important;
    font-weight: 700 !important;
}}

.hpe-footer {{
    font-size: 1rem !important;
    color: {HPE_COLORS['muted']} !important;
}}

/* 6. Slider UI Cleanup (Removing numeric artifacts) */
.xtick-label {{ 
    display: none !important; /* Hides 0 and 9 labels */
}}

.gradio-container input[type=number].slider-input {{ 
    display: none !important; /* Hides numeric input box */
}}


/* Add to ui/styling.py */
.system-tile {{
    min-height: 100px !important;
    max-height: 100px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    text-align: center !important;
    font-weight: 600 !important;
    line-height: 1.2 !important;
    padding: 10px !important;
    transition: all 0.2s ease !important;
}}

/* Ensure the primary (green) button stands out */
.system-tile.primary {{
    border: 2px solid #00E8C0 !important;
    box-shadow: 0 0 10px rgba(1, 169, 130, 0.4) !important;
}}

/* THIS IS THE MISSING PIECE: It aligns the number and the label */
.stat-card h2 {{
    display: flex !important;
    align-items: baseline !important; /* Aligns the 'bottom' of the text */
    gap: 10px !important;
    margin: 0 !important;
    color: {HPE_COLORS['green']} !important;
    font-size: 2.8rem !important;
}}

/* This makes the word 'tokens' look professional and small */
.unit-text {{
    font-size: 1.2rem !important;
    color: {HPE_COLORS['muted']} !important;
    font-weight: normal !important;
    text-transform: lowercase;
}}

/* 1. Force the inner span text container of the unselected choice to pure black */
.gradio-radio label:not(.selected) span {{
    color: #000000 !important;
    font-weight: 600 !important;   /* Enhances text clarity on the white tile */
    opacity: 1.0 !important;       /* Prevents Gradio from lowering the visibility layer */
}}

/* 2. Optional: Clean up the radio circle icon itself so it isn't faint */
.gradio-radio label:not(.selected) input[type="radio"] {{
    border-color: #000000 !important;
}}

/* Make the overall container taller and give labels larger text */
.gradio-radio {{
    font-size: 1.1rem !important; /* Increase text size from default */
}}

/* Make the unselected white box look larger and match system tiles */
.gradio-radio label {{
    padding: 12px 20px !important; /* Increases target area and block size */
    min-height: 48px !important;    /* Assures a prominent block height */
    display: inline-flex !important;
    align-items: center !important;
}}

/* Optional: Make the radio dot/circle icons slightly larger to scale with the text */
.gradio-radio input[type="radio"] {{
    transform: scale(1.2) !important;
    margin-right: 8px !important;
}}

.gradio-dataframe table thead th {{
        background-color: #000000 !important;
        color: #01A982 !important;
        font-size: 0.75rem !important;
        font-weight: 600 !important;
        border-bottom: 2px solid #01A982 !important;
    }}

    .gradio-dataframe table tbody td {{
        background-color: #000000 !important;
        color: #01A982 !important;
        font-size: 0.75rem !important;
        border: 1px solid #2A3F5C !important;
    }}

    .gradio-dataframe table tr:nth-child(even) td {{
        background-color: #000000 !important;
    }}

    .gradio-dataframe .table-wrap, 
    .gradio-dataframe table {{
        background-color: #000000 !important;
        border-radius: 4px !important;
    }}

"""


# CUSTOM_CSS = f"""
# /* 1. Global Scaling and Branding */
# :root {{
#     font-size: 18px !important; /* Increases base size for the entire app */
# }}

# body, .gradio-container {{
#     font-family: 'HPE Metric Regular', 'HPE Simplified', Arial, sans-serif !important;
# }}

# /* 2. Header and Text Hierarchy */
# .hpe-header {{ 
#     background-color: {HPE_COLORS['blue']}; 
#     padding: 25px 20px; 
#     border-bottom: 3px solid {HPE_COLORS['green']}; 
#     min-height: 100px;
# }}

# .hpe-header h1 {{
#     font-size: 2.2rem !important;
#     font-weight: 700 !important;
#     margin: 0 !important;
# }}

# .hpe-header p {{
#     font-size: 1.1rem !important;
#     margin: 0 !important;
# }}

# /* 3. Stat Cards and Totals (Enhanced Legibility) */
# .stat-card {{ 
#     background: {HPE_COLORS['blue']}; 
#     padding: 20px; 
#     border-radius: 8px; 
#     border: 1px solid {HPE_COLORS['border']}; 
# }}

# /* Targets the 'not bold' totals to make them stand out */
# .stat-card span, .stat-card div, .stat-card p {{
#     font-size: 2.4rem !important;
#     font-family: 'HPE Metric Regular', sans-serif !important;
#     line-height: 1.1 !important;
# }}

# .green-text {{ 
#     color: {HPE_COLORS['green']}; 
#     font-weight: bold;
#     font-size: 1.3rem !important; 
# }}

# /* 4. Small Text and Footer Cleanup */
# .hpe-footer {{ 
#     font-size: 0.95rem !important; 
#     color: {HPE_COLORS['muted']}; 
#     padding: 20px; 
#     border-top: 1px solid {HPE_COLORS['border']}; 
#     margin-top: 50px; 
# }}

# .block-label {{
#     background-color: {HPE_COLORS['blue']} !important;
#     color: white !important;
#     font-size: 1rem !important;
#     border: 1px solid {HPE_COLORS['border']} !important;
# }}

# /* 5. Slider UI Cleanup */
# .xtick-label {{ 
#     display: none !important; 
# }}

# .gradio-container input[type=number].slider-input {{ 
#     display: none !important; 
# }}

# /* 6. Logo artifact cleanup */
# .hpe-header img + div {{
#     display: none !important;
# }}

# .hpe-header div[data-testid="image-actions"] {{
#     display: none !important;
# }}

# .hpe-header .secondary-header-pills {{
#     display: none !important;
# }}
# """

# def get_theme():
#     return gr.themes.Soft(
#         primary_hue="teal",
#         secondary_hue="green",
#         neutral_hue="slate",
#     ).set(
#         body_background_fill=HPE_COLORS['navy'],
#         block_background_fill=HPE_COLORS['card'],
#         block_border_color=HPE_COLORS['border'],
#         body_text_color=HPE_COLORS['light'],
#         header_text_color="#FFFFFF"
#     )

# CUSTOM_CSS = f"""
# /* 1. Use double braces for CSS blocks to avoid f-string errors */
# .hpe-header {{ 
#     background-color: {HPE_COLORS['blue']}; 
#     padding: 20px; 
#     border-bottom: 3px solid {HPE_COLORS['green']}; 
# }}

# .hpe-footer {{ 
#     font-size: 0.8rem; 
#     color: {HPE_COLORS['muted']}; 
#     padding: 20px; 
#     border-top: 1px solid {HPE_COLORS['border']}; 
#     margin-top: 50px; 
# }}

# .stat-card {{ 
#     background: {HPE_COLORS['blue']}; 
#     padding: 15px; 
#     border-radius: 8px; 
#     border: 1px solid {HPE_COLORS['border']}; 
# }}

# .green-text {{ 
#     color: {HPE_COLORS['green']}; 
#     font-weight: bold; 
# }}

# /* 2. Slider cleanup: Hide the index numbers and small input box */
# .xtick-label {{ 
#     display: none !important; 
# }}

# .gradio-container input[type=number].slider-input {{ 
#     display: none !important; 
# }}

# /* 3. Logo artifact cleanup */
# .hpe-header img + div {{
#     display: none !important;
# }}

# .hpe-header div[data-testid="image-actions"] {{
#     display: none !important;
# }}

# .hpe-header .secondary-header-pills {{
#     display: none !important;
# }}
# """

