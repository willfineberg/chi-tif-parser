import os
import sys
import time
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from multiprocessing import Pool, cpu_count

def generate_tif_figure(args):
    """Generate a Matplotlib figure for a single TIF."""
    tif_name, tif_df, data_columns = args
    import matplotlib.pyplot as plt
    import numpy as np

    years = tif_df['tif_year'].astype(str)
    n_cols = 2
    n_rows = int(np.ceil(len(data_columns) / n_cols))
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(8, n_rows*1.5))
    axes = axes.flatten()

    for i, col in enumerate(data_columns):
        values = tif_df[col].fillna(0).values  # NumPy array
        
        axes[i].bar(years, values, color='skyblue')  # all bars blue
        
        # Annotate values (rotate & shrink font)
        for j, v in enumerate(values):
            axes[i].text(j, v + max(values)*0.01, f"{int(v)}",
                        ha='center', va='bottom', fontsize=4, rotation=45)

        # Highlight years where value is zero by changing x-axis tick label color
        for tick_label, v in zip(axes[i].get_xticklabels(), values):
            if v == 0:
                tick_label.set_color('red')  # or gray if preferred

        axes[i].set_title(col, fontsize=6)
        axes[i].tick_params(axis='x', labelrotation=45, labelsize=5)
        axes[i].tick_params(axis='y', labelsize=5)

    for j in range(len(data_columns), len(axes)):
        fig.delaxes(axes[j])

    fig.suptitle(tif_name, fontsize=8)
    plt.tight_layout(rect=[0, 0, 1, 0.95])

    return tif_name, fig

def create_tif_charts(file_path, current_report_year):
    start_time = time.time()

    # Read master data
    df = pd.read_csv(file_path)

    # Output PDF
    out_dir = f"C:\\Users\\w\\clonedGitRepos\\chi-tif-parser\\charts\\{current_report_year}"
    os.makedirs(out_dir, exist_ok=True)
    output_pdf = os.path.join(out_dir, f'{current_report_year}_tif_charts.pdf')

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
    print(f"Processing {len(tif_names)} TIFs in alphabetical order:")
    print(tif_names)

    # Prepare tasks for multiprocessing
    tasks = [
        (tif_name, df[df['tif_name'] == tif_name].sort_values('tif_year'), data_columns)
        for tif_name in tif_names
    ]

    # Generate figures in parallel
    with Pool(processes=cpu_count()) as pool:
        results = pool.map(generate_tif_figure, tasks)

    # Write PDF sequentially in alphabetical order
    with PdfPages(output_pdf) as pdf:
        for idx, (tif_name, fig) in enumerate(sorted(results, key=lambda x: x[0]), 1):
            print(f"{idx}/{len(tif_names)}: {tif_name}")
            pdf.savefig(fig)
            plt.close(fig)

    elapsed = time.time() - start_time
    print(f"\nAll TIF charts saved to {output_pdf}")
    print(f"Total runtime: {int(elapsed)//60}m {int(elapsed)%60}s")

def main():
    if len(sys.argv) < 2:
        print("Usage: python create-tif-charts.py <year>")
        sys.exit(1)

    year_arg = int(sys.argv[1])

    create_tif_charts(
        r"C:\Users\w\clonedGitRepos\chi-tif-parser\csvs\chi-tif-data-master.csv",
        year_arg
    )

if __name__ == "__main__":
    main()
