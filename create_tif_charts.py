import os
import sys
import time
import re
import json
from collections import defaultdict
import pandas as pd
from chi_tif_parser import Tools

# -------------------------------
# Map TIFs to their Report URLs
# -------------------------------

def build_tif_reports_map():
    """Build a dictionary mapping TIF numbers to {year: report_url}."""
    year_urls = Tools.darYearsUrls()
    tif_reports = defaultdict(dict)
    for year, url in year_urls.items():
        for pdf_link in Tools.urlList(url, year):
            match = re.search(r'T_(\d+)_.*AR(\d{2})\.pdf', pdf_link)
            if match:
                tif_number, yr = match.groups()
                yr_int = int(yr)
                if yr_int >= 90:        # 1990â€"1999
                    full_year = 1900 + yr_int
                else:                   # 2000â€"2089
                    full_year = 2000 + yr_int
                tif_reports[tif_number][str(full_year)] = pdf_link
    return tif_reports

def calculate_cumulative_summary(tif_df, current_year):
    """Calculate cumulative values and track which metrics need asterisks."""
    # Get the most recent year's data for start/end years
    latest_row = tif_df[tif_df['tif_year'] == tif_df['tif_year'].max()].iloc[0]
    
    # Extract start and end years from the latest data
    start_year = int(latest_row.get('start_year', 0)) if pd.notna(latest_row.get('start_year', 0)) else None
    end_year = int(latest_row.get('end_year', 0)) if pd.notna(latest_row.get('end_year', 0)) else None
    
    # Metrics to calculate
    metrics = [
        'property_tax_extraction',
        'transfers_in', 
        'expenses',
        'transfers_out',
        'distribution',
        'admin_costs',
        'finance_costs'
    ]
    
    cumulative_values = {}
    metrics_needing_asterisks = set()
    
    for metric in metrics:
        if start_year and start_year >= 2010:
            # TIF started 2010 or later - sum all values (no asterisks needed)
            cumulative_values[metric] = tif_df[metric].fillna(0).sum()
        else:
            # TIF started before 2010 - use baseline approach
            cumulative_field = f'cumulative_{metric}'
            
            if cumulative_field in tif_df.columns:
                # Use the most recent cumulative value as it represents total cumulative (no asterisk)
                latest_cumulative = tif_df[cumulative_field].fillna(0).iloc[-1]
                cumulative_values[metric] = latest_cumulative
            else:
                # No cumulative field available - sum from 2010 onwards (needs asterisk)
                post_2010_data = tif_df[tif_df['tif_year'] >= 2010]
                cumulative_values[metric] = post_2010_data[metric].fillna(0).sum()
                metrics_needing_asterisks.add(metric)
    
    return cumulative_values, start_year, end_year, metrics_needing_asterisks

def calculate_cumulative_by_year(tif_df, target_year):
    """Calculate cumulative values up to a specific year."""
    # Get the most recent year's data for start/end years
    latest_row = tif_df[tif_df['tif_year'] == tif_df['tif_year'].max()].iloc[0]
    start_year = int(latest_row.get('start_year', 0)) if pd.notna(latest_row.get('start_year', 0)) else None
    
    # Filter data up to target year
    filtered_df = tif_df[tif_df['tif_year'] <= target_year]
    
    if filtered_df.empty:
        return {metric: 0 for metric in ['property_tax_extraction', 'transfers_in', 'expenses', 'transfers_out', 'distribution', 'admin_costs', 'finance_costs']}
    
    metrics = [
        'property_tax_extraction',
        'transfers_in', 
        'expenses',
        'transfers_out',
        'distribution',
        'admin_costs',
        'finance_costs'
    ]
    
    cumulative_values = {}
    
    for metric in metrics:
        if start_year and start_year >= 2010:
            # TIF started 2010 or later - sum all values up to target year
            value = filtered_df[metric].fillna(0).sum()
            cumulative_values[metric] = float(value)  # Convert to native Python float
        else:
            # TIF started before 2010 - use baseline approach
            cumulative_field = f'cumulative_{metric}'
            
            if cumulative_field in filtered_df.columns:
                # Use the latest cumulative value up to target year
                latest_cumulative = filtered_df[cumulative_field].fillna(0).iloc[-1]
                cumulative_values[metric] = float(latest_cumulative)  # Convert to native Python float
            else:
                # No cumulative field available - sum from 2010 onwards up to target year
                post_2010_data = filtered_df[filtered_df['tif_year'] >= 2010]
                value = post_2010_data[metric].fillna(0).sum()
                cumulative_values[metric] = float(value)  # Convert to native Python float
    
    return cumulative_values

