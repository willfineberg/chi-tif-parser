# tabula-py Documentation: https://tabula-py.readthedocs.io/en/latest/tabula.html#tabula.io.convert_into
# Please run `pip install tabula` before running tabula_pdfToCsv.py
import tabula

# Convert the first data table from the report (page 6) into a CSV
tabula.convert_into(
    input_path=r"C:\Users\w\clonedGitRepos\chicago2022TIF\mcdc_tif_research\page6_kinzie.pdf", # modify this
    output_path=r'c:\sc\out_fromTabula.csv',  # modify this
    pages="all", 
    area=[130, 43, 353, 585] # [top, left, bottom, right]
)