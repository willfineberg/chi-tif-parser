# Dependencies: tabula-py, bs4, PyPDF2 (install with `pip install -r requirements.txt`)

# tabula-py Documentation: https://tabula-py.readthedocs.io/en/latest/tabula.html#tabula.io.convert_into
import tabula, csv  # For PDF parsing to CSV
import PyPDF2, io  # For finding the right page number to point Tabula to
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

def getPageNumFromText(url, target_text):
    """
    Get the page number containing the specified text in a PDF document.

    Args:
        url (str): The URL of the PDF document.
        target_text (str): The text to search for in the PDF document.

    Returns:
        int or None: The page number (1-indexed) where the target text is found, or None if not found.
    """
    
    # Get the PDF bytes
    response = requests.get(url)
    file = io.BytesIO(response.content)

    # Read the PDF bytes into PyPDF2
    reader = PyPDF2.PdfReader(file)
    
    # Iterate each page and search for the target_text
    num_pages = len(reader.pages)
    for page_num in range(num_pages):
        page = reader.pages[page_num]
        page_text = page.extract_text()

        if target_text in page_text:
            return page_num + 1  # Add 1 to convert from 0-indexed to 1-indexed page number

    # Return None if the target text is not found in any page
    return None

def getNameYear_sec31(url):
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
        pages=getPageNumFromText(url, "SECTION 3.1"), 
        area=[65, 0, 105, 600], # [topY, leftX, bottomY, rightX]
        pandas_options={'header': None},
    )[0]
    # Obtains the Name and Year by table location
    tifName = str(df.iloc[1,1]).replace(" Redevelopment Project Area", "")
    tifYear = str(df.iloc[0,0]).split()[-1]
    # Return name, year
    return tifName, tifYear

def getData_sec31(url, outDir):
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
        pages=6, 
        area=[130, 45, 595, 585], # [topY, leftX, bottomY, rightX]
        # columns=[45, 362.43, 453.04, 528.64],
    )
    # Return the URL ID Integer and CSV Filepath String
    return idNum, outFp

def getData_sec32a_adminCosts(url):
    """
    Obtains the Administration costs from a TIF DAR
    
    Args:
        url (str): The URL of the PDF.
    
    Returns:
        float: The value for Administration Costs from Section 3.2 A
    """
    # pageNum = getPageNumFromText(url, "SCHEDULE OF EXPENDITURES BY STATUTORY CODE")
    # # Bug here -- pages not found
	# # Retrieve the Admin Costs value
    # if pageNum != None:
    #     df = tabula.read_pdf(
    #         input_path=url,
    #         pages=pageNum, 
    #         area=[190, 450, 240, 600], # [topY, leftX, bottomY, rightX]
    #         pandas_options={'header': None},
    #     )[0]
    #     # Isolate the value from the DataFrame and return it
    #     return stof(str(df.iloc[0, df.shape[1]-1]))  # this is bad, we cannot rely on ordering
    # else:
    # SCHEDULE OF EXPENDITURES BY STATUTORY CODE was not found
    # scrapped above approach, not all DARs have this section. ITEMIZED LIST approach below performs better.
    pageNum = getPageNumFromText(url, "ITEMIZED LIST OF ALL EXPENDITURES FROM THE SPECIAL TAX ALLOCATION FUND")
    if pageNum != None:
        # Grab the value with Tabula
        df = tabula.read_pdf(
            input_path=url,
            pages=pageNum,
        )[0]
        # Drop some rows and fill in categories
        df = df.dropna(how='all')
        df = df.rename(columns={df.columns[0]: "Category"})
        df['Category'].fillna(method='ffill', inplace=True)
        # Condense data by grouping
        grouped = df.groupby("Category", as_index=False).agg({'Amounts': 'sum', 'Reporting Fiscal Year': 'first'})
        grouped['Category'] = grouped['Category'].str.replace('\r',' ')
        desiredCategory = "1. Cost of studies, surveys, development of plans, and specifications. Implementation and administration of the redevelopment plan, staff and professional service cost."
        # Obtain desired value and return it as a Float
        adminCosts_32a = stof(grouped.loc[grouped["Category"] == desiredCategory, "Reporting Fiscal Year"].iloc[0])
        return adminCosts_32a
    else:
        # Unable to find Admin Costs, set them to zero
        # Could possibly try summing Admin entries from Section 3.2 B?
        return "ADMIN COSTS NOT PARSED PROPERLY"
        