def generate_tif_data(args):
    """Generate chart data for a single TIF."""
    tif_name, tif_number, tif_df, data_columns, links, current_year = args

    years = tif_df['tif_year'].astype(str).tolist()
    
    # Calculate summary data
    cumulative_summary, start_year, end_year, metrics_needing_asterisks = calculate_cumulative_summary(tif_df, current_year)
    
    # Calculate cumulative data for all available years for the dropdown
    available_years = sorted([int(year) for year in tif_df['tif_year'].unique()])  # Convert to int
    cumulative_by_year = {}
    for year in available_years:
        cumulative_by_year[str(year)] = calculate_cumulative_by_year(tif_df, year)  # Use string keys for JSON
    
    # Prepare chart data for each metric
    charts_data = {}
    for col in data_columns:
        values = tif_df[col].fillna(0).tolist()
        
        # Color years with zero values differently
        background_colors = []
        border_colors = []
        for v in values:
            if v == 0:
                background_colors.append('rgba(220, 53, 69, 0.6)')  # Red for zero
                border_colors.append('rgba(220, 53, 69, 1)')
            else:
                background_colors.append('rgba(54, 162, 235, 0.6)')  # Blue for data
                border_colors.append('rgba(54, 162, 235, 1)')
        
        # Finance Costs as Tooltip with Bank Name
        extra = {}
        if col == "finance_costs" and "bank" in tif_df.columns:
            bank_list = []
            for v, b in zip(values, tif_df["bank"].fillna("").tolist()):
                bank_list.append(b if v else "")
            extra["bank"] = bank_list

        charts_data[col] = {
            'labels': years,
            'values': values,
            'background_colors': background_colors,
            'border_colors': border_colors,
            'title': col.replace('_', ' ').title(),
            **extra
        }
    
    return tif_name, tif_number, charts_data, links, cumulative_summary, start_year, end_year, metrics_needing_asterisks, cumulative_by_year

