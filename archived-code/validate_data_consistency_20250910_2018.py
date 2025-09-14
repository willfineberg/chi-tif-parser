import pandas as pd
import sys
from pathlib import Path

def check_zero_after_nonzero(group, field_name, tif_name):
    """Check if a field has zero values after the first non-zero value."""
    results = []
    
    # Find the earliest year with ANY non-zero value (positive or negative)
    non_zero_mask = group[field_name] != 0
    if non_zero_mask.any():
        first_nonzero_idx = non_zero_mask.idxmax()
        
        # Check for zeros in subsequent years (negative values are okay, only flag zeros)
        subsequent_data = group.loc[first_nonzero_idx + 1:]
        zero_mask = subsequent_data[field_name] == 0
        
        # For fund_balance_end, exclude zeros that are the very last data point
        if field_name == 'fund_balance_end' and zero_mask.any():
            # Get indices of zero values
            zero_indices = zero_mask[zero_mask].index
            # Filter out zeros that are the last data point in the entire group
            zero_indices = [idx for idx in zero_indices if idx != group.index[-1]]
            zero_mask = pd.Series(False, index=zero_mask.index)
            for idx in zero_indices:
                zero_mask.loc[idx] = True
        
        if zero_mask.any():
            years = subsequent_data.loc[zero_mask, 'tif_year'].tolist()
            results.append({'tif_name': tif_name, 'years': years, 'discrepancy_field': field_name})
    
    return results

def main():
    # Get year from command line argument
    if len(sys.argv) < 2:
        print("Usage: python validate_data_consistency.py <year>")
        sys.exit(1)
        
    year = sys.argv[1]
    output_dir = Path(f"C:/Users/w/clonedGitRepos/chi-tif-parser/csvs/{year}")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{year}_validate_data_consistency.csv"

    # Load CSV
    file_path = r"C:\Users\w\clonedGitRepos\chi-tif-parser\csvs\chi-tif-data-master.csv"
    df = pd.read_csv(file_path)

    # Ensure proper types
    numeric_cols = ['tif_year', 'property_tax_extraction', 'fund_balance_end']
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')

    # Sort data by TIF and year
    df = df.sort_values(['tif_name', 'tif_year'])

    # Define fields to check
    fields_to_check = ['property_tax_extraction', 'fund_balance_end']
    
    all_results = []

    for tif_name, group in df.groupby('tif_name'):
        group = group.reset_index(drop=True)
        
        # Run checks for each field
        for field in fields_to_check:
            results = check_zero_after_nonzero(group, field, tif_name)  # Pass tif_name as parameter
            all_results.extend(results)

    # Output results to console
    print("TIFs with zero values after first non-zero year:")
    for entry in all_results:
        print(f"{entry['tif_name']} ({entry['discrepancy_field']}): Years -> {entry['years']}")

    # Create CSV report
    report_data = []

    for entry in all_results:
        years_str = ', '.join(map(str, entry['years']))
        report_data.append({
            'tif_name': entry['tif_name'],
            'years': years_str,
            'discrepancy_field': entry['discrepancy_field'],
            'status': '', # Placeholder for manual review status
        })

    # Create DataFrame and save to CSV
    report_df = pd.DataFrame(report_data)
    if not report_df.empty:
        report_df = report_df.sort_values(by=['tif_name', 'discrepancy_field'], ascending=True).reset_index(drop=True)
    report_df.to_csv(output_file, index=False)

    print(f"\nCSV report saved to: {output_file}")
    print(f"Total discrepancies found: {len(all_results)}")

if __name__ == "__main__":
    main()