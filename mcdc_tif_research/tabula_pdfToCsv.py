# Dependencies: tabula, bs4 (install with pip)

# tabula-py Documentation: https://tabula-py.readthedocs.io/en/latest/tabula.html#tabula.io.convert_into
import tabula, csv  # For PDF parsing to CSV
import pandas as pd  # For working with data obtained from Tabula
import locale  # For using C-style atoi() function
import json  # For printing the Dictionary as Structured JSON
import os, tempfile  # For storing the CSVs
import re  # For regexing the TIF ID number from URL
import requests  # For getting an HTML Response to parse with BeautifulSoup
from bs4 import BeautifulSoup  # For HTML parsing the DAR URLs

#                                  #
#                                  #
#       FUNCTION DEFINITIONS       #
#                                  #  
#                                  #

# FUNCTION: String to Float
# RETURNS: Numerical Value as Float
def stof(toClean):
    # Handle zeroes (which are represented as dashes)
    toClean = toClean.replace('-', '0')
    # Handle bad characters that may or may not occur
    for badChar in ['$','(',')']:
        toClean = toClean.replace(badChar, '')
    # Return the cleaned string as a Float
    return locale.atof(toClean)

# FUNCTION: Obtains a list of URLs using BeautifulSoup
# RETURNS: List of URLs
def urlList():
    # Load 2021 TIF reports url
    url = "https://www.chicago.gov/city/en/depts/dcd/supp_info/district-annual-reports--2021-.html"
    r = requests.get(url)
    # Parses through html
    soup = BeautifulSoup(r.text, "html.parser")
    links = soup.find_all(href=True) #contains hyperlink
    # Return a List of pdf links
    pdf_links = ["https://www.chicago.gov" + link['href'] for link in soup.find_all(href=lambda href: href and href.endswith('.pdf'))]
    return pdf_links

# FUNCTION: Convert the first data table from the report (page 6) into a CSV using Tabula
# RETURNS: Dictionary with TIF ID Number as Integer and CSV Filepath as String
def urlToCsv(url, outDir):
    # Obtain ID from URL
    filename = url.split("/")[-1]
    pattern = r"T_(\d+)_"
    match = re.search(pattern, filename)
    if match:
        idNum = int(match.group(1))
        print("File Name: ", filename)
        print("ID Number: ", idNum)
    else:
        print("ID number not found.")
    # ID Found, so store CSV output location
    outFp = os.path.join(outDir, f'{str(idNum)}.csv')
    # Produce a CSV using Tabula
    tabula.convert_into(
        input_path=url,
        output_path=outFp,  # modify this for batch processing
        pages="6", 
        area=[130, 45, 595, 585], # [top, left, bottom, right]
        # columns=[45, 362.43, 453.04, 528.64],
    )
    # Return the URL ID and CSV Filepath
    return {'id': idNum, 'fp': outFp}

# FUNCTION: Cleans the CSV, overwrites it, and loads it back into a Pandas DataFrame
# RETURNS: DataFrame
def cleanCsv(csvFp):
    # Open the CSV produced by Tabula
    with open(csvFp, 'r') as file:
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
    # This overwrites the file stored at 'csvFp' filepath
    rows = rows[5:]
    rows.insert(0, header_row)
    with open(csvFp, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerows(rows)

    # Get the Pandas DataFrame from the partially-cleaned CSV
    df = pd.read_csv(csvFp)
    # Remove the Unnamed row (it is full of dollar signs)
    df.drop(df.columns[df.columns.str.contains('unnamed',case = False)],axis = 1, inplace = True)
    # Overwrite CSV with cleaned one
    df.to_csv(csvFp)
    # Return the DataFrame
    return df

# FUNCTION: Sets Dictionary Values by parsing the CSV
# RETURNS: Output Dictionary
def putDataInDict(df, id):
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
    
    # Set the ID number in the Output Dictionary
    outDict['tif_number'] = id
    
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

    # Return the finalized Dictionary
    return outDict

#                                 #
#                                 #
#        PROCEDURAL SCRIPT        #
#                                 #  
#                                 #

# Create a Temporary Directory to store the temporary CSV files
with tempfile.TemporaryDirectory() as tempDir:
    # Iterate each TIF DAR URL
    for url in urlList():
        # Get the TIF ID and the Filepath to the extracted CSV
        idAndFp = urlToCsv(url, tempDir)
        # Separate ID and FP to two variables
        id = idAndFp['id']
        fp = idAndFp['fp']
        # Pass Filepath to cleanCsv()
        df = cleanCsv(fp)
        # Parse the Data and retrieve the Dictionary of desired values
        finalDict = putDataInDict(df, id)
        # Print structured output to console
        print(json.dumps(finalDict, indent=4))