def create_tif_charts(file_path, current_report_year):
    start_time = time.time()
    df = pd.read_csv(file_path)

    out_dir = f"C:\\Users\\w\\clonedGitRepos\\chi-tif-parser\\charts"
    os.makedirs(out_dir, exist_ok=True)
    output_html = os.path.join(out_dir, f'{current_report_year}_tif_charts.html')

    data_columns = [
        'property_tax_extraction',
        'cumulative_property_tax_extraction', 
        'transfers_in',
        'cumulative_transfers_in',
        'expenses',
        'fund_balance_end',
        'transfers_out',
        'distribution',
        'admin_costs',
        'finance_costs'
    ]

    tif_names = sorted(df['tif_name'].unique())
    print(f"Processing {len(tif_names)} TIFs in alphabetical order.")

    # Calculate active TIFs and oldest start year (no longer using oldest start year)
    active_tifs = 0
    # oldest_start_year = float('inf')
    
    for tif_name in tif_names:
        tif_df = df[df['tif_name'] == tif_name]
        latest_row = tif_df[tif_df['tif_year'] == tif_df['tif_year'].max()].iloc[0]
        
        # Calculate active TIFs (those with data in current report year)
        active_tifs = len(df[df['tif_year'] == current_report_year]['tif_name'].unique())
        
        # Track oldest start year
        start_year = int(latest_row.get('start_year', 0)) if pd.notna(latest_row.get('start_year', 0)) else None
        # if start_year and start_year < oldest_start_year:
            # oldest_start_year = start_year

    # Build TIF report links map
    print("Building TIF report links map...")
    tif_links_map = build_tif_reports_map()

    # Process all TIFs
    all_tif_data = []
    toc_entries = []
    
    for i, tif_name in enumerate(tif_names):
        tif_df = df[df['tif_name'] == tif_name].sort_values('tif_year')
        tif_number = str(int(tif_df['tif_number'].iloc[0])).zfill(3)
        links = tif_links_map.get(tif_number, {})
        
        # Updated to pass current_report_year
        _, _, charts_data, _, cumulative_summary, start_year, end_year, metrics_needing_asterisks, cumulative_by_year = generate_tif_data((tif_name, tif_number, tif_df, data_columns, links, current_report_year))
        all_tif_data.append((tif_name, tif_number, charts_data, links, cumulative_summary, start_year, end_year, metrics_needing_asterisks, cumulative_by_year))
        toc_entries.append((tif_name, tif_number))
        
        if (i + 1) % 20 == 0:
            print(f"Processed {i + 1}/{len(tif_names)} TIFs")

    # Create HTML document
    html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TIF Report Charts {current_report_year}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js/dist/chart.umd.js"></script>
    <style>
        html {{
            scroll-behavior: auto !important;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f5f5;
            max-height: 500vh; /* Limits total scroll height */
        }}
        
        /* Table of Contents Sidebar */
        .toc-toggle {{
            position: fixed;
            top: 20px;
            left: 20px;
            z-index: 1001;
            background: #007bff;
            color: white;
            border: none;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            font-size: 18px;
            cursor: pointer;
            box-shadow: 0 4px 20px rgba(0,123,255,0.3);
            transition: all 0.3s ease;
        }}
        
        .toc-sidebar.open + .toc-toggle {{
            left: 370px;
            background: #004085;
            box-shadow: inset 0 2px 5px rgba(0,0,0,0.3);
        }}
        
        .toc-toggle:hover {{
            background: #0056b3;
            transform: scale(1.1);
        }}
        
        .toc-sidebar {{
            position: fixed;
            top: 0;
            left: -350px;
            width: 350px;
            height: 100vh;
            background: white;
            box-shadow: 2px 0 10px rgba(0,0,0,0.1);
            z-index: 999;
            transition: left 0.3s ease;
            overflow-y: auto;
        }}
        
        .toc-sidebar.open {{
            left: 0;
        }}
        
        .toc-header {{
            background: #007bff;
            color: white;
            padding: 1rem;
            font-size: 1.2rem;
            font-weight: 600;
        }}
        
        .toc-search {{
            padding: 1rem;
            border-bottom: 1px solid #eee;
        }}
        
        .toc-search input {{
            width: 100%;
            padding: 0.5rem;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 14px;
        }}
        
        .toc-list {{
            max-height: calc(100vh - 140px);
            overflow-y: auto;
        }}
        
        .toc-item {{
            display: block;
            padding: 0.75rem 1rem;
            color: #333;
            text-decoration: none;
            border-bottom: 1px solid #f0f0f0;
            transition: background 0.2s ease;
            font-size: 14px;
            line-height: 1.4;
        }}
        
        .toc-item:hover {{
            background: #f8f9fa;
            color: #007bff;
        }}
        
        .toc-item.hidden {{
            display: none;
        }}
        
        .toc-overlay {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: rgba(0,0,0,0.5);
            z-index: 998;
            opacity: 0;
            visibility: hidden;
            transition: all 0.3s ease;
        }}
        
        .toc-overlay.show {{
            opacity: 1;
            visibility: visible;
        }}

        .jump-controls {{
            position: fixed;
            top: 50%;
            right: 20px;
            transform: translateY(-50%);
            z-index: 1000;
            display: flex;
            flex-direction: column;
            gap: 70vh;
        }}
        
        .jump-controls button {{
            background: rgba(0, 123, 255, 0.8);
            color: white;
            border: none;
            border-radius: 20px;
            width: 35px;
            height: 30px;
            font-size: 14px;
            cursor: pointer;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
            transition: all 0.2s ease;
        }}
        
        .jump-controls button:hover {{
            background: rgba(0, 123, 255, 1);
            transform: scale(1.05);
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            height: auto;
            padding: 2rem;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            position: relative;
        }}
        
        .header h1 {{
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
        }}
        
        .header p {{
            font-size: 1.1rem;
            opacity: 0.9;
        }}
        
        .header-logo {{
            position: absolute;
            top: 50%;
            right: 2rem;
            transform: translateY(-50%);
            height: 80px;
            width: auto;
            cursor: pointer;
            transition: transform 0.3s ease;
        }}

        .header-logo:hover {{
            transform: translateY(-50%) scale(1.1);
        }}
        
        .attribution-banner {{
            background: linear-gradient(135deg, #4facfe 0%, #667eea 100%);
            color: white;
            padding: 1.5rem 2rem;
            text-align: center;
            font-size: 0.95rem;
            line-height: 1.6;
        }}
        
        .attribution-banner a {{
            color: white;
            text-decoration: underline;
            font-weight: 500;
        }}
        
        .attribution-banner a:hover {{
            text-decoration: none;
            opacity: 0.8;
        }}
        
        .attribution-line {{
            margin: 0.5rem 0;
        }}
        
        .tif-page {{
            background: white;
            margin: 2rem auto;
            max-width: 1400px;
            border-radius: 10px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            overflow: hidden;
            page-break-after: always;
        }}
        
        .tif-title {{
            background: linear-gradient(135deg, #764ba2 0%, #8e44ad 100%);
            color: white;
            text-align: center;
            padding: 1.5rem;
            margin: 0;
        }}
        
        .tif-name {{
            font-size: 1.5rem;
            font-weight: 600;
            margin: 0;
        }}
        
        .tif-years {{
            font-size: 1.1rem;
            font-weight: 400;
            margin-top: 0.3rem;
            opacity: 0.9;
        }}
        
        .year-links {{
            background: #f8f9fa;
            padding: 1rem;
            text-align: center;
            border-bottom: 1px solid #e9ecef;
        }}
        
        .year-link {{
            display: inline-block;
            margin: 0.25rem 0.5rem;
            padding: 0.5rem 1rem;
            background: linear-gradient(135deg, #764ba2 0%, #8e44ad 100%);
            color: white !important;
            text-decoration: none;
            border-radius: 25px;
            font-weight: 500;
            font-size: 0.9rem;
            transition: all 0.3s ease;
            box-shadow: 0 2px 5px rgba(118, 75, 162, 0.3);
        }}

        .year-link:hover {{
            background: linear-gradient(135deg, #8e44ad 0%, #9b59b6 100%);
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(118, 75, 162, 0.4);
        }}

        .summary-section {{
            background: #f8f9fa;
            padding: 1.5rem;
            border-bottom: 1px solid #e9ecef;
            font-size: 0.9rem;
            line-height: 1.4;
        }}
        
        .summary-header {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
            margin-bottom: 1rem;
            font-weight: 600;
            color: #495057;
            font-size: 1rem;
        }}

        .summary-header select {{
            padding: 0.3rem 0.6rem;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 0.95rem;
            font-weight: 600;
            background: white;
            cursor: pointer;
            color: #495057;
        }}
        
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1rem;
        }}
        
        .summary-item {{
            background: white;
            padding: 0.8rem;
            border-radius: 5px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .summary-label {{
            font-weight: 500;
            color: #495057;
        }}
        
        .summary-value {{
            font-weight: 600;
            color: #007bff;
        }}
        
        .charts-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 1.5rem;
            padding: 2rem;
        }}
        
        .chart-container {{
            background: #f8f9fa;
            border-radius: 8px;
            padding: 1rem;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        }}
        
        .chart-title {{
            text-align: center;
            margin-bottom: 1rem;
            font-weight: 600;
            color: #333;
            font-size: 1rem;
        }}
        
        .chart-canvas {{
            max-height: 300px;
        }}
        
        .footer {{
            background: linear-gradient(135deg, #4facfe 0%, #667eea 100%);
            text-align: center;
            padding: 2rem;
            color: white;
            margin-top: 2rem;
        }}
        
        .footnote {{
            font-size: 0.85rem;
            color: white;
            font-style: italic;
            margin-top: 1rem;
        }}
        
        /* Print styles */
        @media print {{
            .toc-toggle, .toc-sidebar, .toc-overlay {{ display: none !important; }}
            body {{ background: white; }}
            .tif-page {{ 
                page-break-after: always; 
                margin: 0;
                box-shadow: none;
                max-width: none;
            }}
        }}
        
        /* Mobile responsive */
        @media (max-width: 768px) {{
            .header h1 {{ font-size: 2rem; }}
            .header-logo {{
                position: relative;
                display: block;
                margin: 1rem auto 0;
                right: auto;
                top: auto;
                transform: none;
                height: 60px;
                width: auto;
            }}
            .tif-page {{ margin: 1rem; }}
            .charts-grid {{ 
                grid-template-columns: 1fr;
                padding: 1rem;
            }}
            .summary-grid {{
                grid-template-columns: 1fr;
            }}
            .toc-sidebar {{ width: 100vw; left: -100vw; }}
            .toc-sidebar.open {{ left: 0; }}
            .attribution-banner {{
                font-size: 0.85rem;
                padding: 1rem;
            }}
        }}
    </style>
</head>
<body>
    <div id="top"></div>
    <!-- Table of Contents -->
    <button class="toc-toggle" onclick="toggleTOC()">☰</button>
    <div class="toc-overlay" onclick="closeTOC(); event.stopPropagation();"></div>
    <div class="toc-sidebar">
        <div class="toc-header">
            TIF Directory ({len(tif_names)} Districts)
        </div>
        <div class="toc-search">
            <input type="text" id="tocSearch" placeholder="Search TIF districts..." onkeyup="filterTOC()">
        </div>
        <div class="toc-list">'''

    # Add TOC entries - simple anchor links
    for tif_name, tif_number in toc_entries:
        html_content += f'<a href="#tif-{tif_number}" class="toc-item" onclick="setTimeout(closeTOC, 100)">{tif_name}</a>'

    html_content += f'''
        </div>
    </div>

    <!-- Jump Controls -->
    <div class="jump-controls">
        <button onclick="jumpTo('top')" title="Jump to Top">↑</button>
        <button onclick="jumpTo('bottom')" title="Jump to Bottom">↓</button>
    </div>
    
    <div class="header">
        <a href="https://tifreports.com/" target="_blank">
            <img src="https://github.com/willfineberg/chi-tif-parser/blob/main/images/TIF_Logo.jpg?raw=true" alt="TIF Logo" class="header-logo">
        </a>
        <h1>Chicago Tax Increment Financing (TIF) Report Charts</h1>
        <p>{active_tifs} Active TIFs in {current_report_year} • {len(tif_names)} total TIFs parsed<sup class="footnote-symbol" title="Chicago has created a total of 186 TIFs since the program began. Visit tifreports.com to see the full history." onclick="jumpTo('bottom')" style="cursor: pointer; color: white; font-weight: bold; text-shadow: 1px 1px 2px rgba(0,0,0,0.5);">†</sup></p>
        <!-- <p style="font-size: 1.0rem; opacity: 0.8; margin-top: 0.5rem;">Blue year buttons link directly to PDF reports</p> -->
    </div>
    
    <div class="attribution-banner">
        <div class="attribution-line">
            <a href="https://tifreports.com/" target="_blank">The TIF Illumination Project</a> is a people-powered investigation of the hyper-local impacts of Tax Increment Financing Districts. The Lead Organizer is <a href="http://www.tresser.com" target="_blank">Tom Tresser</a>. For more information, please contact <a href="mailto:tom@tresser.com">tom@tresser.com</a>.
        </div>
        <div class="attribution-line">
            Chicago TIF Report Charts and associated data are <a href="https://github.com/willfineberg/chi-tif-parser/" target="_blank">parsed and maintained</a> by <a href="https://www.linkedin.com/in/will-fineberg/" target="_blank">Will Fineberg</a>.
        </div>
    </div>
    '''

    # Add all TIF sections
    for tif_name, tif_number, charts_data, links, cumulative_summary, start_year, end_year, metrics_needing_asterisks, cumulative_by_year in all_tif_data:
        available_years = sorted([int(k) for k in cumulative_by_year.keys()])  # Convert keys to int for sorting
        html_content += f'''
    <div class="tif-page" id="tif-{tif_number}">
        <div class="tif-title">
            <div class="tif-name">{tif_name}</div>'''
        
        # Add years info under the title
        if start_year and end_year:
            html_content += f'<div class="tif-years">({start_year} - {end_year})</div>'
        elif start_year:
            html_content += f'<div class="tif-years">(Started: {start_year})</div>'
            
        html_content += '</div>'
        
        if links:
            html_content += '<div class="year-links">'
            for year, url in sorted(links.items()):
                html_content += f'<a href="{url}" target="_blank" class="year-link">{year}</a>'
            html_content += '</div>'
        
        # Add summary section with year selector
        html_content += '<div class="summary-section">'
        
        # Header with inline dropdown
        html_content += f'''
        <div class="summary-header">
            <span>Cumulative Totals as of</span>
            <select id="yearSelect-{tif_number}" onchange="updateSummary('{tif_number}')" autocomplete="off">'''
        
        for year in available_years:
            selected = 'selected' if year == max(available_years) else ''
            html_content += f'<option value="{year}" {selected}>{year}</option>'
        
        html_content += '''
            </select>
        </div>'''
        
        # Cumulative values grid
        html_content += f'<div class="summary-grid" id="summaryGrid-{tif_number}">'
        
        metric_labels = {
            'property_tax_extraction': 'Property Tax Extraction',
            'transfers_in': 'Transfers In',
            'expenses': 'Expenses',
            'transfers_out': 'Transfers Out',
            'distribution': 'Distribution',
            'admin_costs': 'Admin Costs',
            'finance_costs': 'Finance Costs'
        }
        
        for metric, label in metric_labels.items():
            value = cumulative_summary.get(metric, 0)
            
            # Add asterisk if this metric needs it
            if metric in metrics_needing_asterisks:
                display_label = f'{label}<span class="footnote-symbol" title="Cumulative values for TIFs established before 2010 are calculated from 2010 data onwards due to data availability limitations." onclick="jumpTo(\'bottom\')" style="cursor: pointer; color: #007bff;">*</span>'
            else:
                display_label = label
            
            html_content += f'''
            <div class="summary-item">
                <span class="summary-label">{display_label}:</span>
                <span class="summary-value" id="{metric}-{tif_number}">${value:,.0f}</span>
            </div>
            '''
        
        html_content += '</div></div>'
        
        html_content += '<div class="charts-grid">'
        
        # Add each chart
        for col, chart_data in charts_data.items():
            chart_id = f"chart_{tif_number}_{col}"
            html_content += f'''
            <div class="chart-container">
                <div class="chart-title">{chart_data['title']}</div>
                <canvas id="{chart_id}" class="chart-canvas"></canvas>
            </div>
            '''
        
        html_content += '</div></div>'

    # Check if any TIF has metrics needing asterisks for footnote
    any_asterisk_needed = any(len(metrics_needing_asterisks) > 0 for _, _, _, _, _, _, _, metrics_needing_asterisks, _ in all_tif_data)

    # Add JavaScript for charts and footer
    footer_content = f'''
    <div class="footer">
        <p>Generated on {time.strftime("%Y-%m-%d %H:%M:%S")} • Total TIFs Parsed: {len(tif_names)}</p>
        <p>Click year links to view detailed annual reports (opens in new tab) • Hover over charts for details</p>'''
    
    if any_asterisk_needed:
        footer_content += '''
        <div class="footnote">
            * Cumulative values for TIFs established before 2010 are calculated from 2010 data onwards due to data availability limitations.
        </div>'''
    
    footer_content += '''
    <div class="footnote">
        † Chicago has created a total of 186 TIFs since the program began. Click <a href="https://tifreports.com/" target="_blank" style="color: white; text-decoration: underline;">here</a> to see the full history.
    </div>'''
    
    footer_content += '</div>'
    html_content += footer_content

    html_content += '''
    <script>
        if (history.scrollRestoration) {
            history.scrollRestoration = 'manual';
        }
        window.scrollTo(0, 0);
        // Chart data
        const chartData = ''' + json.dumps({f"{tif_number}": charts_data for _, tif_number, charts_data, _, _, _, _, _, _ in all_tif_data}) + ''';
        
        // Cumulative data by year for each TIF
        const cumulativeData = ''' + json.dumps({f"{tif_number}": cumulative_by_year for _, tif_number, _, _, _, _, _, _, cumulative_by_year in all_tif_data}) + ''';
        
        // TOC functions
        function toggleTOC() {
            const sidebar = document.querySelector('.toc-sidebar');
            const overlay = document.querySelector('.toc-overlay');
            const toggle = document.querySelector('.toc-toggle');
            
            sidebar.classList.toggle('open');
            overlay.classList.toggle('show');
            
            if (sidebar.classList.contains('open')) {
                toggle.style.left = '370px';
                toggle.style.background = '#004085';
                toggle.style.boxShadow = 'inset 0 2px 5px rgba(0,0,0,0.3)';
            } else {
                toggle.style.left = '20px';
                toggle.style.background = '#007bff';
                toggle.style.boxShadow = '0 4px 20px rgba(0,123,255,0.3)';
            }
        }
        
        function closeTOC() {
            const sidebar = document.querySelector('.toc-sidebar');
            const overlay = document.querySelector('.toc-overlay');
            const toggle = document.querySelector('.toc-toggle');
            
            sidebar.classList.remove('open');
            overlay.classList.remove('show');
            
            // Reset button state
            toggle.style.left = '20px';
            toggle.style.background = '#007bff';
            toggle.style.boxShadow = '0 4px 20px rgba(0,123,255,0.3)';
        }
        
        function filterTOC() {
            const input = document.getElementById('tocSearch');
            const filter = input.value.toLowerCase();
            const items = document.querySelectorAll('.toc-item');
            
            items.forEach(item => {
                const text = item.textContent.toLowerCase();
                if (text.includes(filter)) {
                    item.classList.remove('hidden');
                } else {
                    item.classList.add('hidden');
                }
            });
        }

        // Function to jump to top or bottom
        function jumpTo(direction) {
            if (direction === 'top') {
                // Jump to top anchor
                window.location.href = '#top';
            } else if (direction === 'bottom') {
                // First jump to anchor
                window.location.href = '#page-bottom';
                
                // Then force scroll to absolute bottom after a tiny delay
                setTimeout(() => {
                    window.scrollTo(0, document.body.scrollHeight);
                }, 50);
                }
        }

        // Jump to bottom function
        function jumpToActualBottom() {
            // First jump to anchor
            window.location.href = '#page-bottom';
            
            // Then force scroll to absolute bottom after a tiny delay
            setTimeout(() => {
                window.scrollTo(0, document.body.scrollHeight);
            }, 50);
        }

        // Function to update summary based on selected year
        function updateSummary(tifNumber) {
            const yearSelect = document.getElementById(`yearSelect-${tifNumber}`);
            const selectedYear = parseInt(yearSelect.value);
            const data = cumulativeData[tifNumber][selectedYear];
            
            // Reset dropdowns on page load
            window.addEventListener('load', function() {
                document.querySelectorAll('select[id^="yearSelect-"]').forEach(function(select) {
                    // Find the maximum year option
                    let maxYear = 0;
                    for (let i = 0; i < select.options.length; i++) {
                        const year = parseInt(select.options[i].value);
                        if (year > maxYear) {
                            maxYear = year;
                        }
                    }
                    // Force set to max year
                    select.value = maxYear.toString();
                    
                    // Update the summary display
                    const tifNumber = select.id.replace('yearSelect-', '');
                    updateSummary(tifNumber);
                });
            });

            const metricLabels = {
                'property_tax_extraction': 'Property Tax Extraction',
                'transfers_in': 'Transfers In',
                'expenses': 'Expenses',
                'transfers_out': 'Transfers Out',
                'distribution': 'Distribution',
                'admin_costs': 'Admin Costs',
                'finance_costs': 'Finance Costs'
            };
            
            for (const [metric, label] of Object.entries(metricLabels)) {
                const element = document.getElementById(`${metric}-${tifNumber}`);
                if (element && data[metric] !== undefined) {
                    element.textContent = `$${data[metric].toLocaleString()}`;
                }
            }
        }
        
        // Initialize charts as the user scrolls
        const chartInstances = {};  // Keep track of created charts

        const observer = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const canvas = entry.target;
                    const idParts = canvas.id.split('_');          // ["chart", tifNumber, metric parts...]
                    const tifNumber = idParts[1];
                    const metric = idParts.slice(2).join('_');    // join remaining parts for metric name
                    
                    if (!chartInstances[canvas.id]) {
                        const data = chartData[tifNumber]?.[metric];
                        
                        if (!data) {
                            console.warn(`No chart data for ${canvas.id}`);
                            return;
                        }

                        chartInstances[canvas.id] = new Chart(canvas, {
                            type: 'bar',
                            data: {
                                labels: data.labels,
                                datasets: [{
                                    label: data.title,
                                    data: data.values,
                                    backgroundColor: data.background_colors,
                                    borderColor: data.border_colors,
                                    borderWidth: 1
                                }]
                            },
                            options: {
                                responsive: true,
                                maintainAspectRatio: false,
                                plugins: {
                                    legend: { display: false },
                                    tooltip: {
                                        callbacks: {
                                            label: function(context) {
                                                let label = context.dataset.label || '';
                                                let value = context.parsed.y;
                                                let idx = context.dataIndex;
                                                // Only add bank info for finance_costs
                                                if (metric === "finance_costs" && Array.isArray(data.bank)) {
                                                    let bank = data.bank[idx] || "";
                                                    if (bank) {
                                                        return `${label}: ${value.toLocaleString()} (${bank})`;
                                                    }
                                                }
                                                return `${label}: ${value.toLocaleString()}`;
                                            }
                                        }
                                    }
                                },
                                scales: {
                                    x: { ticks: { maxRotation: 45, font: { size: 10 } } },
                                    y: { beginAtZero: true, ticks: { font: { size: 10 } } }
                                },
                                interaction: { intersect: false, mode: 'index' }
                            }
                        });
                    }

                    observer.unobserve(canvas);  // Only create once
                }
            });
        }, { rootMargin: '0px 0px 200px 0px' });  // preload slightly before viewport

        document.querySelectorAll('.chart-canvas').forEach(canvas => {
            observer.observe(canvas);
        });


    </script>
    <div id="page-bottom"></div>
</body>
</html>'''

    # Write HTML file
    with open(output_html, 'w', encoding='utf-8') as f:
        f.write(html_content)

    elapsed = time.time() - start_time
    print(f"\nAll TIF charts saved to {output_html}")
    print(f"Total runtime: {int(elapsed)//60}m {int(elapsed)%60}s")

def main():
    if len(sys.argv) < 2:
        print("Usage: python create-tif-charts.py <year>")
        sys.exit(1)

    year_arg = int(sys.argv[1])
    create_tif_charts(
        r"C:\Users\w\clonedGitRepos\chi-tif-parser\csvs\chi_tif_data_master.csv",
        year_arg
    )

if __name__ == "__main__":
    main()