AUTHOR: WILL FINEBERG
DATE CREATED: 8/9/2026 17:11 PM MST
DATE MODIFIED: 8/19/2026 

THIS DOCUMENTS THE ANNUAL TIF PROCESS WHILE PERFORMING THE 
2025 TIF PARSING IN 2026.

THIS DOCUMENT IS INTENDED FOR PERSONAL REFERENCE ONLY AND 
IS ADMITTEDLY NOT AS THOROUGH AS IT COULD AND SHOULD BE. Maybe one day...


---
SEQUENTIAL STEPS (Using VS Code)
---

-- PARSING DATA -- 

1. Check requirements.txt since windows update stole my `py` alias... Found my install using `python -0p` at "C:\Users\w\AppData\Local\Programs\Python\Python38\python.exe".

2. Running it failed with IndexError from YearParse.setIdNameYear_sec31() due to Tabula referencing hardcoded X,Y coords. Claude generated a new version using pdfplumber anchors (and gave me a new Option #1 to aid in debugging)

3. New code worked. Switching back to Option #3 and running to get data: `C:\Users\w\clonedGitRepos\chi-tif-parser\src>C:\Users\w\AppData\Local\Programs\Python\Python38\python.exe chi_tif_parser.py 2025`.

4. Merge into master failed, but data parsing was successful. Open in Excel for review.

5. Cumulatives are off due to tabula coord cutting it short. Testing Claude code for pdfplumber swap.

6. Successful. Merge into master worked as well. AI suggested some spot checks based on looking at whole master for data quality issues and all checked out. Proceeding with data.

-- TOM'S SHEET --

7. Assemble Tom's sheet. I created a template using a named range on a separate sheet to easily update the year. Copy this file, rename it, and open it.

8. Change the TIF_YEAR A1 cell to the year parsed. Copy all rows from the <YEAR>_out.csv file from this year's parsing. paste into A10 values only (Ctrl + Shift + V). Delete the extra rows, but not the total rows or anything below it. 

9. Rename the sheet name, which is not automatic like rest. Close the workbook.

10. Get the URLs. Open `map_report_urls_to_excel.py` and change the year. Then run it from command line. It will update most of the TIF Names with hyperlinks. Review the output and manually hyperlink the rest.

-- REPORT CHARTS WEBPAGE UPDATE --

11. Run `create_tif_charts.py` from the command line, passing in the parsed year as the first and only arg. It will output a new HTML file within "../charts".

12. Github will reference "../docs/index.html" for the web app deployed to "https://willfineberg.github.io/chi-tif-parser/". Copy the new output from the previous step in "../charts" and paste it into "../docs". Delete index.html, and rename the pasted file as index.html.

-- PUSH TO GITHUB -- 

13. Use VS Code UI to push to Github.

-- GEE APP UPDATES -- 