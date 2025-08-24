import locale, sys, argparse, concurrent
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
from contextlib import suppress
import pyautogui
import time
from pdf2image import convert_from_bytes
from urllib.parse import urljoin  # For joining URLs in Tools.darYearsUrls()
from math import isnan
from bs4 import BeautifulSoup

# ! FUNCTIONS
def configurePandas():
    pd.set_option('display.max_columns', None)
    pd.set_option('display.max_rows', None)
    pd.set_option('display.width', 100000)

def cleanDf_before2011(df):
    print(df)
    # cols = df.columns.tolist()
    # cols[0] = 'Revenue/Cash Receipts Deposited in Fund During Reporting FY'
    # newIndexZero = df[df[df.columns[0]].str.contains('Property', na=False)].index[0]
    # if newIndexZero is None:
    #     print('USE DEFAULT 3 AS INDEX VALUE')
    # cleaned = df[3:]
    df.columns = ['Revenue/Cash Receipts Deposited in Fund During Reporting FY', 'Reporting Year', 'Cumulative*', '% of Total']
    return df

def parseIdAndData_sec31(pdf, pdfUrl, year, sec32b_height, outDict): # TODO - copy this code back to tifParse_2017AndBeyond.py b/c str.contains() is more robust
    """Converts TIF Section 3.1 into a CSV and parses the values; returns outDict with added key/value pairs"""

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
    if int(year) <= 2011:
        coords_revenue = Tools.getTextCoords(pdf, 'Year')
    else:
        coords_revenue = Tools.getTextCoords(pdf, 'Revenue/')
    if coords_revenue is None:
        # Hardcoded from previous usage in-case bad OCR causes None return from Tools.getTextCoords()
        leftX, topY = 406.32, 85.9199
    else:
        leftX, topY = coords_revenue["x0"], coords_revenue["top"]
    df = tabula.read_pdf(
        input_path=pdf,
        area=[(topY/sec32b_height)*100, 0, 100, 100], # [topY, leftX, bottomY, rightX]
        columns=[leftX-47, leftX+24, leftX+98], 
        stream=True,
        relative_area=True,
    )[0]
    if int(year) <= 2011:
        df = cleanDf_before2011(df)
    print(df)

    # *STEP 2: CLEAN DATAFRAME HEADER
    sourceColName = 'Revenue/Cash Receipts Deposited in Fund During Reporting FY:'
    curYearColName = 'Reporting Year'
    cumColName = 'Cumulative*'
    # Overwrite defaults with str.contains
    sourceColName = df.filter(like='Revenue').columns.tolist()[0] # replace columns.tolist
    curYearColName = df.filter(like='Year').columns.tolist()[0] # replace columns.tolist
    cumColName = df.filter(like='umu').columns.tolist()[0] # replace columns.tolist

    # *STEP 3: PARSE CLEANED DATAFRAME INTO DICTIONARY
    # Obtain the Pandas series for the 'Property Tax Increment' Row
    propTaxIncRow = df[df[sourceColName].str.contains('property tax inc', na=False, case=False)]
    if propTaxIncRow.empty:
        propTaxIncRow = df[df[sourceColName].str.contains('Prooertv Tax', na=False, case=False)]
        if propTaxIncRow.empty:
            propTaxIncRow = df[df[sourceColName].str.contains('erty Tax', na=False, case=False)]
            if propTaxIncRow.empty:
                propTaxIncRow = df[df[sourceColName].str.contains('PropertTyax', na=False, case=False)]
    if propTaxIncRow.empty:
        propTaxIncRow = df[3]
    print('PROPTAXINCROW: ', propTaxIncRow)
    # Obtain the Current and Cumulative Strings out of the propTaxIncRow series
    propTaxIncCur = propTaxIncRow[curYearColName].values[0]
    propTaxIncCum = propTaxIncRow[cumColName].values[0]
    # Use the user-defined Tools.stof() to clean the Strings to Integers for storage in outDict
    outDict['property_tax_extraction'] = int(Tools.stof(propTaxIncCur))
    outDict['cumulative_property_tax_extraction'] = int(Tools.stof(propTaxIncCum))

    # Obtain the Pandas series for the 'Transfers from Municipal Sources' Row
    transFromMunRow = df[df[sourceColName].str.contains('Transfers in', na=False, case=False)]
    # Obtain the Current and Cumulative Strings out of the propTaxIncRow series
    transFromMunCur = transFromMunRow[curYearColName].values[0]
    transFromMunCum = transFromMunRow[cumColName].values[0]
    # Use the user-defined Tools.stof() to clean the Strings to Integers for storage in outDict
    outDict['transfers_in'] = int(Tools.stof(transFromMunCur))
    outDict['cumulative_transfers_in'] = int(Tools.stof(transFromMunCum))

    # Obtain the Pandas series for the 'Total Expenditures/Cash Disbursements' Row
    totExpRow = df[df[sourceColName].str.contains('Cash Disbursements', na=False, case=False)]
    # Obtain the value as a String
    totExp = totExpRow[curYearColName].values[0]
    # Use the user-defined Tools.stof() to clean the String to an Integer for storage in outDict
    # if int(year) == 2011:
    #     totExp = totExp[:-1]
    outDict['expenses'] = int(Tools.stof(totExp))

    # Obtain the Pandas series for the 'FUND BALANCE, END OF REPORTING PERIOD*' Row
    fundBalRow = df[df[sourceColName].str.contains('END OF REPORTING', na=False)]
    # Obtain the value as a String
    fundBal = fundBalRow[curYearColName].values[0]
    # Use the user-defined Tools.stof() to clean the String to an Integer for storage in outDict
    outDict['fund_balance_end'] = int(Tools.stof(fundBal))

    # Obtain the Pandas series for the 'Transfers to Municipal Sources' Row
    transToMunRow = df[df[sourceColName].str.contains('to Municipal Sources', na=False, case=False)]
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

