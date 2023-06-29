# Dependencies: tabula-py, bs4, PyPDF2, requests (install with `pip install -r requirements.txt`)

# tabula-py Documentation: https://tabula-py.readthedocs.io/en/latest/tabula.html#tabula.io.convert_into
import tabula, csv  # For PDF parsing to CSV
import PyPDF2, io  # For finding the right page number to point Tabula to
import locale  # For using C-style atoi() function
import json  # For printing the Dictionary as Structured JSON
import re  # For regexing the TIF ID number from URL
import requests  # For getting an HTML Response to parse with BeautifulSoup
import sys, os  # For arg parsing and filepath management
import time  # For reporting program runtime
import pandas as pd  # For data cleaning
import concurrent.futures  # For threading
from bs4 import BeautifulSoup  # For HTML parsing the DAR URLs

class Tools:
    """A collection of utility functions for TIF data parsing and processing."""

    def stof(toClean):
        """Converts a string to a float."""

        if '-' in toClean:
            # Handle zeroes (which are represented as dashes)
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
        """Obtains a list of TIF DAR URLs using BeautifulSoup."""

        # Load 2021 TIF reports URL
        r = requests.get(url)
        # Parses through HTML
        soup = BeautifulSoup(r.text, "html.parser")
        links = soup.find_all(href=True) #contains hyperlink
        # Return a List of PDF links
        pdf_links = ["https://www.chicago.gov" + link['href'] for link in soup.find_all(href=lambda href: href and href.endswith('.pdf'))]
        return pdf_links

    def getPageNumFromText(pdf, target_text):
        """Get the page number containing the specified text in a PDF document; return an int or None."""   

        # Read the PDF bytes into PyPDF2
        reader = PyPDF2.PdfReader(pdf)
        # Iterate each page and search for the target_text
        num_pages = len(reader.pages)
        for page_num in range(num_pages):
            page = reader.pages[page_num]
            page_text = page.extract_text()
            if target_text in page_text:
                return page_num + 1  # Add 1 to convert from 0-indexed to 1-indexed page number
        # Return None if the target text is not found in any page
        return None

    def fixHeader(df, startRow, endRow):
        """Gets the header row by concatenating multiple rows; returns a list of column headers"""
        header_row = df.iloc[startRow:endRow].fillna('').apply(lambda x: ' '.join(x.str.strip()), axis=0).tolist()
        header_row = [header.strip() for header in header_row]
        header_row = [header for header in header_row if header]
        # Omit the first rows and add the merged header back in
        df = df.iloc[endRow:].reset_index(drop=True)
        df.columns = header_row
        return df

class YearParse:
    """An Object that obtains and stores one year's worth of DAR Objects"""
    def __init__(self, yearUrl):
        self.year = None
        self.yearUrl = yearUrl
        self.urlList = Tools.urlList(yearUrl)
        self.termTable = None
        self.darList = []
        self.dictList = []

    def buildCsvFromDicts(self, csvFp):
        """Create a CSV file from a list of Dictionaries. Each row is one Dictionary."""

        # Get the list of keys from the first dictionary in the list
        if len(self.dictList) > 0 :
            fieldnames = list(self.dictList[0].keys())
            # Write the data to the CSV file
            with open(csvFp, 'w', newline='') as csvfile:
                # Open the CSV and pass the fieldnames
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                # Write the header row (uses fieldnames)
                writer.writeheader()
                # Write the data rows (each dict in dictList is one TIF)
                for dict in self.dictList:
                    writer.writerow(dict)
            print("CSV File saved to: " + csvFp)
        else:
            print('Unable to save CSV: No data found in dictList')
    
    def run(self, outDir):
        startTime = time.time()
        # Iterate each TIF DAR URL in the specified year
        isFirst = True
        if isFirst:
            # Obtain Year and Termination Table if this is the first url
            isFirst = False
            dar = DAR(self.urlList[0])
            self.year = dar.outDict['tif_year']
            self.termTable = dar.parseTermTable_sec1(outDir)
            # Append to dictList and print structured output to console
            self.darList.append(dar)
            self.dictList.append(dar.outDict) 
            print(json.dumps(dar.outDict, indent=4))
        # Iterate each TIF DAR URL except the first one
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_dar = {executor.submit(DAR, url): url for url in self.urlList[1:]}
            # Iterate the completed futures to obtain the DAR object data
            for future in concurrent.futures.as_completed(future_to_dar):
                # url = future_to_dar[future]
                dar = future.result()
                self.darList.append(dar)
                self.dictList.append(dar.outDict)
                print(json.dumps(dar.outDict, indent=4))
        # After one year is parsed, store output in a CSV
        self.buildCsvFromDicts(os.path.join(outDir, f'{self.year}_out.csv')) # TODO: command line arg for output directory?
        # Print the runtime in minutes:seconds format
        endTime = time.time()
        runtime_seconds = endTime - startTime
        runtime_minutes = runtime_seconds // 60
        runtime_seconds %= 60
        print(f"Program runtime: {int(runtime_minutes)} minutes {int(runtime_seconds)} seconds")

