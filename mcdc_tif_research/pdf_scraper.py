import tabula as tb
import pandas as pd
import pdfquery

pdf = pdfquery.PDFQuery('T_052_KinzieAR21.pdf')
pdf.load(5)
pdf.tree.write('pdfXML.txt', pretty_print = True)

cumulative_totals = pdf.pq('LTTextLineHorizontal:overlaps_bbox("468.52, 392.733, 524.154, 402.718")').text()
# page = pd.DataFrame({'cumulative_totals': cumulative_totals}, index=[0])
print(cumulative_totals)

    