def parseAdminFinance_sec32b(sec32b_pdfFp_out, sec32b_height, outDict):
    try:
        x1, top = (coords := Tools.getTextCoords(sec32b_pdfFp_out, 'Nam')).get('x1'), coords.get('top')
        x2, x3 = (coords := Tools.getTextCoords(sec32b_pdfFp_out, 'Amount')).get('x0'), coords.get('x1')
        col = [0, x1+60, x2-45, x3+55]
        print("COL:", col)
        top = 100 * ((top - 15) / sec32b_height)
        print("TOP:", top)
        dfs = tabula.read_pdf(
            input_path=sec32b_pdfFp_out,
            pages=1, 
            area=[top, 0, 100, 100], # [topY, leftX, bottomY, rightX]
            relative_area=True,
            columns=col,
            # pandas_options={'header': None},
        )
        df = dfs[0].drop('Unnamed: 0', axis=1)
        print(df)
        # ! - Parse Section 3.2 B Admin and Finance Data into outDict
        # Get Column Names
        try:
            nameColName = df.filter(like='Nam').columns.tolist()[0]
            serviceColName = df.filter(like='vice').columns.tolist()[0]
            amountColName = df.filter(like='Amount').columns.tolist()[0]
        except:
            print("FAILED ON: ", outDict['tif_name'])
        # Parse each Admin Cost and sum them; assume larger value is more accurate
        # TODO - Copy this code to post2017 script b/c this is more robust using str.contains
        adminCosts_service = df[df[serviceColName].astype(str).str.contains('Administration', case=False, na=False)][amountColName].apply(Tools.stof).sum()
        adminCosts_byName = df[df[nameColName].astype(str).str.contains('City Program Management Costs|City Staff Costs', case=False, na=False)][amountColName].apply(Tools.stof).sum()
        adminCosts = max(adminCosts_service, adminCosts_byName)
        if adminCosts_service != adminCosts_byName:
            print("\nAdmin Cost Discrepancy! Larger value chosen.")
            print(f"Chosen Admin Value for TIF #{outDict['tif_number']}: {adminCosts}\n")
        # TODO: rely on the names, not service administration?
        # Parse each Finance Cost Amount and sum them
        financeCosts = df[df[serviceColName].astype(str).str.contains('Financing', case=False, na=False)][amountColName].apply(Tools.stof).sum()
        # Obtain the Bank Name(s)
        bankNameList = df[df[serviceColName].astype(str).str.contains('Financing', case=False, na=False)][nameColName].drop_duplicates().tolist()
        if "Amalgamated Bank of Chicago" in bankNameList:
            bankNameList[bankNameList.index("Amalgamated Bank of Chicago")] = "Amalgamated Bank"
        bankNames = ', '.join(sorted(bankNameList))
    except Exception as e:
        adminCosts = 0
        financeCosts = 0
        bankNames = ''
        print(f'{e=}')
        # Check if the "No Vendors" message is present
        if Tools.getTextCoords(sec32b_pdfFp_out, 'There') is None:
            print("CHECK OUTPUT, unable to verify presence of vendors")
        else:
            print("NO VENDORS ABOVE $10,000 FOUND, proceed to next...")
    
    outDict['admin_costs'] = int(adminCosts)
    outDict['finance_costs'] = int(financeCosts)
    outDict['bank'] = bankNames
    return outDict


