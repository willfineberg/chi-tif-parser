import os
import pandas as pd
import pdfquery
import tabula
from bs4 import BeautifulSoup
import requests

# Load 2021 TIF reports url
url = "https://www.chicago.gov/city/en/depts/dcd/supp_info/district-annual-reports--2021-.html"
r = requests.get(url)

# Parses through html
soup = BeautifulSoup(r.text, "html.parser")
links = soup.find_all(href=True) #contains hyperlink

# List of pdf links
pdf_links = ["https://www.chicago.gov" + link['href'] for link in soup.find_all(href=lambda href: href and href.endswith('.pdf'))]
print(pdf_links)

# Directory of PDFs to produce XML from
pdfDir = r"c:\sc\pdf"
xmlDir = r"c:\sc\xml"

# Loop each PDF in pdfDir
for link in pdf_links:
    # Obtain the PDFQuery Object and load it
    pdfPath = os.path.join(pdfDir, filename)
    pdf = pdfquery.PDFQuery(pdfPath)
    pdf.load(5) # Page 6

    # Write the loaded data into XML
    xml_path = os.path.join(xmlDir, os.path.basename(pdfPath).replace('.pdf', '.xml'))
    pdf.tree.write(xml_path, pretty_print=True)

    # Post-processing of XML elements
    cumulative_totals = pdf.pq('LTTextLineHorizontal:overlaps_bbox("468.52, 392.733, 524.154, 402.718")').text()
    # page = pd.DataFrame({'cumulative_totals': cumulative_totals}, index=[0])
    print(cumulative_totals)
