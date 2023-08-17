<img src="docs/images/civiclab_tifillum.jpg" width="240" alt="The CivicLab Logo">

# 2023 MCDC Project with The CivicLab
- [put generalized info about our project here?]

## Chicago Shiny TIF Heatmap 
- [put info about the shiny app and how to use it here]

## Chicago Top TIFs Web App
Chicago Top TIFs is a Google Earth Engine Web App designed to illuminate the finances of the City of Chicago. Please review ["App Features"](https://github.com/willfineberg/chi-top-tifs#app-features) and ["What Are These Variables?"](https://github.com/willfineberg/chi-top-tifs#what-are-these-variables) to better understand the [Chicago Top TIFs Web App](https://wtfineberg.users.earthengine.app/view/toptifs).

- Chicago Top TIFs Web App URL: https://wtfineberg.users.earthengine.app/view/toptifs
- Google Earth Engine Snapshot: https://code.earthengine.google.com/f132f5ff21f5b0b2d9e273e950d41d18

### App Features
- **Modify Map (Top/Bottom Five Outlines)**
  - The app will find the largest five and smallest five values across all TIFs based on your selections. Changing the Selected Year or Variable (top-left) will modify the outlines appropriately. 
    - For example, the default map highlights the five TIFs with the largest Property Tax Extraction in 2022 as well as the five TIFs with the smallest Property Tax Extraction values in 2022.
- **TIF Selection**
  - You can select a tif by clicking within the shape boundaries on the map. This will outline the district in cyan and highlight it in yellow (similar to the top/bottom five outlines). TIF Selection causes both Data Displays to update.
- **Data Displays**
  - Data Displays are updated by TIF Selection. There are two different displays of the TIF data:
    - Top-Right UI: This panel is populated with all data points for the current TIF selection within the currently selected year.
    - Bottom-Left UI: This panel is populated with a Bar Chart that visualizes all values of the currently selected variable for the TIF that was clicked.

### What Are These Variables?
Data for Chicago TIF Districts are released once per year. A yearly report for each TIF contains a variety 
Here are explanations for each data variable accessed in the [Chicago Top TIFs Web App](https://wtfineberg.users.earthengine.app/view/toptifs):
| Variable                               | Explanation                                 |
| -------------------------------------- | ------------------------------------------- |
| **TIF Lifespan**                       | The starting year through the proposed ending year. |
| **Current Data Year**                  | The year that the current data is from. |
| **Property Tax Extraction**            | The amount of property tax collected this year (within the TIF District). |
| **Cumulative Property Tax Extraction** | CUMULATIVE sum of property tax collected throughout the TIFs lifespan. |
| **Transfers In**                       | The amount transferred into this TIF District from neighboring TIF Districts this year. |
| **Cumulative Transfers In**            | CUMULATIVE sum of funds transferred into the TIF Fund from neighboring TIFs throughout the TIFs lifespan. |
| **Expenses**                           | The Total Expenditures. The amount of money spent on projects applicable to the TIF. |
| **Fund Balance End**                   | Balance of this TIF District's Fund at the end of the Current Data Year.    |
| **Transfers Out**                      | Amount of funds transferred out of the account and ported to a neighboring TIF District. |
| **Distribution**                       | Allocation and disbursement of funds.  |
| **Administration Costs**               | Amount taken by the City of Chicago for "City Staff Costs" and "City Program Management Costs". |
| **Finance Costs**                      | Amount provided to the TIF Fund by a banking institution. |
| **Bank Names**                         | Banks that provided the Finance Costs to the TIF Fund. |

Please refer back to this table for concise explanations of variables while utilizing the app.

# TIF Resources
### What Are TIFs?
TIF stands for Tax Increment Financing. TIF Districts are designated by the municipality to capture property taxes for a fixed period of time. The captured property taxes are used to boost development in the designated TIF district. Visit the [The CivicLab](https://www.civiclab.us/) website to read more about what TIFs are and how they work. Here are two resources to start with:
- [TIF 101 Video](https://www.civiclab.us/tif-101/)
- [How Do TIFs Work?](https://www.civiclab.us/tif_illumination_project/how-do-tifs-work/)

### Where Is The Data From?
* The financial data was parsed from the City of Chicago's [TIF District Annual Report webpage](https://www.chicago.gov/city/en/depts/dcd/supp_info/tif-district-annual-reports-2004-present.html). Data from 2010-2022 inclusive was parsed from the PDFs using various Python libraries.
* Shapefiles for Chicago TIF District boundaries are sourced from the [Chicago Data Portal](https://data.cityofchicago.org/browse?q=tif+boundaries&sortBy=last_modified&tags=shapefiles&utf8=%E2%9C%93). The Red Line Extension (TIF# 186) is the only exception: this shape was entered in manually.
