# ! - Ran in 2025 (on 24' reports) using Py 3.8.10

# ! - Install Dependencies with `pip install -r requirements.txt`

# * tabula-py Documentation: https://tabula-py.readthedocs.io/en/latest/tabula.html#tabula.io.convert_into
import tabula, csv  # For PDF parsing to CSV
import PyPDF2, pdfplumber  # For finding the right page number and page locations to point Tabula to
import locale  # For using C-style atoi() function
import json  # For printing the Dictionary as Structured JSON
import re  # For regexing the TIF ID number from URL
import requests  # For getting an HTML Response to parse with BeautifulSoup
import sys, os, io  # For arg parsing and filepath management
import time  # For reporting program runtime
import pandas as pd  # For data cleaning
import traceback  # For printing stack traces upon failure
import multiprocessing, concurrent.futures  # For threading
import logging
# For Debugging: import tabula, csv, PyPDF2, pdfplumber, locale, json, re, requests, sys, os, io, time, pandas as pd, traceback, multiprocessing, concurrent.futures
from bs4 import BeautifulSoup  # For HTML parsing the DAR URLs
from math import isnan  # For checking if parsed values are NaN or not
from urllib.parse import urljoin  # For joining URLs in Tools.darYearsUrls()

class Tools:
    """A collection of utility functions for TIF data parsing and processing."""

    def stof(toClean):
        """Converts a string to a float."""
        locale.setlocale(locale.LC_NUMERIC, 'en_US.UTF-8')
        if isinstance(toClean, str):
            # Remove stray dollar signs and/or asterisks to prepare for locale.atof() parsing
            toClean = toClean.replace('$', '').replace('*', '').replace(' ', '').strip()
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
        elif isinstance(toClean, float):
            # toClean is not a String; check if it is a NaN float (which we treat as zero)
            if isnan(toClean):
                return 0.0
            else:
                print("Parsed a float?")
                sys.exit(1)
        # Return None if the value cannot be determined
        return None
        
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

    def urlList(url, year):
        """Obtains a list of TIF DAR URLs using BeautifulSoup."""

        # Obtain a 2 digit year
        yr = str(year)[-2:]
        # Load TIF reports URL for a specific year
        r = requests.get(url)
        # Parses through HTML
        soup = BeautifulSoup(r.text, "html.parser")
        #links = soup.find_all(href=True) #contains hyperlink
        # Return a List of PDF links
        pdf_links = ["https://www.chicago.gov" + link['href'] for link in soup.find_all(href=lambda href: href and href.endswith(f'AR{yr}.pdf'))]
        # Remove any duplicates
        outList = []
        [outList.append(url) for url in pdf_links if url not in outList]
        # ! - Added in 2024, preserved in 2025 (23 report, 24 report) - href exists for this PDF but the URL is invalid, and is not visible on the webpage itself
        archerCourtsUrlToRemove = f'https://www.chicago.gov/content/dam/city/depts/dcd/tif/{yr}reports/T_067_ArcherCourtsAR{yr}.pdf'
        if archerCourtsUrlToRemove in outList and int(year) <= 2022:  
            outList.remove(archerCourtsUrlToRemove)
        return outList

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

    def getTextCoords(pdf, page, target_text):
        with pdfplumber.open(pdf) as pdf:
            page = pdf.pages[page-1] 
            for word in page.extract_words():
                if re.search(target_text, word["text"]):
                    # print(word)
                    return word
        return None  # Target text not found

    def fixHeader_termTable(df, searchstr):
        """Eliminated the extraneous rows on the top by finding the first TIF"""
        # * 2025 Update
        # Find index of first real data row (contains search string)
        idx = df.index[df.apply(lambda row: row.astype(str).str.contains(searchstr, case=False, na=False).any(), axis=1)]
        if len(idx) == 0:
            raise ValueError(f"Search string '{searchstr}' not found in DataFrame.")
        first_real_row = idx[0]
        # Drop everything above that row
        df = df.iloc[first_real_row:]
        # Reset index after slicing
        df.reset_index(drop=True, inplace=True)
        # Assign fixed headers
        df.columns = ["Name of Redevelopment Project Area", "Date Designated", "Date Terminated"]
        # Return final term table DateFrame
        # ! TODO - Eliminate exraneous rows at the bottom of the dataframe
        return df

    def fixHeader(df, searchStr):
        """Gets the header row by concatenating multiple rows; returns a list of column headers"""
        endRow = int(df.index[df[0].str.contains(searchStr, case=False, na=False)].values[0])
        header_row = df.iloc[:endRow].fillna('').apply(lambda x: ' '.join(x.str.strip()), axis=0).tolist()
        header_row = [header.strip() for header in header_row]
        header_row = [header for header in header_row if header]
        header_row = [re.sub(r'\s+', ' ', header) for header in header_row] # Remove double spaces
        # Omit the first rows and add the merged header back in
        df = df.iloc[endRow:].reset_index(drop=True)
        df.columns = header_row
        return df

    def mergeNewYear(masterFp, mergeFp):
        """
        Merge new rows from mergeFp into masterFp.
        
        Parameters:
            masterFp (str): Path to master CSV.
            mergeFp (str): Path to new year CSV.
            
        Returns:
            pd.DataFrame: The updated master DataFrame.
        """
        # Read CSVs
        master_df = pd.read_csv(masterFp)
        master_df_len = len(master_df)
        merge_df = pd.read_csv(mergeFp)
        merge_df_len = len(merge_df)
        
        # Confirm original master row count
        
        print(f"Original master row count: {master_df_len}")
        
        # Append new rows (only rows not already in master)
        # Assuming 'ID' or similar unique column exists; adjust if needed
        # If no unique ID, this will append all rows
        combined_df = pd.concat([master_df, merge_df], ignore_index=True).drop_duplicates()
        
        new_count = len(combined_df)
        added_rows = new_count - master_df_len
        print(f"New rows added: {added_rows}")
        # Confirm this matches the appended data
        if added_rows != merge_df_len:
            print(f"ERROR: Expected {merge_df_len} rows to append, but found {added_rows} actually appended. Data will remain unmodified")
            return None
        
        # Write updated master back to disk
        combined_df.to_csv(masterFp, index=False)
        print(f"Master CSV updated: {masterFp}")

        # Sort the Data
        # Assuming your DataFrame is called df
        combined_df = combined_df.sort_values(by=['tif_name', 'tif_year'], ascending=[True, True]).reset_index(drop=True)
        
        return combined_df
        


