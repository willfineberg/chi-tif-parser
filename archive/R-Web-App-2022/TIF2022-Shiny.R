library(shiny)
library(sf)
library(classInt)
library(leaflet)
library(tidyverse)
library(viridisLite)
library(scales)
library(gt)
library(htmltools)
library(shinythemes)
library(shinyWidgets)
library(rlang)

# Read and transform the shape files
Sf2022 <- st_read("chiTifBoundaries")
Sf2022 <- st_transform(Sf2022, crs = "+proj=longlat +datum=WGS84")


# Read in TIF 2022 data
tif2022 <- read.csv("2022_out.csv")

# Merge TIF 2022 data with shape files
Sf2022 <- Sf2022 %>%
  inner_join(tif2022,by="tif_number")

# Make the table for the app
gt_tif_2022 <- 
  tif2022 %>%
  gt() %>%
  fmt_currency(columns=c(property_tax_extraction,cumulative_property_tax_extraction,
                         transfers_in,cumulative_transfers_in,expenses,
                         fund_balance_end,transfers_out,distribution,admin_costs,
                         finance_costs),decimals=0) %>%
  cols_hide(columns=tif_year) %>%
  cols_label(tif_name="TIF Name",start_year="Start Year",end_year="End Year",
             tif_number="TIF #",property_tax_extraction="Property Tax Extraction",
             cumulative_property_tax_extraction="Cumulative Property Tax Extraction",
             transfers_in="Transfers In",
             cumulative_transfers_in="Cumulative Transfers In",expenses="Expenses",
             fund_balance_end="Fund Balance End",transfers_out="Transfers Out",
             distribution="Distribution",
             admin_costs="Administrative Costs",finance_costs="Finance Costs",
             bank="Bank") %>%
  opt_interactive(use_compact_mode=TRUE) %>%
  tab_header(title=tagList(tags$div(style=css(`text-align`="center"),
                                    HTML(local_image("CivicLabLogo.jpeg",height=px(65)))),
                           tags$div("Chicago TIF Districts 2022"))) %>%
  cols_width(contains("bank") ~ px(200),ends_with("name") ~ px(250),starts_with("cumulative") ~ px(200),everything() ~ px(150))

# Inputs for the Shiny app
ui <- fluidPage(
  theme = shinytheme("cosmo"),
  setBackgroundColor(
    color = c("#FFFFFF", "#B3DDF2", "#FF0000"),
    gradient = "linear",
    direction = "right"
  ),
  tags$h1("Chicago TIF Districts 2022"),
  fluidRow(
    column(
      width = 4,
      varSelectInput("variable","Select Variable:",data=tif2022[,6:15],
                     selected="property_tax_extraction")),
    column(
      width = 8,leafletOutput(outputId = "map"))),
  gt_output(outputId = "table")
)

# Shiny server code
server <- function(input,output, session){
  
  output$map <- renderLeaflet({
    # Using Jenks natural breaks - similar to ArcGIS
    breaks_j <- with(Sf2022,classIntervals(inject(!!input$variable),n=7,style="jenks"))
    breaks_j_color <- findColours(breaks_j,plasma(7))
    p_popup <- paste0("<strong>Variable Selected: </strong>","<br>",
                      Sf2022$tif_name,"<br>",
                      with(Sf2022,inject(dollar(!!input$variable))))
    
    leaflet(Sf2022) %>% addPolygons(stroke=FALSE,
                                    fillColor=~breaks_j_color,
                                    fillOpacity=0.75,smoothFactor=0.5,
                                    popup=p_popup,group="Chicago") %>%
      addTiles(group="OSM") %>%
      addLegend("topright",
                colors=plasma(7),
                labels=paste0("up to ",dollar(breaks_j$brks[-1])),
                title="Variable Selected:") %>%
      addLayersControl(baseGroups=c("OSM","Carto"),overlayGroups=c("Chicago"))
  })
  output$table <- render_gt(expr = gt_tif_2022)
}

# Run the app
shinyApp(ui = ui, server = server)
