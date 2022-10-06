import folium
import folium.plugins as plugins
import streamlit as st
from streamlit_folium import folium_static
from PIL import Image
import xarray as xr
from syn_noaa import *
import requests
import numpy.ma as ma
import pandas as pd
import matplotlib.pyplot as plt
import datetime
import branca
import branca.colormap as cm
from scipy import interpolate
from branca.element import Template, MacroElement

def legendDraw():
    template = """
    {% macro html(this, kwargs) %}

    <!doctype html>
    <html lang="en">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>jQuery UI Draggable - Default functionality</title>
      
      <script src="https://code.jquery.com/ui/1.12.1/jquery-ui.js"></script>
      
      
      <script>
      $( function() {
        $( "#maplegend" ).draggable({
                        start: function (event, ui) {
                            $(this).css({
                                right: "auto",
                                top: "auto",
                                bottom: "auto"
                            });
                        }
                    });
    });

      </script>
    </head>
    <body>

     
    <div id='maplegend' class='maplegend' 
        style='position: absolute; z-index:9999; border:2px solid grey; background-color:rgba(255, 255, 255, 0.8);
         border-radius:6px; padding: 10px; font-size:14px; right: 20px; bottom: 20px;'>
         
    <div class='legend-title'>Legend</div>
    <div class='legend-scale'>
      <ul class='legend-labels'>
        <li><span style='background:Blue;opacity:0.7;'></span>Flooded</li>
        <li><span style='background:gray;opacity:0.7;'></span>non-Flooded</li>

      </ul>
    </div>
    </div>
     
    </body>
    </html>

    <style type='text/css'>
      .maplegend .legend-title {
        text-align: left;
        margin-bottom: 5px;
        font-weight: bold;
        font-size: 90%;
        }
      .maplegend .legend-scale ul {
        margin: 0;
        margin-bottom: 5px;
        padding: 0;
        float: left;
        list-style: none;
        }
      .maplegend .legend-scale ul li {
        font-size: 80%;
        list-style: none;
        margin-left: 0;
        line-height: 18px;
        margin-bottom: 2px;
        }
      .maplegend ul.legend-labels li span {
        display: block;
        float: left;
        height: 16px;
        width: 30px;
        margin-right: 5px;
        margin-left: 0;
        border: 1px solid #999;
        }
      .maplegend .legend-source {
        font-size: 80%;
        color: #777;
        clear: both;
        }
      .maplegend a {
        color: #777;
        }
    </style>
    {% endmacro %}"""
    macro = MacroElement()
    macro._template = Template(template)
    return macro
if 'AOI_str' not in st.session_state:
    st.session_state.AOI_str = 'MississippiRiver'


# Page Configuration
st.set_page_config(layout="wide")

# Title and Description
st.title("Forecasting Inundation Extents using REOF analysis (FIER) – Sentinel-1")

thSelect=-3
row1_col1, row1_col2= st.columns([2, 1])
# Set up Geemap
with row1_col1:
    m = folium.Map(
        zoom_start=4,
        location =(36.52, -89.55),
        control_scale=True,
    )

    plugins.Fullscreen(position='topright').add_to(m)
    folium.TileLayer('Stamen Terrain').add_to(m)
    m.add_child(folium.LatLngPopup())
    folium.LayerControl().add_to(m)