class DAR:
    """Parses and stores data from a single TIF DAR PDF."""

    def __init__(self, url):
        """Initializes a DAR object."""

        self.pdfUrl = url
        self.pdf = io.BytesIO(requests.get(url).content)
        self.sec31 = Tools.getPageNumFromText(self.pdf, 'SECTION 3.1')
        self.sec32a = Tools.getPageNumFromText(self.pdf, 'ITEMIZED LIST OF ALL EXPENDITURES FROM THE SPECIAL TAX ALLOCATION FUND')
        self.sec32b = Tools.getPageNumFromText(self.pdf, "Section 3.2 B")
        self.outDict = {}
        # Populate the outDict dictionary using methods.
        self.parseNameAndYear_sec31() 
        self.sec31_df = self.parseIdAndData_sec31()
        self.sec32b_df = self.parseAdminFinanceBank_sec32b()

    def parseTermTable_sec1(self, outDir):
        """Saves the Termination Table CSV to outDir"""
        dfs = tabula.read_pdf(
            input_path=self.pdf,
            pages='1-4', # adjust dynamically based on year?
            pandas_options={'header': None},
        )
        # Drop first column from first page of the table (it is empty)
        dfs[0] = dfs[0].drop(0, axis=1)
        dfs[0].columns = [0,1,2]
        # Combine all the DataFrames into one
        df = pd.concat(dfs, ignore_index=True)
        # Fix the header and indicies
        df = Tools.fixHeader(df, 1, 3)
        # Save the DataFrame to a CSV in outDir
        df.to_csv(os.path.join(outDir, f"{self.outDict['tif_year']}_termTable.csv"))
        # Return the DataFrame
        return df

    def parseNameAndYear_sec31(self):
        """Obtains the name and year of a TIF from a PDF."""

        # Makes a Dataframe out of Section 3.1 (usually Page 6)
        df = tabula.read_pdf(
            input_path=self.pdf,
            pages=self.sec31, 
            area=[65, 0, 105, 600], # [topY, leftX, bottomY, rightX]
            pandas_options={'header': None},
        )[0]
        # Obtains the name and year by table location
        tifName = str(df.iloc[1,1]).replace(" Redevelopment Project Area", "")
        tifYear = str(df.iloc[0,0]).split()[-1]
        # Set the TIF name and year
        self.outDict['tif_name'] = tifName
        self.outDict['tif_year'] = tifYear

    def parseIdAndData_sec31(self):
        """Converts TIF Section 3.1 into a CSV and parses the values; returns ID number or None"""

        # Obtain ID from URL
        filename = self.pdfUrl.split("/")[-1]
        pattern = r"T_(\d+)_"
        match = re.search(pattern, filename)
        if match:
            idNum = int(match.group(1))
            self.outDict['tif_number'] = idNum
        else:
            print("ID number not found.")
            return None
        # *STEP 1: READ PDF INTO DATAFRAME
        df = tabula.read_pdf(
            input_path=self.pdf,
            pages=self.sec31, 
            area=[130, 45, 595, 585], # [topY, leftX, bottomY, rightX]
            # ! area above works only for 2019-onward. 
            # TODO: need to run tests for pre-2018 without area and update cleanDf() accordingly
            # columns=[45, 362.43, 453.04, 528.64],
        )[0]
        # *STEP 2: CLEAN DATAFRAME HEADER
        # Remove unnamed column full of dollar signs
        df = df.drop('Unnamed: 1', axis=1) # ? is this bad? does dollar sign always get its own column?
        # Merge the first 5 rows to fix the header
        df = Tools.fixHeader(df, 0, 4)
        #df.drop(df.columns[df.columns.str.contains('unnamed',case = False)],axis = 1, inplace = True)
        # *STEP 3: PARSE CLEANED DATAFRAME INTO DICTIONARY
        # Obtain the Pandas series for the 'Property Tax Increment' Row
        propTaxIncRow = df[df['SOURCE of Revenue/Cash Receipts:'] == 'Property Tax Increment']
        # Obtain the Current and Cumulative Strings out of the propTaxIncRow series
        propTaxIncCur = propTaxIncRow['Revenue/Cash Receipts for Current Reporting Year'].values[0]
        propTaxIncCum = propTaxIncRow['Totals of Revenue/Cash Receipts for life of TIF'].values[0]
        # Use the user-defined Tools.stof() to clean the Strings to Integers for storage in self.outDict
        self.outDict['property_tax_extraction'] = Tools.stof(propTaxIncCur)
        self.outDict['cumulative_property_tax_extraction'] = Tools.stof(propTaxIncCum)

        # Obtain the Pandas series for the 'Transfers from Municipal Sources' Row
        transFromMunRow = df[df['SOURCE of Revenue/Cash Receipts:'] == 'Transfers from Municipal Sources']
        # Obtain the Current and Cumulative Strings out of the propTaxIncRow series
        transFromMunCur = transFromMunRow['Revenue/Cash Receipts for Current Reporting Year'].values[0]
        transFromMunCum = transFromMunRow['Totals of Revenue/Cash Receipts for life of TIF'].values[0]
        # Use the user-defined Tools.stof() to clean the Strings to Integers for storage in self.outDict
        self.outDict['transfers_in'] = Tools.stof(transFromMunCur)
        self.outDict['cumulative_transfers_in'] = Tools.stof(transFromMunCum)

        # Obtain the Pandas series for the 'Total Expenditures/Cash Disbursements' Row
        totExpRow = df[df['SOURCE of Revenue/Cash Receipts:'] == 'Total Expenditures/Cash Disbursements (Carried forward from']
        # Obtain the value as a String
        totExp = totExpRow['Revenue/Cash Receipts for Current Reporting Year'].values[0]
        # Use the user-defined Tools.stof() to clean the String to an Integer for storage in self.outDict
        self.outDict['expenses'] = Tools.stof(totExp)

        # Obtain the Pandas series for the 'FUND BALANCE, END OF REPORTING PERIOD*' Row
        fundBalRow = df[df['SOURCE of Revenue/Cash Receipts:'] == 'FUND BALANCE, END OF REPORTING PERIOD*']
        # Obtain the value as a String
        fundBal = fundBalRow['Revenue/Cash Receipts for Current Reporting Year'].values[0]
        # Use the user-defined Tools.stof() to clean the String to an Integer for storage in self.outDict
        self.outDict['fund_balance_end'] = Tools.stof(fundBal)

        # Obtain the Pandas series for the 'Transfers to Municipal Sources' Row
        transToMunRow = df[df['SOURCE of Revenue/Cash Receipts:'] == 'Transfers to Municipal Sources']
        # Obtain the value as a String
        transToMun = transToMunRow['Revenue/Cash Receipts for Current Reporting Year'].values[0]
        # Use the user-defined Tools.stof() to clean the String to an Integer for storage in self.outDict
        self.outDict['transfers_out'] = Tools.stof(transToMun)

        # Obtain the Pandas series for the 'Total Expenditures/Cash Disbursements' Row
        distSurpRow = df[df['SOURCE of Revenue/Cash Receipts:'] == 'Distribution of Surplus']
        # Obtain the value as a String
        distSurp = distSurpRow['Revenue/Cash Receipts for Current Reporting Year'].values[0]
        # Use the user-defined Tools.stof() to clean the String to an Integer for storage in self.outDict
        self.outDict['distribution'] = Tools.stof(distSurp)

        # Return Section 3.1 DataFrame for Storage
        return df

    # * SECTION 3.2 A PARSING -- repurpose this for finance parsing from sec32a?
    # TODO: REVISIT: Parse Finance from Sec 3.2 A too? compare it?
    # def getAdmin_sec32a(self, pdf, pageNum):
        """Obtains the Administration costs from a TIF DAR."""

        # if pageNum != None:
        #     # Grab the value with Tabula
        #     df = tabula.read_pdf(
        #         input_path=self.pdf,
        #         pages=pageNum,
        #     )[0]
        #     # Drop some rows and fill in categories
        #     df = df.dropna(how='all')
        #     df = df.rename(columns={df.columns[0]: "Category"})
        #     df['Category'].fillna(method='ffill', inplace=True)
        #     # Condense data by grouping
        #     grouped = df.groupby("Category", as_index=False).agg({'Amounts': 'sum', 'Reporting Fiscal Year': 'first'})
        #     grouped['Category'] = grouped['Category'].str.replace('\r',' ')
        #     desiredCategory = "1. Cost of studies, surveys, development of plans, and specifications. Implementation and administration of the redevelopment plan, staff and professional service cost."
        #     # Obtain desired value and return it as a Float
        #     adminCosts_32a = Tools.stof(grouped.loc[grouped["Category"] == desiredCategory, "Reporting Fiscal Year"].iloc[0])
        #     # Set self.outDict with the parsed AdminCost
        #     self.outDict['admin_costs'] = adminCosts_32a
        # else:
        #     # Unable to find Admin Costs, set them to zero
        #     # Could possibly try summing Admin entries from Section 3.2 B?
        #     return "ADMIN COSTS NOT PARSED PROPERLY"

    def parseAdminFinanceBank_sec32b(self):
        """Obtains the Administration and Financing costs from Page 11 of a TIF DAR PDF."""

        # Retrieve the Page 11 Table using Tabula
        df = tabula.read_pdf(
            input_path=self.pdf,
            pages=self.sec32b, 
            area=[145, 0, 645, 600], # [topY, leftX, bottomY, rightX]
            lattice=True
        )[0]
        # Parse each Admin Cost and sum them
        adminCosts = df[df['Service'] == 'Administration']['Amount'].apply(Tools.stof).sum()
        # Parse each Finance Cost Amount and sum them
        financeCosts = df[df['Service'] == 'Financing']['Amount'].apply(Tools.stof).sum()
        # Obtain the Bank Name(s)
        bankNameList = df[df['Service'] == 'Financing']['Name'].drop_duplicates().tolist()
        bankNames = ', '.join(bankNameList)
        # Set the adminCosts, financeCosts, and bankNames
        self.outDict['admin_costs'] = adminCosts
        self.outDict['finance_costs'] = financeCosts
        self.outDict['bank'] = bankNames
        # Return the DataFrame for storage
        return df

