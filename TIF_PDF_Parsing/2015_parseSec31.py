import locale, sys
import tabula, csv
import pandas as pd
import PyPDF2, pdfplumber, io, os
import requests
import json
import re
import tempfile, shutil, subprocess
import ocrmypdf
import pygetwindow as gw
from pygetwindow import PyGetWindowException
import pyautogui
import time
from pdf2image import convert_from_bytes
from math import isnan
from bs4 import BeautifulSoup

def main():
    tempDir = 'c:\\sc' # ! - MODIFY THIS to an existing scratch directory
    year = '2015'
    urlListOffset = int(sys.argv[1]) # obtains offset from command line
    # try:
    pd.set_option('display.max_columns', None)
    csvFp = os.path.join(tempDir, f'out_{year}.csv')
    pdfFp = os.path.join(tempDir, 'out.pdf')
    dictList = []
    
    for i, url in enumerate(Tools.urlList(f"https://www.chicago.gov/city/en/depts/dcd/supp_info/district-annual-reports--{year}-.html")[urlListOffset:], urlListOffset):
        # Reset outDict
        outDict = {}
        # Obtain PDF bytes
        pdf = io.BytesIO(requests.get(url).content)        
        pdf_writer = PyPDF2.PdfWriter()
        sec31 = Tools.getPageNumFromText(pdf, 'SECTION 3.1')
        if sec31 == None:
            sec31 = 7 # hardcode it to page 7 if string 'SECTION 3.1' is not found
        pdf_writer.add_page(PyPDF2.PdfReader(pdf).pages[sec31 - 1]) # TODO: this can be done without making a new pdf_writer (i think?)
        sec31_origBytes = io.BytesIO()
        pdf_writer.write(sec31_origBytes)
        # Bytes of Section 3.1 Page is now obtained; convert it to a PIL image
        sec31_img = convert_from_bytes(sec31_origBytes.getvalue(), dpi=300) #, poppler_path=r'C:\Program Files\poppler-23.07.0\Library\bin'
        with tempfile.TemporaryDirectory() as tempDir:
            sec31_imgFp = os.path.join(tempDir, 'out.png')
            sec31_pdfFp = os.path.join(tempDir, 'out.pdf')
            sec31_img[0].save(sec31_imgFp, format='PNG')
            ocrmypdf.ocr(sec31_imgFp, sec31_pdfFp, optimize=0, redo_ocr=True, image_dpi=300)
            ocrmypdf.ocr(sec31_pdfFp, sec31_pdfFp, redo_ocr=True, optimize=1)
            # Copy output pdf for debugging
            shutil.copy(sec31_pdfFp, pdfFp)

            # ! Parse Section 3.1 Name and Year into outDict
            leftX, topY = Tools.getTextCoords(sec31_pdfFp, 'FY')
            df = tabula.read_pdf(
                input_path=r'c:\sc\out.pdf',
                # pages=sec31, 
                area=[topY-2, 0, topY+25, 600], # [topY, leftX, bottomY, rightX]
                columns=[leftX-2, leftX+54],
                pandas_options={'header': None},
            )[0]
            print(df)
            # Obtains the name and year by table location
            tifName = str(df.iloc[1,2]).replace(" Redevelopment Project Area", "").strip()
            match = re.search(r"FY\s+(\d{4})", str(df.iloc[0,1]))
            if match:
                tifYear = match.group(1)
            else:
                print('\nFAILED TO IDENTIFY YEAR...\n')
                sys.exit(0)
            # Set the TIF name and year
            outDict['tif_name'] = tifName.replace('_','').replace('—','').strip()
            outDict['tif_year'] = tifYear.strip()
            # Add current outDict to dictList
            dictList.append(outDict)
            # ! Parse Section 3.1 Datatable into outDict
            outDict = parseIdAndData_sec31(sec31_pdfFp, url, outDict)

        print(json.dumps({k: f"{v:,}" if isinstance(v, int) else v for k, v in outDict.items()}, indent=4, separators=(',', ': ')))
        print('\nurlList Index: ', i, '\n')
        Tools.buildCsvFromDicts(outDict, csvFp)
        
        # ! MODIFY THIS: IT IS WINDOWS-SPECIFIC
        # open pdf
        subprocess.Popen(['start', '', pdfFp], shell=True)   
        # open csv
        subprocess.Popen(['start', '', csvFp], shell=True)
        time.sleep(1)
        try:
            pdf_gw = gw.getWindowsWithTitle('out - PDF-XChange Editor')[0]
            xcl_gw = gw.getWindowsWithTitle('out_2015.csv - Excel')[0]
            xcl_gw.activate()
            pyautogui.hotkey('ctrl', 'end') # go to end of csv
            pdf_gw.activate()
            gw.getWindowsWithTitle([window for window in gw.getAllTitles() if 'Visual Studio Code' in window][0])[0].activate()
        except PyGetWindowException as e:
            print(f'{e=}')
            continue
        # Wait
        input('Press Enter to continue...')
        # Close Windows
        xcl_gw.close()
        pdf_gw.close()
    # except Exception as e:
    #     print(f'ERROR: {e=}')
    #     print("FAILED ON: ", tifName, f'\n{url}')
    #     print("urlList Index: ", i)

