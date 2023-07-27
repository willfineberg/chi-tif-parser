import PyPDF2, io, requests

# ! - MODIFY INPUT URL TO A SINGLE HIGH QUALITY PDF FOR DESIRED YEAR
url = 'https://www.chicago.gov/content/dam/city/depts/dcd/tif/14reports/T_072_24thMichiganAR14.pdf'

# * Obtain Full PDF, split first 4 pages into their own BytesIO object
pdf = io.BytesIO(requests.get(url).content)
# fullPdf = PyPDF2.PdfReader(pdf)
# pdfWriter = PyPDF2.PdfWriter()
# for pageNum in range(4): # ? - May need to modify this too? Table could take up more or less than 4 pages.
#     pdfWriter.add_page(fullPdf.pages[pageNum])
# # First 4 pages obtained, now write them into bytes
# tt_bytes = io.BytesIO()
# pdfWriter.write(tt_bytes)

# TODO: If we need OCR, implement it here
# ocr code goes here

# * Run Tabula

