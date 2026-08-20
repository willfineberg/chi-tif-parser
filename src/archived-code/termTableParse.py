import PyPDF2, io, os, requests, tabula, tempfile, ocrmypdf, sys
import pandas as pd
from pdf2image import convert_from_bytes

def ocr(pdf, pageNum, twoPasses):
	b = io.BytesIO()
	pdfWriter = PyPDF2.PdfWriter()
	pdfPage = PyPDF2.PdfReader(pdf).pages[pageNum - 1]
	pdfWriter.add_page(pdfPage)
	pdfWriter.write(b)
	img = convert_from_bytes(b.getvalue(), dpi=300)[0]
	with tempfile.TemporaryDirectory() as tempDir:
		pngFp = os.path.join(tempDir, 'toOcr.png')
		pdfFp = os.path.join(tempDir, 'toOcr.pdf')
		img.save(pngFp, format='PNG')
		ocrmypdf.ocr(pngFp, pdfFp, optimize=0, redo_ocr=True, image_dpi=300)
		if twoPasses:
			ocrmypdf.ocr(pdfFp, pdfFp, redo_ocr=True, optimize=1)
		with open(pdfFp, 'rb') as ocred:
			return io.BytesIO(ocred.read())

# ! - MODIFY INPUT URL TO A SINGLE HIGH QUALITY PDF FOR DESIRED YEAR (if necessary)
if len(sys.argv) == 2:
    year = sys.argv[1]
else:
	print("BAD USAGE, USAGE: py termTableParse.py [year]")
	sys.exit()

url = f'https://www.chicago.gov/content/dam/city/depts/dcd/tif/{year[2:]}reports/T_072_24thMichiganAR{year[2:]}.pdf'
scratchDir = f'c:\\sc\\{year}'
if not os.path.exists(scratchDir):
    os.makedirs(scratchDir)
outFp = os.path.join(scratchDir, f'{year}__termTable.csv')

# * Obtain Full PDF, split first 4 pages into their own BytesIO object
pdf = io.BytesIO(requests.get(url).content)

# ! - PARSE DATAFRAMES USING TABULA
# * PAGE 2
df = tabula.read_pdf(
    input_path=ocr(pdf, 2, False), # pdf,
    # pages=2,
    area=[410, 0, 695, 600], # [topY, leftX, bottomY, rightX]
    columns=[325, 430],
)[0]
# Store header row for later
headerRow = df.columns.tolist()
# Update header row to allow for concatenation
df.columns = [0,1,2]
# master will ultimately hold the whole termination table
master = df

# * Page 3
df = tabula.read_pdf(
    input_path=pdf,
    pages=3,
    area=[150, 0, 700, 600], # [topY, leftX, bottomY, rightX]
    columns=[325, 430],
    pandas_options={'header': None},
)[0]
master = pd.concat([master, df], ignore_index = True)

# * Page 4
df = tabula.read_pdf(
    input_path=pdf,
    pages=4,
    area=[150, 0, 700, 600], # [topY, leftX, bottomY, rightX]
    columns=[325, 430],
    pandas_options={'header': None},
)[0]
master = pd.concat([master, df], ignore_index = True)

# * Page 5
df = tabula.read_pdf(
    input_path=pdf,
    pages=5,
    area=[150, 0, 700, 600], # [topY, leftX, bottomY, rightX]
    columns=[325, 430],
    pandas_options={'header': None},
)[0]
master = pd.concat([master, df], ignore_index = True)

# * Page 6
df = tabula.read_pdf(
    input_path=pdf,
    pages=6,
    area=[150, 0, 700, 600], # [topY, leftX, bottomY, rightX]
    columns=[325, 430],
    pandas_options={'header': None},
)[0]
master = pd.concat([master, df], ignore_index = True)

# ! - All pages concatenated into master
# fix header
master.columns = headerRow
# save CSV
master.to_csv(outFp)