class Tools:
    """A collection of utility functions for TIF data parsing and processing."""

    def stof(toClean):
        """Converts a string to a float."""
        locale.setlocale(locale.LC_NUMERIC, 'en_US.UTF-8')
        if isinstance(toClean, str):
            # Remove stray dollar signs and/or asterisks to prepare for locale.atof() parsing
            toClean = toClean.replace('L','').replace('_','').replace('-','').replace('|','').replace('~','').replace(']','')
            # OCR often parses '5' as '§'
            toClean = toClean.replace('§', '5')
            # toClean is a String
            # if 'L' in toClean or '-' in toClean or len(toClean) <= 1:
                # Handle zeroes (for >= 2019, represented as dashes)
                # return 0.0
            if len(toClean) <= 0:
                # Handle zeroes (for <= 2018, no representation)
                return 0.0
            # If enclosed in parenthesis, number is negative. So we try to Regex a value out of ()...
            negPattern = r'.*\((.+)\).*'
            match = re.match(negPattern, toClean)
            try:
                if match:
                    # Number is negative, so we update the Float return value appropriately
                    # toClean = match.group(1)
                    # toClean = re.sub(r'\b\d{1,3}(?:,\d{3})*\b', '', toClean)
                    toClean = Tools.extract_numeric_value(toClean)
                    if toClean == None or len(toClean) <= 0:
                        return 0.0
                    return -1 * locale.atof(toClean)
                else:
                    # Number is positive, so return the cleaned string as a Float
                    # toClean = re.sub(r'^[^,\d]*|[^,\d]*$', '', toClean)
                    toClean = Tools.extract_numeric_value(toClean)
                    if toClean == None or len(toClean) <= 0:
                        return 0.0
                    return locale.atof(toClean)
            except ValueError as e:
                print(f"Caught: {e=}")
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

    def extract_numeric_value(toClean):
        segments = toClean.split()
        numbers = []
        for segment in segments:
            clean_str = ""
            for char in segment:
                if char.isdigit() or char == ',':
                    clean_str += char

            if clean_str:
                number = clean_str.replace(',', '')
                numbers.append(number)

        if numbers:
            print(toClean, ' ---> ', ', '.join(numbers))
            return max(numbers)
        else:
            print("\nSTOF ERROR: No number found.\n")  
        # def extract_numeric_value(toClean):
        #     # pattern = r"(?<![^\s\d,])\d{1,3}(?:,\d{3})*(?![^\s\d,])"
        #     pattern = r"\b(?:\d{1,3}(?!\d)|\d{1,3}(?:,\d{3,})+)\b"
        #     match = re.search(pattern, toClean)
        #     if match:
        #         number = match.group()
        #         print(toClean, ' ---> ', number)
        #         return number
        #     else:
        #         print("\nSTOF ERROR: No number found.\n")
    
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

    def getTextCoords(pdf, target_text):
        with pdfplumber.open(pdf) as pdf:
            page = pdf.pages[0]  # Assuming you want to check the first page
            for word in page.extract_words():
                if re.search(target_text, word["text"], re.IGNORECASE):
                    print(word)
                    x = float(word["x0"])
                    y = float(word["top"])
                    return x, y
        return None  # Target text not found

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

    def buildCsvFromDicts(outDict, csvFp):
        """Create a CSV file from a list of Dictionaries. Each row is one Dictionary."""

        # Define the fieldnames in the desired order
        fieldnames = [
            "tif_name",
            "tif_year",
            "start_year",
            "end_year",
            "tif_number",
            "property_tax_extraction",
            "cumulative_property_tax_extraction",
            "transfers_in",
            "cumulative_transfers_in",
            "expenses",
            "fund_balance_end",
            "transfers_out",
            "distribution",
            "admin_costs",
            "finance_costs",
            "bank"
        ]

        if os.path.exists(csvFp):
            mode = 'a'
        else:
            mode = 'w'

        # Write the data to the CSV file
        with open(csvFp, mode, newline='') as csvfile:
            writer = csv.writer(csvfile)
            # Write the header row
            if mode =='w':
                # Only write the header if it is a new CSV file
                writer.writerow(fieldnames)
            # Write the data rows
            row = [outDict.get(key, "") for key in fieldnames]
            writer.writerow(row)
            print("CSV File saved to: " + csvFp)

