# tabula-py Documentation: https://tabula-py.readthedocs.io/en/latest/tabula.html#tabula.io.convert_into
# Please run `pip install tabula` before running this script
import tabula, csv  # For PDF parsing to CSV
import pandas as pd  # For working with data obtained from Tabula
import locale  # For using C-style atoi() function
import json

# TEMPORARY: this will be removed once batch processing is implemented
out = r'c:\sc\out.csv'
# Set Locale for use of atoi() when parsing data
locale.setlocale(locale.LC_NUMERIC, 'en_US.UTF-8')

# Create a Dictionary to store our desired values
outDict = {
    'tif_name': '',
    'tif_number': '',
    '2022_property_tax_extrction': '',
    'cumulative_property_tax_extraction': '',
    '2022_transfers_in': '',
    'cumulative_transfers_in': '',
    '2022_expenses': '',
    'fund_balance_end_2022': '',
    '2022_transfers_out': '',
    '2022_distribution': '',
    'admin_costs': '',
    'finance_costs': '',
    'bank': ''
}

# FUNCTION: String to Float
def stof(toClean):
    # Handle zeroes (which are represented as dashes)
    toClean = toClean.replace('-', '0')
    # Handle bad characters that may or may not occur
    for badChar in ['$','(',')']:
        toClean = toClean.replace(badChar, '')
    # Return the cleaned string as a Float
    return locale.atof(toClean)

# Convert the first data table from the report (page 6) into a CSV
tabula.convert_into(
    # input_path=r"C:\Users\w\clonedGitRepos\chicago2022TIF\mcdc_tif_research\page6_kinzie.pdf", # modify this
    input_path='https://www.chicago.gov/content/dam/city/depts/dcd/tif/21reports/T_052_KinzieAR21.pdf',#r"C:\sc\pdf\T_052_KinzieAR21.pdf",
    output_path=out,  # modify this for batch processing
    pages="6", 
    area=[130, 45, 595, 585], # [top, left, bottom, right]
    # columns=[45, 362.43, 453.04, 528.64],
)

# Open the CSV produced by Tabula
with open(out, 'r') as file:
    reader = csv.reader(file)
    rows = list(reader)

# Merge the first 5 rows to fix the header
header_row = []
for column in zip(*rows):
    column_values = []
    for cell in column[:5]:
        column_values.append(str(cell))
    concatenated_value = ' '.join(column_values)
    header_row.append(concatenated_value.strip())

# Omit the first 5 rows and add the merged header back in
# This overwrites the file stored at 'out' filepath
rows = rows[5:]
rows.insert(0, header_row)
with open(out, 'w', newline='') as file:
    writer = csv.writer(file)
    writer.writerows(rows)

# Get the Pandas DataFrame from the cleaned CSV
df = pd.read_csv(out)
# Remove the Unnamed row (it is full of dollar signs)
df.drop(df.columns[df.columns.str.contains('unnamed',case = False)],axis = 1, inplace = True)

# Obtain the Pandas series for the 'Property Tax Increment' Row
propTaxIncRow = df[df['SOURCE of Revenue/Cash Receipts:'] == 'Property Tax Increment']
# Obtain the Current and Cumulative Strings out of the propTaxIncRow series
propTaxIncCur = propTaxIncRow['Revenue/Cash Receipts for Current Reporting Year'].values[0]
propTaxIncCum = propTaxIncRow['Cumulative Totals of Revenue/Cash Receipts for life of TIF'].values[0]
# Use the user-defined stof() to clean the Strings to Integers for storage in outDict
outDict['2022_property_tax_extrction'] = stof(propTaxIncCur)
outDict['cumulative_property_tax_extraction'] = stof(propTaxIncCum)

# Obtain the Pandas series for the 'Transfers from Municipal Sources' Row
transFromMunRow = df[df['SOURCE of Revenue/Cash Receipts:'] == 'Transfers from Municipal Sources']
# Obtain the Current and Cumulative Strings out of the propTaxIncRow series
transFromMunCur = transFromMunRow['Revenue/Cash Receipts for Current Reporting Year'].values[0]
transFromMunCum = transFromMunRow['Cumulative Totals of Revenue/Cash Receipts for life of TIF'].values[0]
# Use the user-defined stof() to clean the Strings to Integers for storage in outDict
outDict['2022_transfers_in'] = stof(transFromMunCur)
outDict['cumulative_transfers_in'] = stof(transFromMunCum)

# Obtain the Pandas series for the 'Total Expenditures/Cash Disbursements' Row
totExpRow = df[df['SOURCE of Revenue/Cash Receipts:'] == 'Total Expenditures/Cash Disbursements (Carried forward from']
# Obtain the value as a String
totExp = totExpRow['Revenue/Cash Receipts for Current Reporting Year'].values[0]
# Use the user-defined stof() to clean the String to an Integer for storage in outDict
outDict['2022_expenses'] = stof(totExp)

# Obtain the Pandas series for the 'FUND BALANCE, END OF REPORTING PERIOD*' Row
fundBalRow = df[df['SOURCE of Revenue/Cash Receipts:'] == 'FUND BALANCE, END OF REPORTING PERIOD*']
# Obtain the value as a String
fundBal = fundBalRow['Revenue/Cash Receipts for Current Reporting Year'].values[0]
# Use the user-defined stof() to clean the String to an Integer for storage in outDict
outDict['fund_balance_end_2022'] = stof(fundBal)

# Obtain the Pandas series for the 'Transfers to Municipal Sources' Row
transToMunRow = df[df['SOURCE of Revenue/Cash Receipts:'] == 'Transfers to Municipal Sources']
# Obtain the value as a String
transToMun = transToMunRow['Revenue/Cash Receipts for Current Reporting Year'].values[0]
# Use the user-defined stof() to clean the String to an Integer for storage in outDict
outDict['2022_transfers_out'] = stof(transToMun)

# Obtain the Pandas series for the 'Total Expenditures/Cash Disbursements' Row
distSurpRow = df[df['SOURCE of Revenue/Cash Receipts:'] == 'Distribution of Surplus']
# Obtain the value as a String
distSurp = distSurpRow['Revenue/Cash Receipts for Current Reporting Year'].values[0]
# Use the user-defined stof() to clean the String to an Integer for storage in outDict
outDict['2022_distribution'] = stof(distSurp)

print(json.dumps(outDict, indent=4))