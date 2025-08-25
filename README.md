
<div style="position: relative;">
  <img src="archive/images/mcdc.png" width="200" height=200 alt="MCDC Logo" style="position: absolute; right: 0;">
  <img src="archive/images/CivicLabLogo.jpeg" height='200' alt="The CivicLab Logo" style="position: absolute; left: 0;">
</div>

# Continuation of the [TIF Illumination](http://tifreports.com/) [MCDC](https://sites.northwestern.edu/mcdc/) Project with [The CivicLab](https://www.civiclab.us/)

___This is a 2025 fork of the original GitHub Repository created for 2024 report parsing. This repo will continue to be updated annually by Will Fineberg with new TIF Report Data from the City of Chicago.___

_The [TIF Illumination Project](http://tifreports.com/) uses data mining, investigatory reporting, graphic design, and popular education methods to expose the hyper-local harms Tax Increment Financing Districts bring to our communities. We have been in the field since 2013 and have been called into community over 230 times. As far as we know, this is the only civic project in America interrogating and organizing around TIFs. See www.tifreports.com. Reach us at info@tifreports.com._

_This particular project was coordinated by the [Metropolitan Chicago Data-science Corps (MCDC)](https://sites.northwestern.edu/mcdc/), which is a collaboration of non-profit or community organizations and data science students. We worked with The CivicLab on the aforementioned [TIF Illumination Project](http://tifreports.com/) to reveal City of Chicago finances through Tax Increment Financing (TIF) analysis. Please view the resources below to learn more about the City of Chicago finances and how TIFs work._

## Static HTML Product - [Chicago TIF Report Charts](https://willfineberg.github.io/chi-tif-parser/)[^3]

The [Chicago TIF Report Charts](https://willfineberg.github.io/chi-tif-parser/) provide a quick, easy, and reliable way to view TIF data. The user can use the Table of Contents to find a specific TIF where they will find a chart for each data point over time. Each TIF has blue buttons that link directly to the PDF report for the specified year. Chart data will only go back to 2010, but the blue buttons for PDFs will be available for every PDF year found on the [TIF District Annual Report webpage](https://www.chicago.gov/city/en/depts/dcd/supp_info/tif-district-annual-reports-2004-present.html). The [Chicago TIF Report Charts](https://willfineberg.github.io/chi-tif-parser/) will be updated annually.[^1]

## Dynamic GIS Web App Product - [Chicago Top TIFs Web App](https://wtfineberg.users.earthengine.app/view/toptifs/)[^3]

The [Chicago Top TIFs Web App](https://wtfineberg.users.earthengine.app/view/toptifs/) contains data from 2010-2024[^1] and was developed using [Google Earth Engine (GEE)](https://earthengine.google.com/). It provides a geospatial component for improved analysis of the TIF data.

### Web App Instructional Guide for Users

#### **_TIF Selection (click the map)_**
You can select a TIF by clicking within its boundary on the map. This will outline the district in cyan and highlight it in yellow (similar to the top/bottom five outlines). TIF Selection causes both Data Displays to update.

#### **_Modify Map Selection UI (top-left)_**
Changing the Selected Year or Variable will modify the outlines for the top 5 layer and the bottom 5 layer, as well as clear the current TIF Selection. The app is selecting the largest five and smallest five values across all TIFs based on your Selected Year and Variable. For some variables (like Transfers), the bottom 5 values will often be all zeros. The Selected Variable also determines which data the bottom-left chart will graph. To further understand the variables, please reference the [What Are These Variables?](https://github.com/philipayates/chicago2022TIF/blob/main/README.md#what-are-these-variables) table below.

#### **_Data Displays (top-right & bottom-left)_**
Selecting different TIFs, variables, and years will modify the two different Data Displays as described below:
* Top-Right UI: This panel is populated with all data points for the current **_TIF Selection_** within the currently __*Selected Year*__.
* Bottom-Left UI: This panel is populated with a Bar Chart that visualizes all values of the currently Selected Variable for the TIF that was clicked.

### For Developers

Developers can modify the JavaScript code by using the [Earth Engine Code Editor](https://developers.google.com/earth-engine/guides/playground) Snapshot URL[^2] below:

* https://code.earthengine.google.com/4e69cac1236837eeceae30a644a74a08
  * _Updated 08/24/2025_

## Chicago 2022 TIF Heatmap - Developed in [R](https://www.r-project.org/) using [Shiny](https://shiny.posit.co/)

_Unmaintained beyond 2022 reports_

For R users, code is provided to run a Shiny app locally. You will need the shape files found in the folder `chiTifBoundaries` as well as the 2022 TIF data (`2022_out.csv`) and the `CivicLabLogo.jpeg` file. The app is named `TIF2022-Shiny.R`. Be sure to save all of the files in the same directory.

For non-R users, the Shiny App for the 2022 TIF data can be found here:

* https://philipayates.shinyapps.io/apps/

## TIF Resources

### What Are TIFs?
TIF stands for Tax Increment Financing. TIF Districts are designated by the municipality to capture property taxes for a fixed period of time. The captured property taxes are used to boost development in the designated TIF district. Visit the [The CivicLab](https://www.civiclab.us/) website to read more about what TIFs are and how they work. Here are two resources to start with:
* [TIF 101 Video](https://www.civiclab.us/tif-101/)
* [How Do TIFs Work?](https://www.civiclab.us/tif_illumination_project/how-do-tifs-work/)

### Where Is The Data From?
* The financial data was parsed from the City of Chicago's [TIF District Annual Report webpage](https://www.chicago.gov/city/en/depts/dcd/supp_info/tif-district-annual-reports-2004-present.html). Data from 2010-2022 inclusive was parsed from the PDFs using various Python libraries.
* Shapefiles for Chicago TIF District boundaries are sourced from the [Chicago Data Portal](https://data.cityofchicago.org/browse?q=tif+boundaries&sortBy=last_modified&tags=shapefiles&utf8=%E2%9C%93). The Red Line Extension (TIF# 186) is the only exception: this shape was entered in manually.

### What Are These Variables?

Data for Chicago TIF Districts are released once per year. A yearly report for each TIF contains a variety of different metrics, but the ones listed below are the values that we have obtained from all PDFs from 2010 through 2023.[^1] Please refer to these explanations while using the [Chicago Top TIFs Web App](https://wtfineberg.users.earthengine.app/view/toptifs):

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
| **Distribution**                       | Disbursement of surplus funds. This is often directed to the Treasurer for reallocation elsewhere.  |
| **Administration Costs**               | Amount taken by the City of Chicago Department of Planning for "City Staff Costs" and "City Program Management Costs". |
| **Finance Costs**                      | Amount paid to a banking institution to settle debt. This is money that was loaned to the TIF Fund previously and is now being paid back to the bank. |
| **Bank Names**                         | Bank(s) that provided the financing (Finance Costs) to the TIF Fund. |

Please refer back to this table for concise explanations of variables while utilizing the app.

[^1]: Data is released annually (for the prior year) around June 30th. Expect the GEE Top TIFs Web Map to be updated around that time.
[^2]: The GEE Editor requires you to register with a Google account. Earth Engine is free for non-commercial use.
[^3]: Updated 2025-08-24
