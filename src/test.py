import requests, io, pdfplumber, tabula, re

url = 'https://www.chicago.gov/content/dam/city/depts/dcd/tif/25reports/T_072_24thMichiganAR25.pdf'
pdf = io.BytesIO(requests.get(url).content)

def getTextCoords(pdf, page, target_text):
    with pdfplumber.open(pdf) as p:
        pg = p.pages[page-1]
        for word in pg.extract_words():
            if re.search(target_text, word["text"]):
                return word
    return None

source_coords = getTextCoords(pdf, 5, 'SOURCE')
print('SOURCE:', source_coords)
pdf.seek(0)
fund_coords = getTextCoords(pdf, 5, 'FUND')
print('FUND:', fund_coords)
print('x1:', source_coords['x1'])
print('x1+192:', source_coords['x1']+192)
print('x1+267:', source_coords['x1']+267)
print('x1+339:', source_coords['x1']+339)