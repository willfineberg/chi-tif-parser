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

def stof(toClean):
    """
    Converts a string to a float.
    
    Args:
        toClean (str): The string to be converted.
    
    Returns:
        float: The numerical value as a float.
    """

    # Set Locale for use of atoi() when parsing data
    locale.setlocale(locale.LC_NUMERIC, 'en_US.UTF-8')
    # Handle zeroes (which are represented as dashes)
    if '-' in toClean:
        return 0.0
    # Remove stray dollar signs to prepare for locale.atof() parsing
    toClean = toClean.replace('$', '').strip()
    # If enclosed in parenthesis, number is negative. So we try to Regex a value out of ()...
    negPattern = r'\((.+)\)'
    match = re.match(negPattern, toClean)
    if match:
        # Number is negative, so we update the Float return value appropriately
        return -1 * locale.atof(match.group(1))
    else:
        # Number is positive, so return the cleaned string as a Float
        return locale.atof(toClean)

def urlList(url):
    """
    Obtains a list of URLs using BeautifulSoup.
    
    Returns:
        list: A list of URLs.
    """

    # Load 2021 TIF reports URL
    r = requests.get(url)
    # Parses through HTML
    soup = BeautifulSoup(r.text, "html.parser")
    links = soup.find_all(href=True) #contains hyperlink
    # Return a List of PDF links
    pdf_links = ["https://www.chicago.gov" + link['href'] for link in soup.find_all(href=lambda href: href and href.endswith('.pdf'))]
    return pdf_links

def getNameYear_p6(url):
    """
    Obtains the Name and Year of a TIF from a PDF URL.
    
    Args:
        url (str): The URL of the PDF.
    
    Returns:
        str: The name of the TIF as a string.
        str: The year of the TIF as a string.
    """

    # Makes a Dataframe out of the top part of Page 6
    df = tabula.read_pdf(
        input_path=url,
        pages="6", 
        area=[65, 0, 105, 600], # [topY, leftX, bottomY, rightX]
        pandas_options={'header': None},
    )
    # Obtains the Name and Year by table location
    tifName = df[0].iloc[1,1].replace(" Redevelopment Project Area", "")
    tifYear = df[0].iloc[0,0].split()[-1]
    # Return name, year
    return tifName, tifYear

def getData_p6(url, outDir):
    """
    Converts the first data table from the report (page 6) into a CSV using Tabula.
    
    Args:
        url (str): The URL of the PDF.
        outDir (str): The directory path to store the extracted CSV.
    
    Returns:
        int: The TIF ID number.
        str: The filepath of the extracted CSV.
    """

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
        area=[130, 45, 595, 585], # [topY, leftX, bottomY, rightX]
        # columns=[45, 362.43, 453.04, 528.64],
    )
    # Return the URL ID Integer and CSV Filepath String
    return idNum, outFp

def cleanCsv(csvFp):
    """
    Cleans the CSV, overwrites it, and loads it back into a Pandas DataFrame.
    
    Args:
        csvFp (str): The filepath of the CSV.
    
    Returns:
        pandas.DataFrame: The cleaned DataFrame.
    """

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

