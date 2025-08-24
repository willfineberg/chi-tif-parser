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
    if len(sys.argv) < 2:
        urlListOffset = 0
    else:
        urlListOffset = int(sys.argv[1]) # obtains offset from command line
    print("urlList Offset Inputted:", urlListOffset)
    # try:
    pd.set_option('display.max_columns', None)
    csvFp = os.path.join(tempDir, f'out_{year}.csv')
    pdfFp = os.path.join(tempDir, 'out.pdf')
    dictList = []
    urlList = Tools.urlList(f"https://www.chicago.gov/city/en/depts/dcd/supp_info/district-annual-reports--{year}-.html")
    urlListLen = len(urlList)
    
    # ! - Iterate each TIF DAR URL for a single year
    for i, url in enumerate(urlList[urlListOffset:], urlListOffset):
        outDict = {} # For building a CSV
        # ! - Obtain TIF Number and Name
        filename = url.split("/")[-1].split('_')
        outDict['tif_number'] = int(filename[1])
        outDict['tif_name'] = filename[2][:-8]
        # ! - Isolate Desired PDF Page to PIL Image
        pdf = io.BytesIO(requests.get(url).content)        
        pdf_writer = PyPDF2.PdfWriter()
        sec32b = Tools.getPageNumFromText(pdf, 'Section 3.2 B')
        print('Isolating Page', sec32b)
        if sec32b == None:
            sec32b = 11 # hardcode it to page 7 if string 'Section 3.2 B' is not found
        sec32b_page = PyPDF2.PdfReader(pdf).pages[sec32b - 1]
        height = float(sec32b_page.mediabox[3])
        pdf_writer.add_page(sec32b_page) # TODO: this can be done without making a new pdf_writer (i think?)
        sec32b_origBytes = io.BytesIO()
        pdf_writer.write(sec32b_origBytes)
        # Bytes of Section 3.1 Page is now obtained; convert it to a PIL image
        sec32b_img = convert_from_bytes(sec32b_origBytes.getvalue(), dpi=300) #, poppler_path=r'C:\Program Files\poppler-23.07.0\Library\bin'
        
        with tempfile.TemporaryDirectory() as tempDir:
            # ! - Save to disk and redo OCR on isolated page
            sec32b_imgFp = os.path.join(tempDir, 'out.png')
            sec32b_pdfFp = os.path.join(tempDir, 'out.pdf')
            sec32b_img[0].save(sec32b_imgFp, format='PNG')
            ocrmypdf.ocr(sec32b_imgFp, sec32b_pdfFp, optimize=0, redo_ocr=True, image_dpi=300)
            # ocrmypdf.ocr(sec32b_pdfFp, sec32b_pdfFp, redo_ocr=True, optimize=1)
            # Copy output pdf for debugging
            shutil.copy(sec32b_pdfFp, pdfFp)
            # input("Press Enter to continue (paused after PDF creation)...")
            # ! - Obtain Section 3.2 B Dataframe
            try:
                x0, x1, top = (coords := Tools.getTextCoords(pdfFp, 'Name')).get('x0'), coords.get('x1'), coords.get('top')
                x2, x3 = (coords := Tools.getTextCoords(pdfFp, 'Amount')).get('x0'), coords.get('x1')
                col = [x0-125, x1+100, x2-45, x3+55]
                print("COL:", col)
                top = 100 * ((top - 15) / height)
                print("TOP:", top)
                dfs = tabula.read_pdf(
                    input_path=pdfFp,
                    pages=1, 
                    area=[top, 7.3, 100, 92.5], # [topY, leftX, bottomY, rightX]
                    relative_area=True,
                    columns=col,
                    # pandas_options={'header': None},
                )
                df = dfs[0].drop('Unnamed: 0', axis=1)
                print(df)
                # ! - Parse Section 3.2 B Admin and Finance Data into outDict
                # Parse each Admin Cost and sum them; assume larger value is more accurate
                adminCosts_service = df[df['Service'] == 'Administration']['Amount'].apply(Tools.stof).sum()
                adminCosts_byName = df[df['Name'].astype(str).str.contains('City Program Management Costs|City Staff Costs', case=False, na=False)]['Amount'].apply(Tools.stof).sum()
                adminCosts = max(adminCosts_service, adminCosts_byName)
                if adminCosts_service != adminCosts_byName:
                    print("\nAdmin Cost Discrepancy! Larger value chosen.")
                    print(f"Chosen Admin Value for TIF #{outDict['tif_number']}: {adminCosts}\n")
                # TODO: rely on the names, not service administration
                # Parse each Finance Cost Amount and sum them
                financeCosts = df[df['Service'] == 'Financing']['Amount'].apply(Tools.stof).sum()
                # Obtain the Bank Name(s)
                bankNameList = df[df['Service'] == 'Financing']['Name'].drop_duplicates().tolist()
                bankNames = ', '.join(bankNameList)
            except Exception as e:
                print(f'{e=}')
                noVendors = Tools.getTextCoords(pdfFp, 'There')
                if noVendors is None:
                    print("CHECK OUTPUT, unable to verify presence of vendors")
                else:
                    print("NO VENDORS ABOVE $10,000 FOUND, proceed to next...")
                adminCosts = 0.0
                financeCosts = 0.0
                bankNames = ''
            # Either way, set the adminCosts, financeCosts, and bankNames
            outDict['admin_costs'] = adminCosts
            outDict['finance_costs'] = financeCosts
            outDict['bank'] = bankNames
            # Add current outDict to dictList
            dictList.append(outDict)

        print(json.dumps({k: f'{v:,}' if isinstance(v, float) else v for k, v in outDict.items()}, indent=4, separators=(',', ': ')))
        print('\nurlList Index: ', i, '\n')
        Tools.buildCsvFromDicts(outDict, csvFp)
        if i < urlListLen - 2:
            print("ON DECK:", urlList[i+1].split('/')[-1])
        # ! - Open PDF and CSV in GUI for manual validation
        # TODO -  MODIFY THIS: IT IS WINDOWS-SPECIFIC
        subprocess.Popen(['start', '', pdfFp], shell=True)   
        subprocess.Popen(['start', '', csvFp], shell=True)
        time.sleep(1)
        try:
            pdf_gw = gw.getWindowsWithTitle('out - PDF-XChange Editor')[0]
            xcl_gw = gw.getWindowsWithTitle('out_2015.csv - Excel')[0]
            xcl_gw.activate()
            # time.sleep(0.5)
            pyautogui.hotkey('ctrl', 'end') # go to end of csv
            pdf_gw.activate() # put pdf on top of csv
            gw.getWindowsWithTitle([window for window in gw.getAllTitles() if 'Visual Studio Code' in window][0])[0].activate() # put vs code on top of pdf
        except PyGetWindowException as e:
            print(f'{e=}')
        # Wait
        input('Press Enter to continue...')
        # Close Windows
        xcl_gw.close()
        pdf_gw.close()
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
            "tif_number",
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