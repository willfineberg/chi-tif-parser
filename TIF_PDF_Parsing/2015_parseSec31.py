import locale, sys
import tabula, csv
import pandas as pd
import PyPDF2, io
import requests
import json
import re
from math import isnan
from bs4 import BeautifulSoup

def main():
    dictList = []
    for url in Tools.urlList("https://www.chicago.gov/city/en/depts/dcd/supp_info/district-annual-reports--2015-.html"):
        # Reset outDict
        outDict = {}
        # Obtain PDF bytes
        pdf = io.BytesIO(requests.get(url).content)
        # Obtain Section 3.1 Page Number
        sec31 = Tools.getPageNumFromText(pdf, 'SECTION 3.1')
        # TODO: grab the desired page and run ocrmypdf on it to redo the default low-quality OCR

        # ! Parse Section 3.1 Name and Year into outDict
        df = tabula.read_pdf(
            input_path=pdf,
            pages=sec31, 
            area=[80, 0, 105, 600], # [topY, leftX, bottomY, rightX]
            pandas_options={'header': None},
        )[0]
        # Obtains the name and year by table location
        tifName = str(df.iloc[1,1]).replace(" Redevelopment Project Area", "")
        tifYear = str(df.iloc[0,0]).split()[-1]
        # Set the TIF name and year
        outDict['tif_name'] = tifName.strip()
        outDict['tif_year'] = tifYear.strip()
        # Add current outDict to dictList
        dictList.append(outDict)
        
        # ! Parse Section 3.1 Datatable into outDict
        outDict = parseIdAndData_sec31(pdf, url, sec31, outDict)

        print(json.dumps(outDict, indent=4))

class Tools:
    """A collection of utility functions for TIF data parsing and processing."""

    def stof(toClean):
        """Converts a string to a float."""
        locale.setlocale(locale.LC_NUMERIC, 'en_US.UTF-8')
        if isinstance(toClean, str):
            # Remove stray dollar signs and/or asterisks to prepare for locale.atof() parsing
            toClean = toClean.replace('$', '').replace('*', '').replace('_', '').replace('~', '').replace('.', '').replace('I', '').replace(';', '').replace(' ', '').strip()
            # toClean is a String
            if '-' in toClean and len(toClean) <= 1:
                # Handle zeroes (for >= 2019, represented as dashes)
                return 0.0
            if len(toClean) <= 0:
                # Handle zeroes (for <= 2018, no representation)
                return 0.0
            # If enclosed in parenthesis, number is negative. So we try to Regex a value out of ()...
            negPattern = r'\((.+)\)'
            match = re.match(negPattern, toClean)
            try:
                if match:
                    # Number is negative, so we update the Float return value appropriately
                    return -1 * locale.atof(match.group(1))
                else:
                    # Number is positive, so return the cleaned string as a Float
                    return locale.atof(toClean)
            except ValueError as e:
                print(f"Caught: {e}")
                print(len(toClean))
                print(f"Trying to parse: '{toClean}'")
                sys.exit(1)
        elif isinstance(toClean, float):
            # toClean is not a String; check if it is a NaN float (which we treat as zero)
            if isnan(toClean):
                return 0.0
            else:
                print("Parsed a float?")
                sys.exit(1)
        # Return None if the value cannot be determined
        return None
        
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