class YearParse:
    """An Object that obtains and stores one year's worth of DAR Objects"""
    
    def __init__(self, year, yearUrl, outDir):
        self.year = year
        self.yearUrl = yearUrl
        self.outDir = outDir
        self.urlList = Tools.urlList(yearUrl, self.year) # Pull the URLs from the DAR webpage
        self.termTable = self.parseTermTable_sec1(self.urlList[0], outDir) # Parse the 1st TIF's Term Table
        self.darList = []
        self.dictList = []

    def buildCsvFromDicts(self, csvFp):
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

        # Write the data to the CSV file
        with open(csvFp, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            # Write the header row
            writer.writerow(fieldnames)
            # Write the data rows
            for dictionary in self.dictList:
                row = [dictionary.get(key, "") for key in fieldnames]
                writer.writerow(row)
            print("CSV File saved to: " + csvFp)


        # Get the list of keys from the first dictionary in the list
        # if len(self.dictList) > 0 :
        #     fieldnames = list(self.dictList[0].keys())
        #     # Write the data to the CSV file
        #     with open(csvFp, 'w', newline='') as csvfile:
        #         # Open the CSV and pass the fieldnames
        #         writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        #         # Write the header row (uses fieldnames)
        #         writer.writeheader()
        #         # Write the data rows (each dict in dictList is one TIF)
        #         for dict in self.dictList:
        #             writer.writerow(dict)
        #     print("CSV File saved to: " + csvFp)
        # else:
        #     print('Unable to save CSV: No data found in dictList')
    
    def parseTermTable_sec1(self, firstUrl, outDir):
        """Saves the Termination Table CSV to outDir"""
        dfs = tabula.read_pdf(
            input_path=firstUrl,
            pages='1-4', # adjust dynamically based on year?
            pandas_options={'header': None},
        )
        # Drop first column from first page of the table (it is empty)
        dfs[0] = dfs[0].drop(0, axis=1)
        dfs[0].columns = dfs[0].columns = range(len(dfs[0].columns))
        # Combine all the DataFrames into one
        df = pd.concat(dfs, ignore_index=True)
        # * MODIFY THIS - if '105th Vincennes' is no longer the 1st TIF in the Sec 1 table (and in the URL List)
        # Fix the header and indicies
        df = Tools.fixHeader_termTable(df, '105th/Vincennes')
        # Save the DataFrame to a CSV in outDir
        df.to_csv(os.path.join(outDir, f"{self.year}_termTable.csv"), index=False)
        # Return the DataFrame
        print(df)
        return df

    def setLocale(self):
        # Set the locale for each process
        locale.setlocale(locale.LC_NUMERIC, 'en_US.UTF-8')

    def run(self):
        startTime = time.time()
        print(self.urlList)

        # ! - OPTION #1: Without Threading or Multiprocessing (Slow)
        # isFail = False
        # try:
        #     for url in self.urlList:
        #         dar = DAR(self.year, url, self.termTable)
        #         self.darList.append(dar)
        #         self.dictList.append(dar.outDict)
        #         print(json.dumps(dar.outDict, indent=4))
        #         # input('Press Enter to coninue...')
        # except:
        #     self.buildCsvFromDicts(os.path.join(self.outDir, f'{self.year}_out.csv')) # TODO: command line arg for output directory?
        #     # Print the runtime in minutes:seconds format
        #     endTime = time.time()
        #     runtime_seconds = endTime - startTime
        #     runtime_minutes = runtime_seconds // 60
        #     runtime_seconds %= 60
        #     print(f"Program runtime: {int(runtime_minutes)} minutes {int(runtime_seconds)} seconds")

       
        # ! - OPTION #2: With Threading (Much Faster) 
        # with concurrent.futures.ThreadPoolExecutor() as executor:
        #     # Get Term Table from first URL (this is done one time only)
        #     self.termTable = executor.submit(self.parseTermTable_sec1, self.urlList[0], self.outDir).result()
        #     print(self.termTable)
        #     future_to_dar = {executor.submit(DAR, self.year, url, self.termTable): url for url in self.urlList}
        #     # Iterate the completed futures to obtain the DAR object data
        #     for future in concurrent.futures.as_completed(future_to_dar):
        #         # url = future_to_dar[future]
        #         dar = future.result()
        #         self.darList.append(dar)
        #         self.dictList.append(dar.outDict)
        #         print(json.dumps(dar.outDict, indent=4))

        # ! - OPTION #3: With Multiprocessing (Fastest)
        isFail = False
        try:
            # Create a multiprocessing Pool
            pool = multiprocessing.Pool(initializer=self.setLocale, initargs=())
            # Apply DAR to each URL in parallel
            results = []
            for url in self.urlList:
                result = pool.apply_async(DAR, args=(self.year, url, self.termTable))
                results.append(result)
            # Wait for the results and collect DAR objects
            for result in results:
                dar = result.get()
                self.darList.append(dar)
                self.dictList.append(dar.outDict)
                print(json.dumps(dar.outDict, indent=4))
            # Close the multiprocessing Pool
            pool.close()
            pool.join()
        except Exception as e:
            # Handle keyboard interrupt (Ctrl+C)
            print(f"Program failed, error occured: {e=}")
            traceback.print_exc()
            pool.terminate()
            pool.join()
            # Perform any necessary cleanup or finalization steps
            isFail = True
            
        # # After one year is parsed, store output in a CSV
        if not isFail:
            self.buildCsvFromDicts(os.path.join(self.outDir, f'{self.year}_out.csv')) # TODO: command line arg for output directory?
        # Print the runtime in minutes:seconds format
        endTime = time.time()
        runtime_seconds = endTime - startTime
        runtime_minutes = runtime_seconds // 60
        runtime_seconds %= 60
        print(f"Program runtime: {int(runtime_minutes)} minutes {int(runtime_seconds)} seconds")

class DAR:
    """Parses and stores data from a single TIF DAR PDF."""

    def __init__(self, year, url, termTable_df):
        """Initializes a DAR object."""

        self.year = year
        self.pdfUrl = url
        self.pdf = io.BytesIO(requests.get(url).content)
        try:
            self.sec31 = Tools.getPageNumFromText(self.pdf, 'SECTION 3.1')
        except:
            print("Tools.getPageNumFromText() ERROR on 'SECTION 3.1'")
            print("ASSUMING PAGE 6...")
            self.sec31 = 6
        try:
            self.sec32a = Tools.getPageNumFromText(self.pdf, 'ITEMIZED LIST OF ALL EXPENDITURES FROM THE SPECIAL TAX ALLOCATION FUND')
        except:
            print("Tools.getPageNumFromText() ERROR on 'ITEMIZED LIST OF ALL EXPENDITURES FROM THE SPECIAL TAX ALLOCATION FUND'")
            print("ASSUMING PAGE 8...")
            self.sec32a = 8
        try:
            self.sec32b = Tools.getPageNumFromText(self.pdf, "Section 3.2 B")
        except:
            print("Tools.getPageNumFromText() ERROR on 'Section 3.2 B'")
            print("ASSUMING PAGE 11...")
            self.sec32a = 8
        self.sec31_df = None
        self.sec32b_df = None
        self.startYear = -1
        self.endYear = -1
        self.outDict = {}
        # CAN WE CONVERT THESE 4 LINES INTO ASYNC?
        self.setIdNameYear_sec31() 
        self.setStartEndDates(termTable_df)
        self.sec31_df = self.parseData_sec31()
        self.sec32b_df = self.parseAdminFinanceBank_sec32b()
        # Create an event loop
        # loop = asyncio.get_event_loop()
        # # Run the async methods concurrently
        # tasks = [
        #     self.setIdNameYear_sec31(),
        #     self.setStartEndDates(termTable_df),
        #     self.parseData_sec31(),
        #     self.parseAdminFinanceBank_sec32b()
        # ]
        # results = loop.run_until_complete(asyncio.gather(*tasks))
        # # Assign the results to instance variables
        # self.sec31_df = results[2]
        # self.sec32b_df = results[3]

    def setStartEndDates(self, df):
        """Sets outDict start and end years from the Term Table DataFrame"""
        # Obtain the appropriate years from the DataFrame
        tifName = self.outDict['tif_name']
        print(f'tifName: {tifName}')
        # Set Column Names
        nameCol = df.filter(like='Name of Redevelopment Project Area').columns.tolist()[0]
        desigCol = df.filter(like='Date Designated').columns.tolist()[0]
        termCol = df.filter(like='Date Terminated').columns.tolist()[0]
        # Parse values
        try:
            print(df[df[nameCol] == tifName])
            self.startYear = df[df[nameCol] == tifName].loc[:, df.columns.str.contains(desigCol, case=False)].values[0][0].split('/')[2]
            self.endYear = df[df[nameCol] == tifName].loc[:, df.columns.str.contains(termCol, case=False)].values[0][0].split('/')[2]
        except:
            print("FAILED ON: ", self.outDict['tif_name'])
            print("URL: ", self.pdfUrl)

        self.outDict['start_year'] = self.startYear
        self.outDict['end_year'] = self.endYear

    def setIdNameYear_sec31(self):
        """Obtains the name and year of a TIF from a PDF."""
        
        # Set up file logging that works with multiprocessing
        log_file = "tabula_debug.log"
        logging.basicConfig(filename=log_file, level=logging.INFO, 
                        format='%(asctime)s - %(processName)s - %(message)s',
                        filemode='a')
        
        filename = self.pdfUrl.split("/")[-1]
        
        try:
            logging.info(f"STARTING: {filename} | Path: {self.pdf}")
            
            # Your existing code...
            self.outDict['tif_year'] = self.year
            filename_parts = self.pdfUrl.split("/")[-1].split('_')
            tifNumber = int(filename_parts[1])
            self.outDict['tif_number'] = tifNumber
            
            df = tabula.read_pdf(
                input_path=self.pdf,
                pages=self.sec31,
                area=[50, 0, 97, 500],
                pandas_options={'header': None},
                silent=True
            )[0]
            
            tifName = str(df.iloc[2,0])
            self.outDict['tif_name'] = tifName
            
            logging.info(f"SUCCESS: {filename}")
            
        except Exception as e:
            logging.error(f"FAILED: {filename} | Error: {str(e)}")
            # Copy the failing PDF to a known location
            try:
                import shutil
                failed_pdf_path = f"failed_pdf_{filename}"
                shutil.copy2(self.pdf, failed_pdf_path)
                logging.error(f"COPIED FAILED PDF TO: {failed_pdf_path}")
            except:
                pass
            raise

    # def setIdNameYear_sec31(self):
    #     """Obtains the name and year of a TIF from a PDF."""
        
    #     # * Set the TIF year
    #     self.outDict['tif_year'] = self.year
    #     # * Set the TIF number
    #     filename = self.pdfUrl.split("/")[-1].split('_')
    #     tifNumber = int(filename[1])
    #     self.outDict['tif_number'] = tifNumber
    #     # * Set the TIF name
    #     # tifName = filename[2][:-8] 
    #     # Makes a Dataframe out of the Section 3.1 Header (usually Page 6)
    #     df = tabula.read_pdf(
    #         input_path=self.pdf,
    #         pages=self.sec31, 
    #         area=[50, 0, 97, 500], # [topY, leftX, bottomY, rightX]
    #         pandas_options={'header': None},
    #         silent=True  # Suppress stderr output
    #     )[0]
    #     # Obtains the name and year by table location
    #     tifName = str(df.iloc[2,0])
    #     self.outDict['tif_name'] = tifName
    #     # tifYear = str(df.iloc[0,0]).split()[-1]
       
    def parseData_sec31(self):
        """Converts TIF Section 3.1 into a CSV and parses the values; returns ID number or None"""

        # ? Remove below?
        # Obtain ID from URL
        # filename = self.pdfUrl.split("/")[-1]
        # pattern = r"T_(\d+)_"
        # match = re.search(pattern, filename)
        # if match:
        #     idNum = int(match.group(1))
        #     self.outDict['tif_number'] = idNum
        # else:
        #     print("ID number not found.")
        #     return None
        # ! TODO - change to use Property Tax Increment as the x1 point=more reliable
        source_coords = Tools.getTextCoords(self.pdf, self.sec31, 'SOURCE')
        top = source_coords['top']
        fund_coords = Tools.getTextCoords(self.pdf, self.sec31, 'FUND')
        bottom = fund_coords['bottom']
        # cumuCol_coords = Tools.getTextCoords(self.pdf, self.sec31, 'Cumulative')
        x1 = source_coords['x1']
        # *STEP 1: READ PDF INTO DATAFRAME
        df = tabula.read_pdf(
            input_path=self.pdf,
            pages=self.sec31, 
            area=[top-25, 0, 600, bottom+3], # [topY, leftX, bottomY, rightX]
            # ! area above should work for 2017 and beyond. if not, fix Tools.getTextCords() calls
            # * MODIFY THIS - use PDF X-Change viewer to see coordinates on a test DAR in command line, adjust as needed
            columns=[0, x1+192, x1+267, x1+339],
            stream=True,
            pandas_options={'header': None},
        )[0]
        # *STEP 2: CLEAN DATAFRAME HEADER
        sourceColName = 'SOURCE of Revenue/Cash Receipts:'
        curYearColName = 'Revenue/Cash Receipts for Current Reporting Year'
        cumColName = 'Cumulative Totals of Revenue/Cash Receipts for life of TIF'
        # sourceColName = df.filter(like='SOURCE').columns.tolist()[0]
        try:
            # Remove unnamed column full of dollar signs, if it is there (>= 2019)
            # if int(self.outDict['tif_year']) >= 2019:
            df = df.drop(0, axis=1)
            df.columns = range(len(df.columns))
            # Merge the first 5 rows to fix the header
            df = Tools.fixHeader(df, 'Property Tax Increment')
            #df.drop(df.columns[df.columns.str.contains('unnamed',case = False)],axis = 1, inplace = True)
            # Source Column Name
            sourceColName = df.filter(like='SOURCE').columns.tolist()[0]
            curYearColName = df.filter(like='Current').columns.tolist()[0] # replace columns.tolist
            cumColName = df.filter(like='Cumulative').columns.tolist()[0] # replace columns.tolist
        except:
            print("FAILED ON: ", self.outDict['tif_name'])
            print("URL: ", self.pdfUrl)
        # *STEP 3: PARSE CLEANED DATAFRAME INTO DICTIONARY
        # Obtain the Pandas series for the 'Property Tax Increment' Row
        propTaxIncRow = df[df[sourceColName] == 'Property Tax Increment']
        # Obtain the Current and Cumulative Strings out of the propTaxIncRow series
        propTaxIncCur = propTaxIncRow[curYearColName].values[0]
        propTaxIncCum = propTaxIncRow[cumColName].values[0]
        # Use the user-defined Tools.stof() to clean the Strings to Integers for storage in self.outDict
        self.outDict['property_tax_extraction'] = int(Tools.stof(propTaxIncCur))
        self.outDict['cumulative_property_tax_extraction'] = int(Tools.stof(propTaxIncCum))

        # Obtain the Pandas series for the 'Transfers from Municipal Sources' Row
        transFromMunRow = df[df[sourceColName] == 'Transfers from Municipal Sources']
        # Obtain the Current and Cumulative Strings out of the propTaxIncRow series
        transFromMunCur = transFromMunRow[curYearColName].values[0]
        transFromMunCum = transFromMunRow[cumColName].values[0]
        # Use the user-defined Tools.stof() to clean the Strings to Integers for storage in self.outDict
        self.outDict['transfers_in'] = int(Tools.stof(transFromMunCur))
        self.outDict['cumulative_transfers_in'] = int(Tools.stof(transFromMunCum))

        # Obtain the Pandas series for the 'Total Expenditures/Cash Disbursements' Row
        totExpRow = df[df[sourceColName] == 'Total Expenditures/Cash Disbursements (Carried forward from']
        # Obtain the value as a String
        totExp = totExpRow[curYearColName].values[0]
        # Use the user-defined Tools.stof() to clean the String to an Integer for storage in self.outDict
        self.outDict['expenses'] = int(Tools.stof(totExp))

        # Obtain the Pandas series for the 'FUND BALANCE, END OF REPORTING PERIOD*' Row
        fundBalRow = df[df[sourceColName] == 'FUND BALANCE, END OF REPORTING PERIOD*']
        # Obtain the value as a String
        fundBal = fundBalRow[curYearColName].values[0]
        # Use the user-defined Tools.stof() to clean the String to an Integer for storage in self.outDict
        self.outDict['fund_balance_end'] = int(Tools.stof(fundBal))

        # Obtain the Pandas series for the 'Transfers to Municipal Sources' Row
        transToMunRow = df[df[sourceColName] == 'Transfers to Municipal Sources']
        if not transToMunRow.empty:
            # Obtain the value as a String
            transToMun = transToMunRow['Revenue/Cash Receipts for Current Reporting Year'].values[0]
            # Use the user-defined Tools.stof() to clean the String to an Integer for storage in self.outDict
            self.outDict['transfers_out'] = Tools.stof(transToMun)
        else:
            # We cannot identify a 'Transfers to Municipal Sources' row, so value is 0.0
            self.outDict['transfers_out'] = 0.0

        # Obtain the Pandas series for the 'Distribution of Surplus' Row
        distSurpRow = df[df[sourceColName] == 'Distribution of Surplus']
        # Obtain the value as a String
        distSurp = distSurpRow[curYearColName].values[0]
        # Use the user-defined Tools.stof() to clean the String to an Integer for storage in self.outDict
        self.outDict['distribution'] = int(Tools.stof(distSurp))

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
        # Parse each Admin Cost and sum them; assume larger value is more accurate
        adminCosts_service = df[df['Service'] == 'Administration']['Amount'].apply(Tools.stof).sum()
        adminCosts_byName = df[df['Name'].astype(str).str.contains('City Program Management Cost|City Staff Cost', case=False, na=False)]['Amount'].apply(Tools.stof).sum()
        # adminCosts = max(adminCosts_service, adminCosts_byName)
        # if adminCosts_service != adminCosts_byName:
        #     print('\nAdmin Cost Discrepancy! Larger value chosen between', adminCosts_service, 'and', adminCosts_byName)
        #     print(f"Chosen Admin Value for TIF #{self.outDict['tif_number']}: {adminCosts}\n")
        # TODO: rely on the names, not service administration
        # Parse each Finance Cost Amount and sum them
        financeCosts = df[df['Service'] == 'Financing']['Amount'].apply(Tools.stof).sum()
        # Obtain the Bank Name(s)
        bankNameList = df[df['Service'] == 'Financing']['Name'].drop_duplicates().tolist()
        if "Amalgamated Bank of Chicago" in bankNameList:
                    bankNameList[bankNameList.index("Amalgamated Bank of Chicago")] = "Amalgamated Bank"
        bankNames = ', '.join(sorted(bankNameList))
        # Set the adminCosts, financeCosts, and bankNames
        self.outDict['admin_costs'] = adminCosts_byName # ? - adminCosts
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
    outDir = f'C:\\Users\\w\\clonedGitRepos\\chi-tif-parser\\csvs\\{year}'
    if not os.path.exists(outDir):
        os.makedirs(outDir)

    # * DAR URLs to Parse
    darYearsUrls = Tools.darYearsUrls()
    try:
        url = darYearsUrls[year]
    except KeyError as e:
        print(f'{e=}')
        print(f'No URL found for {year}')
        sys.exit(1)
    # ! Confirm this works properly
    yp = YearParse(year, url, outDir)
    yp.run()

    # * Wait for Input before merging into master (added in 2025)
    # Helper Function
    def get_merge_master_input():
        mergeMasterInput = input(f"Would you like to merge this data to the master? (y/n)\nHardcoded Master File Path: {masterFp}\n")
        if mergeMasterInput == 'y':
            return 'y'
        elif mergeMasterInput == 'n':
            return 'n'
        else:
            print(f"'{mergeMasterInput}' is invalid input. Please enter 'y' or 'n'.")
            return get_merge_master_input()  # Recursive call
        
    masterFp = r"C:\Users\w\clonedGitRepos\chi-tif-parser\csvs\chi-tif-data-master.csv"
    choice = get_merge_master_input()
    if choice == 'y':
        # Do merge
        Tools.mergeNewYear(masterFp, os.path.join(outDir, f'{year}_out.csv'))
    else:
        # Skip merge
        pass


if __name__ == "__main__":
    main()
