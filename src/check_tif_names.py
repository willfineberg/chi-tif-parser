import pandas as pd

# ! Use this after the data has been merged to see if GIS updates will be required

def report_tif_differences(file_path, current_year, compare_year):
    # Read the master dataset
    df = pd.read_csv(file_path)

    # Filter for each year
    df_current = df[df['tif_year'] == current_year]
    df_compare = df[df['tif_year'] == compare_year]

    # Check uniqueness
    if df_current['tif_name'].duplicated().any():
        print(f"Warning: duplicate tif_names found in {current_year}")
    if df_compare['tif_name'].duplicated().any():
        print(f"Warning: duplicate tif_names found in {compare_year}")

    # Get the unique tif_names explicitly
    tif_current = set(df_current['tif_name'].drop_duplicates())
    tif_compare = set(df_compare['tif_name'].drop_duplicates())

    # Compare
    added = tif_current - tif_compare
    removed = tif_compare - tif_current

    print(f"TIFs added in {current_year}: {added}")
    print(f"TIFs removed from {compare_year} to {current_year}: {removed}")

report_tif_differences(r"C:\Users\w\clonedGitRepos\chi-tif-parser\csvs\chi_tif_data_master.csv", 2025, 2024)