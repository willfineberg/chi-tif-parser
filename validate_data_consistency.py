import pandas as pd
import sys
from pathlib import Path

# Get year from command line argument
year = sys.argv[1]
output_dir = Path(f"C:/Users/w/clonedGitRepos/chi-tif-parser/csvs/{year}")
output_dir.mkdir(parents=True, exist_ok=True)
output_file = output_dir / f"{year}_validate_data_consistency.csv"

# Load CSV
file_path = r"C:\Users\w\clonedGitRepos\chi-tif-parser\csvs\chi-tif-data-master.csv"
df = pd.read_csv(file_path)

# Ensure proper types
numeric_cols = ['tif_year', 'property_tax_extraction', 'cumulative_property_tax_extraction']
df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')

# Sort data by TIF and year
df = df.sort_values(['tif_name', 'tif_year'])

zero_after_nonzero = []
cumulative_non_increasing = []

for tif_name, group in df.groupby('tif_name'):
    group = group.reset_index(drop=True)
    
    # --- Check property_tax_extraction zeros after first non-zero ---
    first_nonzero_idx = group['property_tax_extraction'].ne(0).idxmax()
    subsequent_zeros = group.loc[first_nonzero_idx + 1:, 'property_tax_extraction'] == 0
    if subsequent_zeros.any():
        years = group.loc[first_nonzero_idx + 1:, 'tif_year'][subsequent_zeros].tolist()
        zero_after_nonzero.append({'tif_name': tif_name, 'years': years})
    
    # --- Check cumulative_property_tax_extraction non-increasing ---
    cum_series = group['cumulative_property_tax_extraction'][first_nonzero_idx:]
    non_increasing_years = cum_series[cum_series.diff() < 0].index
    if len(non_increasing_years) > 0:
        years = group.loc[non_increasing_years, 'tif_year'].tolist()
        cumulative_non_increasing.append({'tif_name': tif_name, 'years': years})

# Output results to console
print("TIFs with property_tax_extraction = 0 after first non-zero year:")
for entry in zero_after_nonzero:
    print(f"{entry['tif_name']}: Years -> {entry['years']}")

print("\nTIFs with cumulative_property_tax_extraction not increasing:")
for entry in cumulative_non_increasing:
    print(f"{entry['tif_name']}: Years -> {entry['years']}")

# Create CSV report
report_data = []

for entry in zero_after_nonzero:
    years_str = ', '.join(map(str, entry['years']))
    report_data.append({
        'tif_name': entry['tif_name'],
        'years': years_str,
        'discrepancy_field': 'property_tax_extraction',
        'status': ''
    })

for entry in cumulative_non_increasing:
    years_str = ', '.join(map(str, entry['years']))
    report_data.append({
        'tif_name': entry['tif_name'],
        'years': years_str,
        'discrepancy_field': 'cumulative_property_tax_extraction',
        'status': ''
    })

# Create DataFrame and save to CSV
report_df = pd.DataFrame(report_data).sort_values(by=['tif_name', 'discrepancy_field'], ascending=[True, True]).reset_index(drop=True)
report_df.to_csv(output_file, index=False)

print(f"\nCSV report saved to: {output_file}")