with row1_col2:
    st.subheader('Determine Region of Interest')
    with st.form('Select Region'):

        region = st.selectbox(
            'Determine region:',
            ('Mississippi River', 'Red River'),
        )

        submitted = st.form_submit_button("Submit")
        if submitted:
            AOI_str = region.replace(" ", "")
            #st.write('Region:', region)
            #if region=='Mississippi River':
            #    location = [36.62, -89.15] # NEED FIX!!!!!!!!!!!
            #elif region=='Red River':
            #    location = [48.44, -97.17]

            #m = folium.Map(
            #        zoom_start = 8,
            #        location = location,
            #        control_scale=True,
            #)
            st.session_state.AOI_str = AOI_str
            st.write(st.session_state.AOI_str)
    try:
        thSelect2=st.select_slider('Select the threshold for inundation map.',options=[round(-3+i*0.1,1) for i in range(30)],value=thSelect)
        if thSelect2!=thSelect:
            thSelect=thSelect2
            changeValue=True
        else:
            changeValue=True #False
            
    except:
        pass
        
    try:
        thSelect2=st.select_slider('Select the Streamflow',options=[10000,40000],value=0)
            
    except:
        pass
    run_type = st.radio('National Water Model Forecast Configurations:', ('Short-Range (archive)','Short-Range', 'Medium-Range','Long-Range'))
    
    with st.form("FIER with NWM Analysis Simulation"):
       if run_type == 'Short-Range (archive)':
            in_run_type = 'archive' #archive
            
            AOI_str = st.session_state.AOI_str
            exp_fct_indata = {'time':xr.load_dataarray('AOI/'+AOI_str+'/Q/Q.nc').time.data}
            exp_fct_data = pd.DataFrame(exp_fct_indata)['time']
            exp_fct_time = pd.to_datetime(exp_fct_data)
            
            first_date = exp_fct_time[0]
            first_datestr = first_date.strftime('%Y-%m-%d')
            last_date = exp_fct_time[len(exp_fct_time)-1]
            last_datestr = last_date.strftime('%Y-%m-%d')

            date = st.date_input(
                "Select the date with available NWM forecast ("+first_datestr+" to "+last_datestr+" UTC):",
                value = first_date,
                min_value = first_date,
                max_value = last_date,
            )
            

            submitted = st.form_submit_button("Submit")
            
            if submitted or changeValue:

                #streamlit_proc(date, AOI_str, in_run_type)

                AOI_str = st.session_state.AOI_str
                bounds = run_fier(AOI_str, str(date), in_run_type,thSelect)
                st.write(AOI_str)

                if region=='Mississippi River':
                    location = [36.62, -89.15] # NEED FIX!!!!!!!!!!!
                elif region=='Red River':
                    location = [48.44, -97.17]

                m = folium.Map(
                        zoom_start = 8,
                        location = location,
                        control_scale=True,
                )

                folium.raster_layers.ImageOverlay(
                    image= 'Output/water_fraction.png',
                    # image = sar_image,
                    bounds = bounds,
                    opacity = 0.5,
                    name = 'Water Fraction Map',
                    show = True,
                ).add_to(m)
                m.add_child(legendDraw())

                plugins.Fullscreen(position='topright').add_to(m)
                folium.TileLayer('Stamen Terrain').add_to(m)
                m.add_child(folium.LatLngPopup())
                folium.LayerControl().add_to(m)


       if run_type == 'Short-Range':
            
            in_run_type = 'short_range'
            exp_fct = requests.get('https://nwmdata.nohrsc.noaa.gov/latest/forecasts/'+in_run_type+'/streamflow?&station_id=7469342').json()
            exp_fct_indata = exp_fct[0]["data"]
            
            exp_fct_data = pd.DataFrame(exp_fct_indata)["forecast-time"]
            exp_fct_time = pd.to_datetime(exp_fct_data)
            
            
            first_date = exp_fct_time[0]
            first_datestr = first_date.strftime('%Y-%m-%d')
            last_date = exp_fct_time[len(exp_fct_time)-1]
            last_datestr = last_date.strftime('%Y-%m-%d')

            date = st.date_input(
                "Select the date with available NWM forecast ("+first_datestr+" to "+last_datestr+" UTC):",
                value = first_date,
                min_value = first_date,
                max_value = last_date,
            )
            

            submitted = st.form_submit_button("Submit")
            print(submitted)
            if submitted or changeValue:

                #streamlit_proc(date, AOI_str, in_run_type)

                AOI_str = st.session_state.AOI_str
                bounds = run_fier(AOI_str, str(date), in_run_type,thSelect)
                st.write(AOI_str)

                if region=='Mississippi River':
                    location = [36.62, -89.15] # NEED FIX!!!!!!!!!!!
                elif region=='Red River':
                    location = [48.44, -97.17]

                m = folium.Map(
                        zoom_start = 8,
                        location = location,
                        control_scale=True,
                )

                folium.raster_layers.ImageOverlay(
                    image= 'Output/water_fraction.png',
                    # image = sar_image,
                    bounds = bounds,
                    opacity = 0.5,
                    name = 'Water Fraction Map',
                    show = True,
                ).add_to(m)
                m.add_child(legendDraw())

                plugins.Fullscreen(position='topright').add_to(m)
                folium.TileLayer('Stamen Terrain').add_to(m)
                m.add_child(folium.LatLngPopup())
                folium.LayerControl().add_to(m)
            

       if run_type == 'Medium-Range':
            in_run_type = 'medium_range_ensemble_mean'
            exp_fct = requests.get('https://nwmdata.nohrsc.noaa.gov/latest/forecasts/'+in_run_type+'/streamflow?&station_id=7469342').json()
            exp_fct_indata = exp_fct[0]["data"]
            exp_fct_data = pd.DataFrame(exp_fct_indata)["forecast-time"]
            exp_fct_time = pd.to_datetime(exp_fct_data)

            first_date = exp_fct_time[0]
            first_datestr = first_date.strftime('%Y-%m-%d')
            last_date = exp_fct_time[len(exp_fct_time)-1]
            last_datestr = last_date.strftime('%Y-%m-%d')

            date = st.date_input(
                "Select the date with available NWM forecast ("+first_datestr+" to "+last_datestr+" UTC):",
                value = first_date,
                min_value = first_date,
                max_value = last_date,
            )


            submitted = st.form_submit_button("Submit")
            if submitted or changeValue:

                #streamlit_proc(date, AOI_str, in_run_type)

                AOI_str = st.session_state.AOI_str
                bounds = run_fier(AOI_str, str(date), in_run_type,thSelect)
                st.write(AOI_str)

                if region=='Mississippi River':
                    location = [36.62, -89.15] # NEED FIX!!!!!!!!!!!
                elif region=='Red River':
                    location = [48.44, -97.17]

                m = folium.Map(
                        zoom_start = 8,
                        location = location,
                        control_scale=True,
                )

                folium.raster_layers.ImageOverlay(
                    image= 'Output/water_fraction.png',
                    # image = sar_image,
                    bounds = bounds,
                    opacity = 0.5,
                    name = 'Water Fraction Map',
                    show = True,
                ).add_to(m)

                m.add_child(legendDraw())

                plugins.Fullscreen(position='topright').add_to(m)
                folium.TileLayer('Stamen Terrain').add_to(m)
                m.add_child(folium.LatLngPopup())
                folium.LayerControl().add_to(m)
            
            
       if run_type == 'Long-Range':
            in_run_type = 'long_range_ensemble_mean'
            exp_fct = requests.get('https://nwmdata.nohrsc.noaa.gov/latest/forecasts/'+in_run_type+'/streamflow?&station_id=7469342').json()
            exp_fct_indata = exp_fct[0]["data"]
            exp_fct_data = pd.DataFrame(exp_fct_indata)["forecast-time"]
            exp_fct_time = pd.to_datetime(exp_fct_data)

            first_date = exp_fct_time[0]
            first_datestr = first_date.strftime('%Y-%m-%d')
            last_date = exp_fct_time[len(exp_fct_time)-1]
            last_datestr = last_date.strftime('%Y-%m-%d')

            date = st.date_input(
                "Select the date with available NWM forecast ("+first_datestr+" to "+last_datestr+" UTC):",
                value = first_date,
                min_value = first_date,
                max_value = last_date,
            )


            submitted = st.form_submit_button("Submit")
            if submitted or changeValue:

                #streamlit_proc(date, AOI_str, in_run_type)

                AOI_str = st.session_state.AOI_str
                bounds = run_fier(AOI_str, str(date), in_run_type,thSelect)
                st.write(AOI_str)

                if region=='Mississippi River':
                    location = [36.62, -89.15] # NEED FIX!!!!!!!!!!!
                elif region=='Red River':
                    location = [48.44, -97.17]

                m = folium.Map(
                        zoom_start = 8,
                        location = location,
                        control_scale=True,
                )

                folium.raster_layers.ImageOverlay(
                    image= 'Output/water_fraction.png',
                    # image = sar_image,
                    bounds = bounds,
                    opacity = 0.5,
                    name = 'Water Fraction Map',
                    show = True,
                ).add_to(m)
                
                m.add_child(legendDraw())

                plugins.Fullscreen(position='topright').add_to(m)
                folium.TileLayer('Stamen Terrain').add_to(m)
                m.add_child(folium.LatLngPopup())
                folium.LayerControl().add_to(m)
                    

    try:
        with open('Output/output.nc', 'rb') as f:
            st.download_button('Download Latest Run Output',
            f,
            file_name='water_fraction_%s_%s.nc'%(AOI_str, date),
            mime= "application/netcdf")
    except:
        pass
            
         


