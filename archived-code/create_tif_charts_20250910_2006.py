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
                if yr_int >= 90:        # 1990–1999
                    full_year = 1900 + yr_int
                else:                   # 2000–2089
                    full_year = 2000 + yr_int
                tif_reports[tif_number][str(full_year)] = pdf_link
    return tif_reports

def validate_cumulative_data(df):
    """
    Validate that calculated cumulative values match parsed cumulative values.
    Returns list of discrepancies or empty list if all match.
    For each TIF with discrepancies, identifies the first year where divergence occurs.
    """
    discrepancies = []
    
    # Metrics that have parsed cumulative values we need to validate
    cumulative_metrics = {
        'property_tax_extraction': 'cumulative_property_tax_extraction',
        'transfers_in': 'cumulative_transfers_in'
    }
    
    for tif_name in df['tif_name'].unique():
        tif_df = df[df['tif_name'] == tif_name].sort_values('tif_year')
        
        for base_metric, cumulative_metric in cumulative_metrics.items():
            if base_metric in tif_df.columns and cumulative_metric in tif_df.columns:
                # Calculate cumulative sum from year-to-year values
                calculated_cumulative = tif_df[base_metric].fillna(0).cumsum()
                parsed_cumulative = tif_df[cumulative_metric].fillna(0)
                
                # Find first year where discrepancy occurs
                first_discrepancy_found = False
                for idx, (calc, parsed, year) in enumerate(zip(calculated_cumulative, parsed_cumulative, tif_df['tif_year'])):
                    if abs(calc - parsed) > 0.01:  # Allow for small rounding differences
                        if not first_discrepancy_found:
                            # This is the first discrepancy for this TIF/metric combination
                            discrepancies.append({
                                'tif_name': tif_name,
                                'metric': base_metric.replace('_', ' ').title(),
                                'first_error_year': year,
                                'calculated_at_error': calc,
                                'parsed_at_error': parsed,
                                'difference_at_error': parsed - calc,
                                'latest_year': tif_df['tif_year'].iloc[-1],
                                'calculated_latest': calculated_cumulative.iloc[-1],
                                'parsed_latest': parsed_cumulative.iloc[-1],
                                'total_difference': parsed_cumulative.iloc[-1] - calculated_cumulative.iloc[-1]
                            })
                            first_discrepancy_found = True
    
    return discrepancies

def calculate_cumulative_summary(tif_df):
    """
    Calculate cumulative summary for a TIF including validation and calculated cumulatives.
    """
    # Get latest year data for display
    latest_year_data = tif_df.iloc[-1]
    
    summary = {}
    
    # Parsed cumulative values (already exist in data)
    if 'cumulative_property_tax_extraction' in tif_df.columns:
        summary['Cumulative Property Tax Extraction'] = latest_year_data['cumulative_property_tax_extraction']
    
    if 'cumulative_transfers_in' in tif_df.columns:
        summary['Cumulative Transfers In'] = latest_year_data['cumulative_transfers_in']
    
    # Calculated cumulative values (sum up year-to-year values)
    calculated_metrics = {
        'Cumulative Expenses': 'expenses',
        'Cumulative Transfers Out': 'transfers_out',
        'Cumulative Distribution': 'distribution',
        'Cumulative Admin Costs': 'admin_costs',
        'Cumulative Finance Costs': 'finance_costs'
    }
    
    for display_name, column_name in calculated_metrics.items():
        if column_name in tif_df.columns:
            total = tif_df[column_name].fillna(0).sum()
            summary[display_name] = total
    
    # Add current fund balance
    if 'fund_balance_end' in tif_df.columns:
        summary['Current Fund Balance'] = latest_year_data['fund_balance_end']
    
    return summary

def generate_tif_data(args):
    """Generate chart data for a single TIF."""
    tif_name, tif_number, tif_df, data_columns, links = args

    years = tif_df['tif_year'].astype(str).tolist()
    
    # Calculate cumulative summary
    cumulative_summary = calculate_cumulative_summary(tif_df)
    
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
    
    return tif_name, tif_number, charts_data, links, cumulative_summary