def csvDataToDict(df, id, name, year):
    """
    Sets dictionary values by parsing the CSV.
    
    Args:
        df (pandas.DataFrame): The DataFrame containing the CSV data.
        id (int): The TIF ID number.
        name (str): The name of the TIF.
        year (str): The year of the TIF.
    
    Returns:
        dict: The output dictionary.
    """

    # Create a Dictionary to store our desired values
    outDict = {
        'tif_year': year,
        'tif_name': name,
        'tif_number': '',
        f'{year}_property_tax_extrction': '',
        'cumulative_property_tax_extraction': '',
        f'{year}_transfers_in': '',
        'cumulative_transfers_in': '',
        f'{year}_expenses': '',
        f'fund_balance_end_{year}': '',
        f'{year}_transfers_out': '',
        f'{year}_distribution': '',
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
    outDict[f'{year}_property_tax_extrction'] = stof(propTaxIncCur)
    outDict['cumulative_property_tax_extraction'] = stof(propTaxIncCum)

    # Obtain the Pandas series for the 'Transfers from Municipal Sources' Row
    transFromMunRow = df[df['SOURCE of Revenue/Cash Receipts:'] == 'Transfers from Municipal Sources']
    # Obtain the Current and Cumulative Strings out of the propTaxIncRow series
    transFromMunCur = transFromMunRow['Revenue/Cash Receipts for Current Reporting Year'].values[0]
    transFromMunCum = transFromMunRow['Cumulative Totals of Revenue/Cash Receipts for life of TIF'].values[0]
    # Use the user-defined stof() to clean the Strings to Integers for storage in outDict
    outDict[f'{year}_transfers_in'] = stof(transFromMunCur)
    outDict['cumulative_transfers_in'] = stof(transFromMunCum)

    # Obtain the Pandas series for the 'Total Expenditures/Cash Disbursements' Row
    totExpRow = df[df['SOURCE of Revenue/Cash Receipts:'] == 'Total Expenditures/Cash Disbursements (Carried forward from']
    # Obtain the value as a String
    totExp = totExpRow['Revenue/Cash Receipts for Current Reporting Year'].values[0]
    # Use the user-defined stof() to clean the String to an Integer for storage in outDict
    outDict[f'{year}_expenses'] = stof(totExp)

    # Obtain the Pandas series for the 'FUND BALANCE, END OF REPORTING PERIOD*' Row
    fundBalRow = df[df['SOURCE of Revenue/Cash Receipts:'] == 'FUND BALANCE, END OF REPORTING PERIOD*']
    # Obtain the value as a String
    fundBal = fundBalRow['Revenue/Cash Receipts for Current Reporting Year'].values[0]
    # Use the user-defined stof() to clean the String to an Integer for storage in outDict
    outDict[f'fund_balance_end_{year}'] = stof(fundBal)

    # Obtain the Pandas series for the 'Transfers to Municipal Sources' Row
    transToMunRow = df[df['SOURCE of Revenue/Cash Receipts:'] == 'Transfers to Municipal Sources']
    # Obtain the value as a String
    transToMun = transToMunRow['Revenue/Cash Receipts for Current Reporting Year'].values[0]
    # Use the user-defined stof() to clean the String to an Integer for storage in outDict
    outDict[f'{year}_transfers_out'] = stof(transToMun)

    # Obtain the Pandas series for the 'Total Expenditures/Cash Disbursements' Row
    distSurpRow = df[df['SOURCE of Revenue/Cash Receipts:'] == 'Distribution of Surplus']
    # Obtain the value as a String
    distSurp = distSurpRow['Revenue/Cash Receipts for Current Reporting Year'].values[0]
    # Use the user-defined stof() to clean the String to an Integer for storage in outDict
    outDict[f'{year}_distribution'] = stof(distSurp)

    # Return the finalized Dictionary
    return outDict

#                                 #
#                                 #
#        BELOW IS THE SCRIPT      #
#   SCRIPT USES FUNCTIONS ABOVE   #  
#                                 #
#                                 #

# MODIFY THIS: Filepath to write finalDict data to for each url
csvFp = r'c:\sc\out.csv'

# DAR URLs to Parse
url2021 = "https://www.chicago.gov/city/en/depts/dcd/supp_info/district-annual-reports--2021-.html"
url2020 = "https://www.chicago.gov/city/en/depts/dcd/supp_info/district-annual-reports--2020-.html"

# Create a list to store the dictionaries for each TIF
dictList = []

# Create a Temporary Directory to store the temporary CSV files
with tempfile.TemporaryDirectory() as tempDir:
    # Iterate each TIF DAR URL
    for url in urlList(url2020):
        # Get the TIF ID and the Filepath to the extracted CSV (for Page 6 TABLE)
        id, fp = getData_p6(url, tempDir)
        # Get the TIF Name and Year (from Page 6)
        name, year = getNameYear_p6(url)
        # Pass Filepath to cleanCsv()
        df = cleanCsv(fp)
        # Parse the Data and retrieve the Dictionary of desired values
        curDict = csvDataToDict(df, id, name, year)
        # Print structured output to console
        dictList.append(curDict)
        print(json.dumps(curDict, indent=4))

# Get the list of keys from the first dictionary in the list
fieldnames = list(dictList[0].keys())

# Write the data to the CSV file
with open(csvFp, 'w', newline='') as csvfile:
    # Open the CSV and pass the fieldnames
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    # Write the header row (uses fieldnames)
    writer.writeheader()
    # Write the data rows (each dict in dictList is one TIF)
    for dict in dictList:
        writer.writerow(dict)
    