# ! MAIN METHOD
def main():
    configurePandas()
    dictList = []
    # ! - Parse Command Line Args
    parser = argparse.ArgumentParser()
    parser.add_argument("year", type=str)
    parser.add_argument("urlListOffset", type=int, nargs="?", default=0)
    parser.add_argument("-o", "--redoOcr", action="store_true", help="Enable to redo OCR")
    parser.add_argument("-m", "--manual", action="store_true", help="Enable for manual verification after each TIF")
    args = parser.parse_args()
    redoOcr = args.redoOcr
    manualMode = args.manual
    year, urlListOffset = args.year, args.urlListOffset
    scratchDir = f'c:\\sc\\{year}' # * - MODIFY THIS to an existing scratch directory
    if not os.path.exists(scratchDir):
        os.makedirs(scratchDir)
    # ! - Make Filepath Variables
    csvFp = os.path.join(scratchDir, f'{year}_out.csv')
    sec31_pdfFp_out = os.path.join(scratchDir, 'sec31.pdf')
    sec32b_pdfFp_out = os.path.join(scratchDir, 'sec32b.pdf')
    print("urlList Offset Inputted:", urlListOffset)
    # ! - DAR URLs than can be parsed
    darYearsUrls = Tools.darYearsUrls()
    try:
        url = darYearsUrls[year]
    except KeyError as e:
        print(f'{e=}')
        print(f'No URL found for {year}')
        sys.exit(1)
    # ! - Read Termination Table from Disk (previously extracted)
    termTable_df = pd.read_csv(os.path.join(scratchDir, f'{year}_termTable.csv'))
    # ! Use the DAR YEAR URL for the appropriate year to generaye the URL LIST OF PDFS
    urlList = Tools.urlList(darYearsUrls[year])
    # HIDDEN TIF: 40th/State, BUT IT HAS NO DATA IN ANY YEAR REPORT
    # FURTHER INVESTEGATION IS REQUIRED
    if (int(year) <= 2013 and int(year) >= 2011):
        # There is a hidden TIF (40th/State) that is not present on any year's pages
        # However, it is present in this url format below for 2010-2013 inclusive
        missingTifUrl = f'https://www.chicago.gov/content/dam/city/depts/dcd/tif/{year[2:]}reports/T_132_40thStateAR{year[2:]}.pdf'
        urlList.insert(5, missingTifUrl)
    # HIDDEN TIF: ChathamRidge
    if (int(year) == 2011):
        missingTifUrl = f'https://www.chicago.gov/content/dam/city/depts/dcd/tif/{year[2:]}reports/T_015_ChathamRidgeAR{year[2:]}.pdf'
        urlList.insert(57, missingTifUrl)
    urlListLen = len(urlList)
    print('URLLIST LENGTH:', urlListLen)
    # ! - Iterate each TIF DAR URL for a single year
    for i, url in enumerate(urlList[urlListOffset:], urlListOffset):
        print("ENABLED VIA ARGS - REDO OCR") if redoOcr else print("DISABLED BY DEFAULT - REDO OCR")
        outDict = {} # For CSV Output
        outDict['tif_year'] = year
        # ! - Obtain TIF Number and Name from File name
        filename = url.split("/")[-1].split('_')
        tifNumber = int(filename[1])
        outDict['tif_number'] = tifNumber
        tifName = filename[2][:-8] 
        outDict['tif_name'] = tifName
        # ! - Obtain Start and End Years from TermTable DataFrame
        startYear = termTable_df[termTable_df['Name of Redevelopment Project Area'] == tifName]['Date Designated'].values[0].split('/')[-1]
        outDict['start_year'] = int(startYear)
        endYear = termTable_df[termTable_df['Name of Redevelopment Project Area'] == tifName]['Date Terminated'].values[0].split('/')[-1]
        outDict['end_year'] = int(endYear)
        # ! - Isolate Desired PDF Page Numbers
        # Get Full PDF bytes
        pdf = io.BytesIO(requests.get(url).content) 
        # Make an output PDF for each section (3.1 & 3.2 B) 
        sec31_pdfWriter = PyPDF2.PdfWriter()      
        sec32b_pdfWriter = PyPDF2.PdfWriter()
        # Obtain the page numbers of the desired sections (hardcode if getPageNumFromText() returns None)
        sec31 = Tools.getPageNumFromText(pdf, 'SECTION 3.1')
        sec32b = Tools.getPageNumFromText(pdf, 'Section 3.2 B')
        # with concurrent.futures.ProcessPoolExecutor() as executor:
        #     future_sec31 = executor.submit(Tools.getPageNumFromText, pdf, 'SECTION 3.1')
        #     future_sec32b = executor.submit(Tools.getPageNumFromText, pdf, 'Section 3.2 B')
        #     concurrent.futures.wait([future_sec31, future_sec32b])
        #     sec31 = future_sec31.result()
        #     sec32b = future_sec32b.result()
        print('Isolating Pages', sec31, 'and', sec32b)
        if sec31 == None:
            sec31 = 7 if int(year) > 2011 else 8
        if sec32b == None:
            sec32b = 11 if int(year) > 2011 else 12
                
        # ! - Convert PDF Pages to PIL Images
        # Convert Section 3.1 to PIL Image
        sec31_page = PyPDF2.PdfReader(pdf).pages[sec31 - 1]
        sec31_pdfWriter.add_page(sec31_page) # TODO: this can be done without making a new pdf_writer (i think?)
        sec31_origBytes = io.BytesIO()
        sec31_pdfWriter.write(sec31_origBytes)
        # Convert Section 3.2 B to PIL Image
        sec32b_page = PyPDF2.PdfReader(pdf).pages[sec32b - 1]
        sec32b_height = float(sec32b_page.mediabox[3]) # grab height for relative_area used in tabula.read_pdf()
        sec32b_pdfWriter.add_page(sec32b_page) # TODO: this can be done without making a new pdf_writer (i think?)
        sec32b_origBytes = io.BytesIO()
        sec32b_pdfWriter.write(sec32b_origBytes)
        # Save to disk for manual verification step
        with open(sec31_pdfFp_out, "wb") as output_pdf:
            output_pdf.write(sec31_origBytes.getvalue())
        with open(sec32b_pdfFp_out, "wb") as output_pdf:
            output_pdf.write(sec32b_origBytes.getvalue())
        # ! - OPTIONAL STEP - Redo OCR
        while True:
            if redoOcr:
                # TODO: Only redoOcr once; Do not let this setting persist, hence redoOcr = False
                # redoOcr = False
                sec31_img = convert_from_bytes(sec31_origBytes.getvalue(), dpi=300)
                sec32b_img = convert_from_bytes(sec32b_origBytes.getvalue(), dpi=300)
                # ! - Redo OCR and save to disk for each section 
                with tempfile.TemporaryDirectory() as tempDir:
                    # Filepaths to save to disk
                    sec31_pdfFp_out = os.path.join(scratchDir, 'sec31.pdf')
                    sec32b_pdfFp_out = os.path.join(scratchDir, 'sec32b.pdf')
                    # Save Section 3.1
                    sec31_imgFp = os.path.join(tempDir, 'sec31.png')
                    sec31_pdfFp = os.path.join(tempDir, 'sec31.pdf')
                    sec31_img[0].save(sec31_imgFp, format='PNG')
                
                    # Save Section 3.2 B
                    sec32b_imgFp = os.path.join(tempDir, 'sec32b.png')
                    sec32b_pdfFp = os.path.join(tempDir, 'sec32b.pdf')
                    sec32b_img[0].save(sec32b_imgFp, format='PNG')
                    
                    # Run OCR WITH MULTIPROCESSING
                    with concurrent.futures.ProcessPoolExecutor() as executor:
                        # Parallel execution of Task 1
                        future_task1 = executor.submit(ocrmypdf.ocr, sec31_imgFp, sec31_pdfFp, optimize=0, redo_ocr=True, image_dpi=300)
                        # Parallel execution of Task 2
                        future_task2 = executor.submit(ocrmypdf.ocr, sec32b_imgFp, sec32b_pdfFp, optimize=0, redo_ocr=True, image_dpi=300)
                        # Wait for both tasks to complete
                        concurrent.futures.wait([future_task1, future_task2])
                    
                    # Run OCR WITHOUT MULTIPROCESSING
                    # First Pass
                    # ocrmypdf.ocr(sec31_imgFp, sec31_pdfFp, optimize=0, redo_ocr=True, image_dpi=300)
                    # Second Pass to Improve OCR Quality
                    # ocrmypdf.ocr(sec31_pdfFp, sec31_pdfFp, redo_ocr=True, optimize=1) 

                    # Save PDF(s) to disk
                    shutil.copy(sec31_pdfFp, sec31_pdfFp_out) 
                    shutil.copy(sec32b_pdfFp, sec32b_pdfFp_out)
                    # input("Press Enter to continue (paused after PDF creation)...")
            # try:
            # ! - Obtain and Parse Section 3.1 Dataframe
            outDict = parseIdAndData_sec31(sec31_pdfFp_out, url, year, sec32b_height, outDict)
            ''' sec31_pdfFp_out was first arg ^^^^^^^^^^^^   '''
            # ! - Obtain and Parse Section 3.2 B Dataframe
            outDict = parseAdminFinance_sec32b(sec32b_pdfFp_out, sec32b_height, outDict)           
            # except Exception as e:
            #     print(f'{e=}')
            #     print(f"REDOING OCR...\n({i}) {outDict['tif_name']}") 
            #     redoOcr = True
            #     continue
            # ! - Data parsed; add to dictList
            dictList.append(outDict)
            # FOR OCR, INDENT FROM HERE ABOVE
            print(json.dumps({k: f'{v:,}' if isinstance(v, int) else v for k, v in outDict.items()}, indent=4, separators=(',', ': ')))
            print('\nurlList Index: ', i, '\n')
            Tools.buildCsvFromDicts(outDict, csvFp)
            print("ON DECK:", f"({str(i+1)})", urlList[i+1].split('/')[-1]) if i < urlListLen - 1 else print("ON DECK:", "NONE!!!")
            # ! - MANAUAL VERIFICATION (Open PDF and CSV in GUI for manual validation)
            if manualMode:
                # pdfxchange = r"C:\Program Files\Tracker Software\PDF Editor\PDFXEdit.exe"
                # subprocess.Popen([pdfxchange, sec31_pdfFp_out], shell=True)
                # subprocess.Popen([pdfxchange, sec32b_pdfFp_out], shell=True)
                subprocess.Popen(['start', '', sec31_pdfFp_out], shell=True)
                subprocess.Popen(['start', '', sec32b_pdfFp_out], shell=True)
                subprocess.Popen(['start', '', csvFp], shell=True)
                time.sleep(0.8)
                with suppress(PyGetWindowException):
                    # PyGetWindow code is dependant on OS default editors for .csv and .pdf, as well as screen size
                    sec31_pdf_gw = gw.getWindowsWithTitle('sec31 - PDF-XChange Editor')[0]
                    sec31_pdf_gw.moveTo(0, 0)
                    sec31_pdf_gw.resizeTo(1168, 1190)
                    sec32b_pdf_gw = gw.getWindowsWithTitle('sec32b - PDF-XChange Editor')[0]
                    sec32b_pdf_gw.moveTo(1153, 0)
                    sec32b_pdf_gw.resizeTo(1188, 574)
                    xcl_gw = gw.getWindowsWithTitle(f'{year}_out.csv - Excel')[0]
                    vscode_gw = gw.getWindowsWithTitle([window for window in gw.getAllTitles() if 'Visual Studio Code' in window][0])[0]
                    sec31_pdf_gw.activate() # put sec31 on bottom
                    sec32b_pdf_gw.activate() # put sec32b on top of sec31
                    xcl_gw.activate()
                    time.sleep(1)
                    pyautogui.hotkey('ctrl', 'end') # go to end of csv
                    time.sleep(0.5)
                    vscode_gw.activate() # put vs code on top of pdf
                # except PyGetWindowException as e:
                #     print(f'{e=}')
                # Wait
                redoCurrent = input("Input NOTHING (Enter) to proceed, input SOMETHING (and then Enter) to redo OCR on current PDF: ")
                # Close Windows
                xcl_gw.close()
                sec31_pdf_gw.close()
                sec32b_pdf_gw.close()
                # Either redo current iteration of for loop, or continue to the next one
                if redoCurrent:
                    redoOcr = True
                    continue
            # else:
            #     # Keep redoOcr off for AUTOMATIC MODE
            #     redoOcr = False # TODO: allow for this functionality: -o switch enables ocr/manual.
            #     # ? - should ocr/auto be an option? see how 2012 performs
            # ^^^^^^^^^^^^^^ MANUAL VERIFICATION CODE ^^^^^^^^^^^^^
            break
    print("Script completed successfully!")
    # except Exception as e:
    #     print(f'ERROR: {e=}')
    #     print('FAILED ON: ', tifName, f'\n{url}')
    #     print('urlList Index: ', i)

