import pandas as pd

# Experiential (from tabula script)
df1 = pd.read_csv(r'C:\Users\will\clonedGitRepos\chicago2022TIF\mcdc_tif_research\csvs\2021_real.csv')

# Real (from Anthony Moser Google Sheet)
df2 = pd.read_csv(r'c:\sc\2021_out.csv')

# Iterate df1 and df2 and print out differences
for index, row in df1.iterrows():
    tif_name = row['tif_name']
    for column in df1.columns:
        value1 = row[column]
        value2 = df2.at[index, column]

        # Compare the cell values
        if value1 != value2:
            print(f"Difference found in TIF '{tif_name}', column '{column}':")
            print(f"   - Value in df1: {value1}")
            print(f"   - Value in df2: {value2}")
            print("--------------------")