def parseIdAndData_sec31(pdf, pdfUrl, sec31, outDict):
    """Converts TIF Section 3.1 into a CSV and parses the values; returns ID number or None"""

    # Obtain ID from URL
    filename = pdfUrl.split("/")[-1]
    pattern = r"T_(\d+)_"
    match = re.search(pattern, filename)
    if match:
        idNum = int(match.group(1))
        outDict['tif_number'] = idNum
    else:
        print("ID number not found.")
        return None
    # *STEP 1: READ PDF INTO DATAFRAME
    df = tabula.read_pdf(
        input_path=pdf,
        pages=sec31,
        area=[144, 0, 540, 600],
        columns=[45, 363, 428.5, 506], # [topY, leftX, bottomY, rightX]
        stream=True,
    )[0]
    # *STEP 2: CLEAN DATAFRAME HEADER
    try:
        sourceColName = df.filter(like='Revenue').columns.tolist()[0]
        curYearColName = df.filter(like='Reporting Year').columns.tolist()[0]
        cumColName = df.filter(like='Cumulative').columns.tolist()[0]
    except:
        print("FAILED ON: ", outDict['tif_name'])
        print("URL: ", pdfUrl)
    # *STEP 3: PARSE CLEANED DATAFRAME INTO DICTIONARY
    # Obtain the Pandas series for the 'Property Tax Increment' Row
    propTaxIncRow = df[df[sourceColName] == 'Property Tax Increment']
    # Obtain the Current and Cumulative Strings out of the propTaxIncRow series
    propTaxIncCur = propTaxIncRow[curYearColName].values[0]
    propTaxIncCum = propTaxIncRow[cumColName].values[0]
    # Use the user-defined Tools.stof() to clean the Strings to Integers for storage in outDict
    outDict['property_tax_extraction'] = Tools.stof(propTaxIncCur)
    outDict['cumulative_property_tax_extraction'] = Tools.stof(propTaxIncCum)

    # Obtain the Pandas series for the 'Transfers from Municipal Sources' Row
    transFromMunRow = df[df[sourceColName].str.contains('Transfers from', na=False, case=False)]
    # Obtain the Current and Cumulative Strings out of the propTaxIncRow series
    transFromMunCur = transFromMunRow[curYearColName].values[0]
    transFromMunCum = transFromMunRow[cumColName].values[0]
    # Use the user-defined Tools.stof() to clean the Strings to Integers for storage in outDict
    outDict['transfers_in'] = Tools.stof(transFromMunCur)
    outDict['cumulative_transfers_in'] = Tools.stof(transFromMunCum)

    # Obtain the Pandas series for the 'Total Expenditures/Cash Disbursements' Row
    totExpRow = df[df[sourceColName].str.contains('Total Expenditures/Cash Disbursements', na=False, case=False)]
    # Obtain the value as a String
    totExp = totExpRow[curYearColName].values[0]
    # Use the user-defined Tools.stof() to clean the String to an Integer for storage in outDict
    outDict['expenses'] = Tools.stof(totExp)

    # Obtain the Pandas series for the 'FUND BALANCE, END OF REPORTING PERIOD*' Row
    fundBalRow = df[df[sourceColName].str.contains('FUND BALANCE, END OF REPORTING PERIOD', na=False, case=False)]
    # Obtain the value as a String
    fundBal = fundBalRow[curYearColName].values[0]
    # Use the user-defined Tools.stof() to clean the String to an Integer for storage in outDict
    outDict['fund_balance_end'] = Tools.stof(fundBal)

    # Obtain the Pandas series for the 'Transfers to Municipal Sources' Row
    transToMunRow = df[df[sourceColName] == 'Transfers to Municipal Sources']
    if not transToMunRow.empty:
        print('\nFOUND A TRANSFER TO MUNICIPAL SOURCES ROW!\n')
        # Obtain the value as a String
        transToMun = transToMunRow[curYearColName].values[0]
        # Use the user-defined Tools.stof() to clean the String to an Integer for storage in outDict
        outDict['transfers_out'] = Tools.stof(transToMun)
    else:
        # We cannot identify a 'Transfers to Municipal Sources' row, so value is 0.0
        outDict['transfers_out'] = 0.0

    # Obtain the Pandas series for the 'Total Expenditures/Cash Disbursements' Row
    distSurpRow = df[df[sourceColName] == 'Distribution of Surplus']
    # Obtain the value as a String
    distSurp = distSurpRow[curYearColName].values[0]
    # Use the user-defined Tools.stof() to clean the String to an Integer for storage in outDict
    outDict['distribution'] = Tools.stof(distSurp)

    # Return Section 3.1 DataFrame for Storage
    return outDict


if __name__ == "__main__":
    main()