def create_tif_charts(file_path, current_report_year):
    start_time = time.time()
    df = pd.read_csv(file_path)

    # Validate cumulative data before proceeding
    print("Validating cumulative data...")
    discrepancies = validate_cumulative_data(df)
    
    if discrepancies:
        print("\nDATA VALIDATION FAILED!")
        print("Found discrepancies between calculated and parsed cumulative values:")
        print("=" * 90)
        
        for disc in discrepancies:
            print(f"\nTIF: {disc['tif_name']}")
            print(f"Metric: {disc['metric']}")
            print(f"Validation Method: {disc['validation_note']}")
            print(f"First Error Year: {disc['first_error_year']}")
            print(f"  - Calculated cumulative through {disc['first_error_year']}: ${disc['calculated_at_error']:,.2f}")
            print(f"  - Parsed cumulative for {disc['first_error_year']}: ${disc['parsed_at_error']:,.2f}")
            print(f"  - Difference at first error: ${disc['difference_at_error']:,.2f}")
            print(f"Latest Data ({disc['latest_year']}):")
            print(f"  - Calculated total: ${disc['calculated_latest']:,.2f}")
            print(f"  - Parsed total: ${disc['parsed_latest']:,.2f}")
            print(f"  - Total difference: ${disc['total_difference']:,.2f}")
            print("-" * 60)
        
        print(f"\nSUMMARY: {len(discrepancies)} TIF/metric combinations have cumulative data errors.")
        print("The 'First Error Year' indicates where the parsed cumulative value first diverges")
        print("from the calculated sum of year-over-year values.")
        print("\nHTML generation aborted due to data validation failures.")
        return False
    
    print("Data validation passed - all cumulative values match calculated sums.")

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
        
        _, _, charts_data, _, cumulative_summary = generate_tif_data((tif_name, tif_number, tif_df, data_columns, links))
        all_tif_data.append((tif_name, tif_number, charts_data, links, cumulative_summary))
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
        }}
        
        /* Table of Contents Sidebar */
        .toc-toggle {{
            position: fixed;
            top: 20px;
            left: 20px;
            z-index: 1000;
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
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            height: auto;
            padding: 2rem;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        
        .header h1 {{
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
        }}
        
        .header p {{
            font-size: 1.1rem;
            opacity: 0.9;
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
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            color: white;
            text-align: center;
            padding: 1.5rem;
            font-size: 1.5rem;
            font-weight: 600;
            margin: 0;
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
            background: #007bff;
            color: white !important;
            text-decoration: none;
            border-radius: 25px;
            font-weight: 500;
            font-size: 0.9rem;
            transition: all 0.3s ease;
            box-shadow: 0 2px 5px rgba(0,123,255,0.3);
        }}
        
        .year-link:hover {{
            background: #0056b3;
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(0,123,255,0.4);
        }}
        
        .cumulative-summary {{
            background: #f8f9fa;
            padding: 1rem;
            border-bottom: 1px solid #e9ecef;
            font-size: 0.9rem;
        }}
        
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 0.5rem;
            margin-top: 0.5rem;
        }}
        
        .summary-item {{
            display: flex;
            justify-content: space-between;
            padding: 0.25rem 0;
        }}
        
        .summary-label {{
            color: #666;
            font-weight: 500;
        }}
        
        .summary-value {{
            font-weight: 600;
            color: #333;
        }}
        
        .summary-value.negative {{
            color: #dc3545;
        }}
        
        .summary-value.positive {{
            color: #28a745;
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
            text-align: center;
            padding: 2rem;
            color: #666;
            background: white;
            margin-top: 2rem;
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
        }}
    </style>
</head>
<body>
    <!-- Table of Contents -->
    <button class="toc-toggle" onclick="toggleTOC()">☰</button>
    <div class="toc-overlay" onclick="closeTOC()"></div>
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
        html_content += f'<a href="#tif-{tif_number}" class="toc-item">{tif_name}</a>'

    html_content += f'''
        </div>
    </div>
    
    <div class="header">
        <h1>Chicago Tax Increment Financing (TIF) Report Charts</h1>
        <p>Year {current_report_year} • {len(tif_names)} TIF Districts</p>
        <p style="font-size: 1.0rem; opacity: 0.8; margin-top: 0.5rem;">Blue year buttons link directly to PDF reports</p>
    </div>
    '''

    # Add all TIF sections
    for tif_name, tif_number, charts_data, links, cumulative_summary in all_tif_data:
        html_content += f'''
    <div class="tif-page" id="tif-{tif_number}">
        <h2 class="tif-title">{tif_name}</h2>
        '''
        
        if links:
            html_content += '<div class="year-links">'
            for year, url in sorted(links.items()):
                html_content += f'<a href="{url}" target="_blank" class="year-link">{year}</a>'
            html_content += '</div>'
        
        # Add cumulative summary section
        if cumulative_summary:
            html_content += '<div class="cumulative-summary">'
            html_content += '<div class="summary-grid">'
            
            for label, value in cumulative_summary.items():
                if pd.isna(value) or value == 0:
                    formatted_value = "$0"
                    value_class = ""
                else:
                    formatted_value = f"${value:,.0f}"
                    if value < 0:
                        value_class = " negative"
                    elif value > 0:
                        value_class = " positive"
                    else:
                        value_class = ""
                
                html_content += f'''
                <div class="summary-item">
                    <span class="summary-label">{label}:</span>
                    <span class="summary-value{value_class}">{formatted_value}</span>
                </div>'''
            
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

    # Add JavaScript for charts
    html_content += '''
    <div class="footer">
        <p>Generated on ''' + time.strftime("%Y-%m-%d %H:%M:%S") + ''' • Total TIFs: ''' + str(len(tif_names)) + '''</p>
        <p>Click year links to view detailed annual reports (opens in new tab) • Hover over charts for details</p>
    </div>
    
    <script>
        // Chart data
        const chartData = ''' + json.dumps({f"{tif_number}": charts_data for _, tif_number, charts_data, _, _ in all_tif_data}) + ''';
        
        // TOC functions
        function toggleTOC() {
            const sidebar = document.querySelector('.toc-sidebar');
            const overlay = document.querySelector('.toc-overlay');
            
            sidebar.classList.toggle('open');
            overlay.classList.toggle('show');
        }
        
        function closeTOC() {
            const sidebar = document.querySelector('.toc-sidebar');
            const overlay = document.querySelector('.toc-overlay');
            
            sidebar.classList.remove('open');
            overlay.classList.remove('show');
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
</body>
</html>'''

    # Write HTML file
    with open(output_html, 'w', encoding='utf-8') as f:
        f.write(html_content)

    elapsed = time.time() - start_time
    print(f"\nAll TIF charts saved to {output_html}")
    print(f"Total runtime: {int(elapsed)//60}m {int(elapsed)%60}s")
    return True

def main():
    if len(sys.argv) < 2:
        print("Usage: python create-tif-charts.py <year>")
        sys.exit(1)

    year_arg = int(sys.argv[1])
    success = create_tif_charts(
        r"C:\Users\w\clonedGitRepos\chi-tif-parser\csvs\chi_tif_data_master.csv",
        year_arg
    )
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()