def getData_sec32b(url):
    """
    Obtains the Administration and Financing costs from Page 11 of a TIF DAR PDF URL
    
    Args:
        url (str): The URL of the PDF.
    
    Returns:
        float: The sum of all costs where 'Service' == 'Administration'
        float: The sum of all costs where 'Service' == 'Financing'
        str: If applicable, the Name(s) of the Bank(s) listed for 'Financing'
    """
    
    # Use PyPDF2 to determine the right Page Number for Section 3.2 B
    pageNum_sec32b = getPageNumFromText(url, "Section 3.2 B")

    # Retrieve the Page 11 Table using Tabula
    df = tabula.read_pdf(
        input_path=url,
        pages=pageNum_sec32b, 
        area=[145, 0, 645, 600], # [topY, leftX, bottomY, rightX]
	    lattice=True
    )[0]

    # Parse each Admin Cost and sum them
    adminCosts_32b = df[df['Service'] == 'Administration']['Amount'].apply(stof).sum()

    # Parse each Finance Cost Amount and sum them
    financeCosts = df[df['Service'] == 'Financing']['Amount'].apply(stof).sum()
    # Obtain the Bank Name(s)
    bankNameList = df[df['Service'] == 'Financing']['Name'].drop_duplicates().tolist()
    bankNames = ', '.join(bankNameList)
    # Return adminCosts and financeCosts
    return adminCosts_32b, financeCosts, bankNames

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

def csvDataToDict(df, id, name, year, adminCosts, financeCosts, bankName=''):
    """
    Sets dictionary values by parsing the CSV.
    
    Args:
        df (pandas.DataFrame): The DataFrame containing the CSV data.
        id (int): The TIF ID number.
        name (str): The name of the TIF.
        year (str): The year of the TIF.
        adminCosts (float): The total Administration Costs from Page 11.
        finanaceCosts (float): The total Finanace Costs from Page 11.
        bankName (str): If financeCosts != 0, bankName is provided from Page 11.
    
    Returns:
        dict: The output dictionary.
    """

    # Create a Dictionary to store our desired values
    outDict = {
        #'tif_year': year,
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
        'admin_costs': adminCosts,
        'finance_costs': financeCosts,
        'bank': bankName
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

# Set Locale for use of atoi() when parsing data (utilized in stof() function)
locale.setlocale(locale.LC_NUMERIC, 'en_US.UTF-8')

# MODIFY THIS: Filepath to write finalDict data to for each url
csvFp = r'c:\sc\2010_out.csv'

# DAR URLs to Parse
url2021 = "https://www.chicago.gov/city/en/depts/dcd/supp_info/district-annual-reports--2021-.html"
url2020 = "https://www.chicago.gov/city/en/depts/dcd/supp_info/district-annual-reports--2020-.html"
url2010 = 'https://www.chicago.gov/city/en/depts/dcd/supp_info/district_annual_reports2010.html'
url2013 = 'https://www.chicago.gov/city/en/depts/dcd/supp_info/district-annual-reports--2013-.html'

# Create a list to store the dictionaries for each TIF
dictList = []

# Create a Temporary Directory to store the temporary CSV files
with tempfile.TemporaryDirectory() as tempDir:
    # Iterate each TIF DAR URL
    for url in urlList(url2013):
        # Get the TIF ID and the Filepath to the extracted CSV (for Page 6 TABLE)
        id, fp = getData_sec31(url, tempDir)
        # Get the TIF Name and Year (from Page 6)
        name, year = getNameYear_sec31(url)

        # Get the Administration Costs (modify this to get a 2nd financing cost value too???)
        adminCosts_32a = getData_sec32a_adminCosts(url)
        # Get Finance Data and Bank Name(s)
        adminCosts_32b, financeCosts, bankName = getData_sec32b(url)

        # REVISIT: Parse Finance from Sec 3.2 A too? compare it?

        # For debugging; remove these prints
        print(adminCosts_32a)
        print(adminCosts_32b)
        # Decide which Admin Cost we want to use
        if adminCosts_32b >= adminCosts_32a:
            adminCosts = adminCosts_32b
        else:
            adminCosts = adminCosts_32a

        # Pass Filepath to cleanCsv()
        df = cleanCsv(fp)
        # Parse the Data and retrieve the Dictionary of desired values
        curDict = csvDataToDict(df, id, name, year, adminCosts, financeCosts, bankName)
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
    print("CSV File saved to: " + csvFp)
    