def main():
    # Use cmd line arg for year
    if len(sys.argv) < 2:
        print('BAD USAGE\nUsage: py tifParse.py [year]')
        return
    year = sys.argv[1]
    # * MODIFY THIS: Filepath to write finalDict data to for each url
    outDir = r'c:\sc'
    # Set Locale for use of atoi() when parsing data (utilized in Tools.stof() function)
    locale.setlocale(locale.LC_NUMERIC, 'en_US.UTF-8')
    # DAR URLs to Parse
    darYearsUrls = {
        "2012": "https://www.chicago.gov/content/city/en/depts/dcd/supp_info/district_annual_reports2012.html",
        "2013": "https://www.chicago.gov/city/en/depts/dcd/supp_info/district-annual-reports--2013-.html",
        "2014": "https://www.chicago.gov/city/en/depts/dcd/supp_info/district-annual-reports--2014-.html",
        "2015": "https://www.chicago.gov/city/en/depts/dcd/supp_info/district-annual-reports--2015-.html",
        "2016": "https://www.chicago.gov/city/en/depts/dcd/supp_info/2016TIFAnnualReports.html",
        "2017": "https://www.chicago.gov/city/en/depts/dcd/supp_info/district-annual-reports--2017-.html",
        "2018": "https://www.chicago.gov/city/en/depts/dcd/supp_info/district-annual-reports--2018-.html",
        "2019": "https://www.chicago.gov/city/en/depts/dcd/supp_info/district-annual-reports--2019-.html",
        "2020": "https://www.chicago.gov/city/en/depts/dcd/supp_info/district-annual-reports--2020-.html",
        "2021": "https://www.chicago.gov/city/en/depts/dcd/supp_info/district-annual-reports--2021-.html",
        "2022": "https://www.chicago.gov/city/en/depts/dcd/supp_info/district-annual-reports--2022-.html",
        "2023": "https://www.chicago.gov/city/en/depts/dcd/supp_info/district-annual-reports--2023-.html"
    }
    # ! Confirm this works properly
    yp = YearParse(darYearsUrls[year])
    yp.run(outDir)

if __name__ == "__main__":
    main()