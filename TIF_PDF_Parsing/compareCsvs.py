import pandas as pd
import math

# Experiential (from tifParse.py program)
exp = pd.read_csv(r'C:\sc\2020_out.csv')
# exp = exp.drop('tif_year', axis=1)

# Real (from Anthony Moser Google Sheet)
real = pd.read_csv(r"C:\sc\VALIDATE_2020_out.csv")
# real = pd.read_csv(r"C:\sc\idleDemo\2020_out.csv")

# Iterate df1 and df2 and print out differences
for index, row in exp.iterrows():
    tif_name = row['tif_name']
    for column in exp.columns:
        if column in ['admin_costs']: #['admin_costs', 'bank', 'tif_name']:
            continue
        value1 = row[column]
        value2 = real.at[index, column]

        # Compare the cell values IF NOT STRING
        if value1 != value2:
            if type(value1) == float and type(value2) == float:
                if math.isnan(value1) and math.isnan(value2):
                    continue
            print(f"Difference found in TIF '{tif_name}', column '{column}':")
            print(f"   - Value in exp: {value1}")
            print(f"   - Value in real: {value2}")
            # print(type(value1))
            # print(type(value2))
            # print(value1 == value2)
            print("--------------------")