def parseIdAndData_sec31(pdf, pdfUrl, outDict): # TODO - copy this code back to tifParse.py b/c str.contains() is more robust
    """Converts TIF Section 3.1 into a CSV and parses the values; returns ID number or None"""

    # Obtain ID from URL
    filename = pdfUrl.split("/")[-1]
    print(filename)
    pattern = r"T_(\d+)_"
    match = re.search(pattern, filename)
    if match:
        idNum = int(match.group(1))
        outDict['tif_number'] = idNum
    else:
        print("ID number not found.")
        return None
    # *STEP 1: READ PDF INTO DATAFRAME
    leftX, topY = Tools.getTextCoords(pdf, 'Revenue')
    df = tabula.read_pdf(
        input_path=pdf,
        area=[topY-3, 0, topY+401, 600], # [topY, leftX, bottomY, rightX]
        columns=[leftX-3, leftX+311, leftX+382, leftX+457], 
        stream=True,
    )[0]
    print(df)
    # *STEP 2: CLEAN DATAFRAME HEADER
    sourceColName = 'Revenue/Cash Receipts Deposited in Fund During Reporting FY:'
    curYearColName = 'Reporting Year'
    cumColName = 'Cumulative*'
    try:
        sourceColName = df.filter(like='Revenue').columns.tolist()[0]
        curYearColName = df.filter(like='Year').columns.tolist()[0]
        cumColName = df.filter(like='Cumulative').columns.tolist()[0]
    except:
        print("FAILED ON: ", outDict['tif_name'])
        print("URL: ", pdfUrl)
    # *STEP 3: PARSE CLEANED DATAFRAME INTO DICTIONARY
    # Obtain the Pandas series for the 'Property Tax Increment' Row
    propTaxIncRow = df[df[sourceColName].str.contains('Property Tax Increment', na=False, case=False)]
    # Obtain the Current and Cumulative Strings out of the propTaxIncRow series
    propTaxIncCur = propTaxIncRow[curYearColName].values[0]
    propTaxIncCum = propTaxIncRow[cumColName].values[0]
    # Use the user-defined Tools.stof() to clean the Strings to Integers for storage in outDict
    outDict['property_tax_extraction'] = int(Tools.stof(propTaxIncCur))
    outDict['cumulative_property_tax_extraction'] = int(Tools.stof(propTaxIncCum))

    # Obtain the Pandas series for the 'Transfers from Municipal Sources' Row
    transFromMunRow = df[df[sourceColName].str.contains('Transfers fr', na=False, case=False)]
    # Obtain the Current and Cumulative Strings out of the propTaxIncRow series
    transFromMunCur = transFromMunRow[curYearColName].values[0]
    transFromMunCum = transFromMunRow[cumColName].values[0]
    # Use the user-defined Tools.stof() to clean the Strings to Integers for storage in outDict
    outDict['transfers_in'] = int(Tools.stof(transFromMunCur))
    outDict['cumulative_transfers_in'] = int(Tools.stof(transFromMunCum))

    # Obtain the Pandas series for the 'Total Expenditures/Cash Disbursements' Row
    totExpRow = df[df[sourceColName].str.contains('Carried', na=False, case=False)]
    # Obtain the value as a String
    totExp = totExpRow[curYearColName].values[0]
    # Use the user-defined Tools.stof() to clean the String to an Integer for storage in outDict
    outDict['expenses'] = int(Tools.stof(totExp))

    # Obtain the Pandas series for the 'FUND BALANCE, END OF REPORTING PERIOD*' Row
    fundBalRow = df[df[sourceColName].str.contains('FUND BALANCE', na=False, case=False)]
    # Obtain the value as a String
    fundBal = fundBalRow[curYearColName].values[0]
    # Use the user-defined Tools.stof() to clean the String to an Integer for storage in outDict
    outDict['fund_balance_end'] = int(Tools.stof(fundBal))

    # Obtain the Pandas series for the 'Transfers to Municipal Sources' Row
    transToMunRow = df[df[sourceColName].str.contains('Transfers t', na=False, case=False)]
    if not transToMunRow.empty:
        print('\nFOUND A TRANSFER TO MUNICIPAL SOURCES ROW!\n')
        # Obtain the value as a String
        transToMun = transToMunRow[curYearColName].values[0]
        # Use the user-defined Tools.stof() to clean the String to an Integer for storage in outDict
        outDict['transfers_out'] = int(Tools.stof(transToMun))
    else:
        # We cannot identify a 'Transfers to Municipal Sources' row, so value is 0.0
        outDict['transfers_out'] = 0

    # Obtain the Pandas series for the 'Distribution of Surplus' Row
    distSurpRow = df[df[sourceColName].str.contains('Distribution', na=False, case=False)]
    # Obtain the value as a String
    distSurp = distSurpRow[curYearColName].values[0]
    # Use the user-defined Tools.stof() to clean the String to an Integer for storage in outDict
    outDict['distribution'] = int(Tools.stof(distSurp))

    # Return Section 3.1 DataFrame for Storage
    return outDict


if __name__ == "__main__":
    main()