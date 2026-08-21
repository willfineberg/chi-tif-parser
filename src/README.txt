AUTHOR: WILL FINEBERG
DATE MODIFIED: 8/19/2026

THIS DOCUMENTS THE ANNUAL TIF PROCESS WHILE PERFORMING THE 
2025 TIF PARSING IN 2026.

THIS DOCUMENT IS INTENDED FOR PERSONAL REFERENCE ONLY AND 
IS ADMITTEDLY NOT AS THOROUGH AS IT COULD AND SHOULD BE. Maybe one day...

******************************************************************************************
8/20/2026 NOTE-TO-SELF FOR 2026 REPORTS BELOW -- LESSONS LEARNED AND TODOS
******************************************************************************************

create_tif_charts.py is overenginnered. Funcs are good, but OOP is bad.
Design the ENTIRE process as module-level code. This includes the process of
running create_tif_charts.py (supp with test.py to fix table error for 25 TIFs
using Option #1 while testing, and Option #3 once confirmed),then check_tif_names.py, 
then create_tif_charts.py (and ../docs/index.html replacement + charts backup). 
map_report_urls_to_excel.py is not included since Excel will remain manual. 

Once processes are properly isolated into module-level code (class for parsing, 
class for charts creation in one file), create a 2nd file that is a driver. Exisiting
DAR class could be used for a 3rd adhoc file that can do one-offs or lists (even with
URL discovery TIF number(s) entry?) -- but honestly? I fear there is no valid use case.

...So just do 2 files, module w/ funcs and a driver? Maybe 1-2 classes but top-level funcs
and no classes might cut it. Put it all together top-level first and decide. 

Also, check SetupIdle.py and see if we want to put some of that
stray code elsewhere (archive funcs, expand geopandas into separate file (or same 
file as a small class? or just a standalone script?) for shapefile update process, 
and document that process).

Finally, clean up the repo. ../csvs by moving XLSX stuff to a different folder and 
putting master backups/copies in new folder ../csvs/master-backups. Change file/folder- 
names to all use '-' or all use '_' and not both randomly. 

I think that's it?

Oh, and archive GEE code into this repo during each annual update for good measure. 

******************************************************************************************
******************************************************************************************

---
SEQUENTIAL STEPS (Using VS Code)
---

-- PARSING DATA -- 

1. Windows stole "py", but I found my install using `py -0p` at "C:\Users\w\AppData\Local\Programs\Python\Python38\python.exe". (Do this on Debian next time? and come back to Win for Excel report only?)

2. Running it failed with IndexError from YearParse.setIdNameYear_sec31() due to Tabula referencing hardcoded X,Y coords (sec31 name shifted). Claude generated a new version using pdfplumber anchors (and gave me a new Option #1 to aid in debugging).

3. New code worked. Switching back to Option #3 and running to get data: `C:\Users\w\clonedGitRepos\chi-tif-parser\src>C:\Users\w\AppData\Local\Programs\Python\Python38\python.exe chi_tif_parser.py 2025`.

4. Merge into master failed, but data parsing was successful. Open in Excel for review.

5. Need to fix code and re-parse. Cumulatives are off due to tabula coord cutting it short (sec31 table shifted). Claude provided code for ./test.py which shows the coords for a test doc, this helped me figure out the new coords easily to make the ./chi_tif_parser updates using PDF X-Change Editor.

6. Successful w/ new coords. Merge into master worked as well. AI suggested some spot checks based on looking at whole master for data quality issues and all checked out. Proceeding with data.

-- TOM'S SHEET --

7. Assemble Tom's sheet. I created a template using a named range on a separate sheet to easily update the year. Copy this file, rename it, and open it. 

8. Change the TIF_YEAR A1 cell to the year parsed. (Optionally, select all cells using TIF_YEAR named var range and copy/paste as values. Then you can delete the 2nd ref sheet.)

9. Copy all rows from the <YEAR>_out.csv file from this year's parsing. paste into first data row (A10) values only (Ctrl + Shift + V). Delete the extra rows (added for convenience), but not the footer/total rows or anything below it. 

9. Rename the sheet name, which is not automatic like rest. Close the workbook.

10. Get the URLs. Open `map_report_urls_to_excel.py` and change the year. Then run it from command line. It will update most of the TIF Names with hyperlinks. Review the output and manually hyperlink the rest.

-- REPORT CHARTS WEBPAGE UPDATE --

11. Run `create_tif_charts.py` from the command line, passing in the parsed year as the first and only arg. It will output a new HTML file within "../charts".

12. Github will reference "../docs/index.html" for the web app deployed to "https://willfineberg.github.io/chi-tif-parser/". Copy the new output from the previous step in "../charts" and paste it into "../docs". Delete index.html, and rename the pasted file as index.html.

-- PUSH TO GITHUB -- 

13. Use VS Code UI to push to Github.

14. Once the deployment updates, ensure the new app looks good and functions properly.

-- GEE APP UPDATES -- 

15. Follow steps marked ANNUAL UPDATE in the users/wtfineberg/mcdc/TopTIFs file in the code.earthengine.google.com GEE Code Editor. (ARCHIVE THIS CODE!!!)

16. Re-publish app once code is updated.

17. Update snapshot URL in ../README.md.

-- INFORM TOM -- 
 
17. Email Tom with the updated TIF Illumination sheet.