class Tools:
    """A collection of utility functions for TIF data parsing and processing."""

    def stof(toClean):
        """Converts a string to a float."""
        locale.setlocale(locale.LC_NUMERIC, 'en_US.UTF-8')
        if isinstance(toClean, str):
            # Remove stray dollar signs and other bad chars to prepare for locale.atof() parsing
            if '$' in toClean:
                toClean = toClean[toClean.index('$'):]
            toClean = toClean.replace('L','').replace('I','').replace('_','')\
                            .replace('-','').replace('|','').replace('~','').replace(']','')\
                            .replace('$','').replace(' ','')
            # OCR sometimes parses '5' as '§' or 's' and '0' as 'o'
            toClean = toClean.replace('§', '5').replace('o','0')
            if len(toClean) > 1:
                toClean = toClean.replace('s', '5')
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
                    toClean = toClean.replace(')','').replace('(','')
                    toClean = re.sub(r'[,.](?P<digit>\d{3})1$', r',\g<digit>', toClean)
                    toClean = Tools.extract_numeric_value(toClean)
                    if toClean == None or len(toClean) <= 0:
                        return 0.0
                    return -1 * locale.atof(toClean)
                else:
                    # Number is positive, so return the cleaned string as a Float
                    # toClean = re.sub(r'^[^,\d]*|[^,\d]*$', '', toClean)
                    # Handle a trailing '1' using regex (ex. '123,456,7891')
                    toClean = re.sub(r'[,.](?P<digit>\d{3})1$', r',\g<digit>', toClean)
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

    def darYearsUrls():
        """Parses the chicago.gov 'TIF District Annual Reports 1997-present' webpage; returns a Dictionary with Years matched to URLs"""
        html = requests.get('https://www.chicago.gov/city/en/depts/dcd/supp_info/tif-district-annual-reports-2004-present.html').text
        soup = BeautifulSoup(html, "html.parser")
        year_links = soup.find_all("a", href=True)
        darYearsUrls = {}
        for link in year_links:
            text = link.text.strip()
            href = link["href"]
            # Extract the year from the link text using regular expression
            year_match = re.search(r"\d{4}", text)
            if year_match:
                year = year_match.group(0)
                full_url = urljoin("https://www.chicago.gov", href)
                # Filter URLs to include only those containing 'city/en/depts/dcd/supp_info'
                if 'city/en/depts/dcd/supp_info' in full_url:
                    darYearsUrls[year] = full_url
        return darYearsUrls

    def getTextCoords(pdf, target_text):
        with pdfplumber.open(pdf) as pdf:
            page = pdf.pages[0]  # Assuming you want to check the first page
            for word in page.extract_words():
                if re.search(target_text, word["text"]):
                    print(word)
                    return word
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

if __name__ == "__main__":
    main()