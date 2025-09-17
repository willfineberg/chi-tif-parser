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

def generate_tif_data(args):
    """Generate chart data for a single TIF."""
    tif_name, tif_number, tif_df, data_columns, links, current_year = args

    years = tif_df['tif_year'].astype(str).tolist()
    
    # Calculate summary data
    cumulative_summary, start_year, end_year, metrics_needing_asterisks = calculate_cumulative_summary(tif_df, current_year)
    
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
    
    return tif_name, tif_number, charts_data, links, cumulative_summary, start_year, end_year, metrics_needing_asterisks

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
        _, _, charts_data, _, cumulative_summary, start_year, end_year, metrics_needing_asterisks = generate_tif_data((tif_name, tif_number, tif_df, data_columns, links, current_report_year))
        all_tif_data.append((tif_name, tif_number, charts_data, links, cumulative_summary, start_year, end_year, metrics_needing_asterisks))
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

        .summary-section {{
            background: #f8f9fa;
            padding: 1.5rem;
            border-bottom: 1px solid #e9ecef;
            font-size: 0.9rem;
            line-height: 1.4;
        }}
        
        .summary-title {{
            text-align: center;
            margin-bottom: 1rem;
            font-weight: 600;
            color: #495057;
            font-size: 1rem;
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
            text-align: center;
            padding: 2rem;
            color: #666;
            background: white;
            margin-top: 2rem;
        }}
        
        .footnote {{
            font-size: 0.85rem;
            color: #6c757d;
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
    for tif_name, tif_number, charts_data, links, cumulative_summary, start_year, end_year, metrics_needing_asterisks in all_tif_data:
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
        
        # Add summary section with non-conditional title
        html_content += '<div class="summary-section">'
        
        # Single summary title for all TIFs
        html_content += '<div class="summary-title">Cumulative Totals</div>'
        
        # Cumulative values grid
        html_content += '<div class="summary-grid">'
        
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
            display_label = f"{label}*" if metric in metrics_needing_asterisks else label
            
            html_content += f'''
            <div class="summary-item">
                <span class="summary-label">{display_label}:</span>
                <span class="summary-value">${value:,.0f}</span>
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
    any_asterisk_needed = any(len(metrics_needing_asterisks) > 0 for _, _, _, _, _, _, _, metrics_needing_asterisks in all_tif_data)

    # Add JavaScript for charts and footer
    footer_content = f'''
    <div class="footer">
        <p>Generated on {time.strftime("%Y-%m-%d %H:%M:%S")} • Total TIFs: {len(tif_names)}</p>
        <p>Click year links to view detailed annual reports (opens in new tab) • Hover over charts for details</p>'''
    
    if any_asterisk_needed:
        footer_content += '''
        <div class="footnote">
            * Cumulative values for TIFs established before 2010 are calculated from 2010 data onwards due to data availability limitations.
        </div>'''
    
    footer_content += '</div>'
    html_content += footer_content

    html_content += '''
    <script>
        // Chart data
        const chartData = ''' + json.dumps({f"{tif_number}": charts_data for _, tif_number, charts_data, _, _, _, _, _ in all_tif_data}) + ''';
        
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
                                                        return `${label}: $${value.toLocaleString()} (${bank})`;
                                                    }
                                                }
                                                return `${label}: $${value.toLocaleString()}`;
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