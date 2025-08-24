import pandas as pd
import geopandas as gpd
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





# GEOPANDAS MERGING
outFp = r"C:\Users\w\Desktop\TIF_Boundaries\merged.shp"
old = r"C:\Users\w\Desktop\TIF_Boundaries\geo_export_51c_deprecDec2015.shp"
new = r"C:\Users\w\Desktop\TIF_Boundaries\chiTifBoundaries.shp"
oldDf = gpd.read_file(old)
newDf = gpd.read_file(new)

# superfluous
deprecated_features = oldDf[~oldDf['tif_number'].isin(newDf['tif_number'])]
print("DEPRECATED FEATURES:")
print(sorted(deprecated_features['tif_number'].tolist()))

cat = pd.concat([newDf, deprecated_features])
print("MERGED FEATURES:")
print(sorted(cat['tif_number'].tolist()))