with row1_col1:
    folium_static(m, height = 600, width = 900)
    st.write('Disclaimer: This is a test version of FIER using VIIRS-derived water fraction maps over selected regions in US.')
    url = "https://www.sciencedirect.com/science/article/pii/S0034425720301024?casa_token=kOYlVMMWkBUAAAAA:fiFM4l6BUzJ8xTCksYUe7X4CcojddbO8ybzOSMe36f2cFWEXDa_aFHaGeEFlN8SuPGnDy7Ir8w"
    st.write("Reference: [Chang, C. H., Lee, H., Kim, D., Hwang, E., Hossain, F., Chishtie, F., ... & Basnayake, S. (2020). Hindcast and forecast of daily inundation extents using satellite SAR and altimetry data with rotated empirical orthogonal function analysis: Case study in Tonle Sap Lake Floodplain. Remote Sensing of Environment, 241, 111732.](%s)" % url)
    url = "https://uofh-my.sharepoint.com/:b:/g/personal/cchang37_cougarnet_uh_edu/EZ70ySxmR3RDhJL5-uAHlAEBf0xI4c-BMsXQnUKT009kFA?e=tynflq"
    st.write("See here for the [Data and Procedure](%s)" % url)
    st.write("This app has been developed by Chi-Hung Chang  & Son Do at University of Houston with supports from NOAA JPSS program.")
    st.write("Kel Markert at the Brigham Young University is also acknowledged for the development of this App.")

    uh = Image.open("logo/uh_logo_2.PNG")
    byu = Image.open("logo/BYU_Logo.png")
    jpss = Image.open("logo/JPSS_Logo.png")
    st.image([uh, byu, jpss], width=150)
