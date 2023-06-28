import pandas as pd

# Experiential (from tabula script)
exp = pd.read_csv(r'C:\sc\2020_out.csv')

# Real (from Anthony Moser Google Sheet)
real = pd.read_csv(r'C:\Users\will\clonedGitRepos\chicago2022TIF\TIF_PDF_Parsing\csvs\2020_real.csv')

# Iterate df1 and df2 and print out differences
for index, row in exp.iterrows():
    tif_name = row['tif_name']
    for column in exp.columns:
        if column in ['admin_costs', 'bank', 'tif_name']:
            continue
        value1 = row[column]
        value2 = real.at[index, column]

        # Compare the cell values IF NOT STRING
        if value1 != value2:
            print(f"Difference found in TIF '{tif_name}', column '{column}':")
            print(f"   - Value in exp: {value1}")
            print(f"   - Value in real: {value2}")
            print("--------------------")
