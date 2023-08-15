import pandas as pd
import PyPDF2, pdfplumber, tabula
import requests, re, io, os
from bs4 import BeautifulSoup

def getTextCoords(pdf, target_text, pageIndex):
        with pdfplumber.open(pdf) as pdf:
            page = pdf.pages[pageIndex]  # Assuming you want to check the first page
            for word in page.extract_words():
                if re.search(target_text, word["text"]):
                    print(word)
                    return word
        return None  # Target text not found

def configure_pandas():
    pd.set_option('display.max_columns', None)
    pd.set_option('display.max_rows', None)
    pd.set_option('display.width', 100000)

configure_pandas()
pdf = io.BytesIO(requests.get('https://www.chicago.gov/content/dam/city/depts/dcd/tif/11reports/T_072_24thMichiganAR11.pdf').content)

