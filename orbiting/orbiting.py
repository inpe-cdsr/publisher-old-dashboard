import datetime
import time
import os
import numpy
import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly
import plotly.graph_objs as go
from dash.dependencies import Input, Output, State
import pyorbital
from pyorbital.orbital import Orbital
#from pyorbital import planets
#from pyorbital.moon_phase import moon_phase
#moon = planets.Moon(time)
#moonphase = moon_phase(time)
# https://github.com/pytroll/pyorbital/issues/38
from pyorbital.astronomy import sun_ecliptic_longitude,sun_ra_dec
import requests
from geopy import distance
from geopy.distance import great_circle,geodesic # https://pypi.org/project/geopy/
import json
from app import app

import math
from math import sin, cos, sqrt, atan2, radians

# https://plotly.com/python/mapbox-layers/#using-layoutmapboxlayers-to-specify-a-base-map
# https://stackoverflow.com/questions/19412462/getting-distance-between-two-points-based-on-latitude-longitude
# https://dash.plotly.com/live-updates
# Legends - https://plotly.com/python/legend/
# https://www.celestrak.com/NORAD/elements/active.php
# https://dash.plotly.com/dash-core-components/interval
# https://plotly.com/python/hover-text-and-formatting/#adding-other-data-to-the-hover-with-customdata-and-a-hovertemplate
# https://geopy.readthedocs.io/en/latest/#module-geopy.geocoders
# 
# Orbital loading
satellites = { \
	'AMAZONIA 1':'https://celestrak.com/satcat/tle.php?INTDES=2021-015', \
	'CBERS 4':'https://celestrak.com/satcat/tle.php?INTDES=2014%2D079', \
	'CBERS 4A':'https://celestrak.com/satcat/tle.php?INTDES=2019-093', \
	'LANDSAT 8':'https://celestrak.com/satcat/tle.php?INTDES=2013-008', \
	'SENTINEL-2A':'https://celestrak.com/satcat/tle.php?INTDES=2015-028', \
	'SENTINEL-2B':'https://celestrak.com/satcat/tle.php?INTDES=2017-013', \
	'ICEYE-X1':'https://celestrak.com/satcat/tle.php?INTDES=2018-004', \
	'HARBINGER (ICEYE-X3)':'https://celestrak.com/satcat/tle.php?INTDES=2019-026' \
}

def getSatOrbital(satellite):
	today = datetime.datetime.now().strftime("%Y-%m-%d")
	tlefile = 'TLE/{}_{}.tle'.format(satellite,today)
	if not os.path.exists(tlefile):
		link = satellites[satellite]
		try:
			response = requests.get(link, stream=True)
		except requests.exceptions.ConnectionError:
			print('getTLE - Connection Error')
		if 'Content-Length' not in response.headers:
			print('getSatOrbital - Content-Length not found in {} {}'.format(link,response.text))
		size = int(response.headers['Content-Length'].strip())
		print('getSatOrbital - file {} size {} Bytes'.format(tlefile,size))
		down = open(tlefile, 'wb')
		for buf in response.iter_content(1024):
			if buf:
				down.write(buf)
		down.close()
	print('getSatOrbital - file {}'.format(tlefile,))
	return Orbital(satellite,tlefile)

satlegend = { \
			'AMAZONIA 1':{'symbol':'star','color':'rgb(255, 0, 0)','size':12}, \
			'CBERS 4':{'symbol':'square','color':'rgb(255, 0, 0)','size':12}, \
			'CBERS 4A':{'symbol':'square','color':'rgb(255, 0, 255)','size':12}, \
			'LANDSAT 8':{'symbol':'triangle-up','color':'rgb(0, 0, 0)','size':12}, \
			'SENTINEL-2A':{'symbol':'diamond','color':'rgb(0, 255, 0)','size':12}, \
			'SENTINEL-2B':{'symbol':'diamond','color':'rgb(0, 255, 255)','size':12}, \
			'ICEYE-X1':{'symbol':'diamond','color':'rgb(0, 255, 100)','size':12}, \
			'HARBINGER (ICEYE-X3)':{'symbol':'diamond','color':'rgb(0, 100, 100)','size':12}, \
			'TARGET':{'symbol':'cross','color':'rgb(0, 0, 255)','size':20}, \
			'SUN':{'symbol':'star','color':'rgb(255, 190, 0)','size':20} \
			}
satswath = { \
			'AMAZONIA 1': 800., \
			'CBERS 4': 120., \
			'CBERS 4A':96., \
			'LANDSAT 8':180., \
			'SENTINEL-2A':360, \
			'SENTINEL-2B':360, \
			'ICEYE-X1':200, \
			'HARBINGER (ICEYE-X3)':200 \
			}

satnames = ['AMAZONIA 1','CBERS 4A','CBERS 4','LANDSAT 8','SENTINEL-2A','SENTINEL-2B','ICEYE-X1','HARBINGER (ICEYE-X3)']
satorbs = {}
for satname in satnames:
	satorbs[satname] = getSatOrbital(satname)
	#print('satname {} satorb {}'.format(satname,satorbs[satname]))

skipmapname = 'orbiting/skipmap.json'
if os.path.exists(skipmapname):
	with open(skipmapname) as file:
		skipmap = json.loads(file.read())

def findDescendingNode(satname,timecur,latcur,deltaseg=3):
# Find the first descending node after current time
# Find where the satellite is, either in the ascending node or descending node.
# If the satellite is in the North Pole, it will be considered as descending node
# If the satellite is in the South Pole, it will be considered as ascending node
	lonant, latant, alt = satorbs[satname].get_lonlatalt(timecur - datetime.timedelta(seconds=deltaseg))
	lonpos, latpos, alt = satorbs[satname].get_lonlatalt(timecur + datetime.timedelta(seconds=deltaseg))
	deltalat = latpos - latcur
	if (latcur >= latant and latcur >= latpos): # North Pole
		lonnext, latnext, alt = satorbs[satname].get_lonlatalt(timecur)
		return timecur,latnext,lonnext
		node = 'descending'
	elif (latcur <= latant and latcur <= latpos): # South Pole
		node = 'ascending'
	elif deltalat > 0.: # if derivative is positive, Satellite is in the ascending node. Use skipmap['descending']
		node = 'descending'
	else: 				# if derivative is negative, Satellite is in the descending node. Use skipmap['ascending']
		node = 'ascending'
	latcurs = str(math.ceil(latcur))
	skip = skipmap[satname][node][latcurs]
	timenext = timecur + datetime.timedelta(seconds=skip)
	lonnext, latnext, alt = satorbs[satname].get_lonlatalt(timenext)
	#print('findDescendingNode - sat {} from {},{:.2f} node {} skip {} to {},{:.2f}'.format(satname,timecur,latcur,node,skip,timenext,latnext))
	return timenext,latnext,lonnext

def findTargetInCurrentNode(satname,timecur,lattarget,lontarget):
# Find the target in the descending node
	loncur, latcur, alt = satorbs[satname].get_lonlatalt(timecur)
	lattargets = str(math.ceil(lattarget))
	skip = skipmap[satname]['descending'][lattargets]
	timenext = timecur + datetime.timedelta(seconds=skip)
	lonnext, latnext, alt = satorbs[satname].get_lonlatalt(timenext)

# Refine the position
	if latnext > lattarget:
		while latnext > lattarget:
			timenext = timenext + datetime.timedelta(seconds=1)
			lonnext, latnext, alt = satorbs[satname].get_lonlatalt(timenext)
			#print('findTargetInCurrentNode - sat {} refine > timenext {} latnext {} lattarget {}'.format(satname,timenext,latnext,lattarget))
	elif latnext < lattarget:
		while latnext < lattarget:
			timenext = timenext - datetime.timedelta(seconds=1)
			lonnext, latnext, alt = satorbs[satname].get_lonlatalt(timenext)
			#print('findTargetInCurrentNode - sat {} refine < timenext {} latnext {} lattarget {}'.format(satname,timenext,latnext,lattarget))
	
	posnext = (latnext,lonnext)
	postarget = (lattarget,lontarget)
	disttotarget = distance.distance(postarget, posnext).km
	#print('findTargetInCurrentNode - sat {} from {},{:.2f} skip {} to {},{:.2f} distance {:.0f}'.format(satname,timecur,latcur,skip,timenext,latnext,disttotarget))

	return timenext,latnext,lonnext,disttotarget

# Map layout
ORBIT_MAP_layout = dict(
		colorbar = True,
		width = 850,
		height = 600,
		margin={"r":0,"t":20,"l":0,"b":0},
		autosize = False,
		legend_title_text='Satellites',
		showlegend = True,
		name = 'Satellites',
		geo = dict( 
			showland = True, 
			landcolor = "rgb(255, 255, 220)", 
			showlakes = True, 
			lakecolor = "rgb(100, 100, 255)",
			showocean = True,
	  		oceancolor = "rgb(220, 240, 255)",
			#projection = {"type": "orthographic"},
			showrivers = True,
			rivercolor = "rgb(60, 120, 216)",
			showcountries = True, 
			countrycolor = "rgb(150, 150, 150)", 
			countrywidth = 0.8, 
			subunitcolor = "rgb(217, 217, 217)", 
			subunitwidth = 0.5, 
			lonaxis = dict( 
				showgrid = True, 
				gridwidth = 0.5, 
				range= [ -180., 180. ], 
				dtick = 5 
			), 
			lataxis = dict ( 
				showgrid = True, 
				gridwidth = 0.5, 
				range= [ -90, 90. ], 
				dtick = 5 
			) 
		))

# Table layout
df = [
	dict(id='SATELLITE_CHECKLIST',parameter= 'Satellites', type='checklist',options=satnames,default=[0]),
	dict(id='MODE_RADIO',parameter= 'Operation Mode', type='radio',options=['Real Time','One Day','Predict'],default=0),
	dict(id='INTERVAL_INPUT',parameter= 'Refresh Rate', type='input',options=[],default='35'),
	dict(id='DATE_INPUT',parameter= 'Date', type='input',options=[],default=datetime.datetime.now().strftime("%Y-%m-%d")),
	dict(id='LAT_INPUT',parameter= 'Latitude', type='input',options=[],default=-25.),
	dict(id='LON_INPUT',parameter= 'Longitude', type='input',options=[],default=-55.),
	dict(id='MARGIN_INPUT',parameter= 'Margin (km)', type='input',options=[],default=48),

]
def renderTable(df):
# Header
	columns = [('Parameter',100),('Value',200)]
	thead = html.Thead(html.Tr([html.Th(col[0],style={"text-align":"center","border":"2px black solid","width":"{}px".format(col[1])}) for col in columns]))
	table_rows = list()
	for i in range(len(df)):
		row = []
		print(df[i])
		parameter = df[i]['parameter']
		td = html.Td(parameter,style={"text-align":"center","border":"1px black solid"})
		row.append(td)
		cp = ''

		if df[i]['type'] == 'radio':
			options = []
			for option in df[i]['options']:
				options.append({'label':option, 'value':option})
				
			default = df[i]['options'][df[i]['default']] if 'default' in df[i] and len(df[i]['options']) > 0 else None
			cp = html.Div(
			children=[
				dcc.RadioItems(
					id=df[i]['id'],
					options=options,
					value=default,
					style=dict(width='100%', display='inline-block',verticalAlign="middle")
				),
			],
			id=df[i]['id']+'_DIV'
			)
		elif df[i]['type'] == 'dropdown':
			options = []
			for option in df[i]['options']:
				options.append({'label':option, 'value':option})
				
			default = df[i]['options'][df[i]['default']] if 'default' in df[i] and len(df[i]['options']) > 0 else None
			cp = html.Div(
			children=[
				dcc.Dropdown(
					id=df[i]['id'],
					options=options,
					value=default,
					style=dict(width='100%', display='inline-block',verticalAlign="middle")
				),
			],
			id=df[i]['id']+'_DIV'
			)
		elif df[i]['type'] == 'input':
			default = df[i]['default'] if 'default' in df[i] else None
			cp = dcc.Input(
				id=df[i]['id'],
				type='text',
				value=default,
				placeholder="Enter {}".format(df[i]['parameter'])
			)
		elif df[i]['type'] == 'checklist':
			options = []
			for option in df[i]['options']:
				options.append({'label':option, 'value':option})
			default = []
			if 'default' in df[i]:
				for j in df[i]['default']:
					default.append(options[j]['value'])
			print('default',default)

			cp = dcc.Checklist(
				id=df[i]['id'],
				options=options,
				value=default,
			)
			
		td = html.Td(cp,style=dict(border="1px black solid"))
		row.append(td)
		table_rows.append(html.Tr(row,style={"height":"1px"}))
	tbody = html.Tbody(children=table_rows)
	table = html.Table(children=[thead, tbody], id='my-table', className='row', style={"border":"3px black solid"})
	return table

layout = html.Div(
		[
			html.Div(
				[
					html.H4('Orbiting',style={'display': 'flex', 'justify-content': 'left'}),
				],
				style={'width': '100%', 'display': 'flex', 'align-items': 'center', 'justify-content': 'left'}
			),
			html.Div(
				[
					renderTable(df),
					html.Button('Submit Mode', id='submit-val', n_clicks=0,style={'width': '40%', 'display': 'flex', 'align-items': 'center', 'justify-content': 'center'}),
					html.Div(id='orbiting-button-basic',children='Press button to change mode')
				],
  				className='five columns'
  			),
			html.Div(
				[
					html.Div(
						[
							html.Div(id='LOCALUTC_text'),
						],
						style={'width': '100%', 'display': 'flex', 'align-items': 'center', 'justify-content': 'left'}
					),
					html.Div(
						[
							dcc.Graph(id='ORBIT_MAP',
									figure={'layout' : ORBIT_MAP_layout}
							),
							dcc.Interval(
								id='REALTIME_interval',
								interval=5*1000, # in milliseconds
								n_intervals=0
							),
							html.Div(id='CURRENT_ZOOM', style={'display': 'none'}),
							html.Div(id='CURRENT_LON', style={'display': 'none'}),
							html.Div(id='CURRENT_LAT', style={'display': 'none'}),
						],
						style={'width': '100%', 'display': 'flex', 'align-items': 'center', 'justify-content': 'center'}
					),
					html.Div([
						html.Pre(id='relayout-data', style={'border': 'thin lightgrey solid','overflowX': 'scroll'}),
					])
				],
				className='five columns'
			)
		])

@app.callback(
	[Output('relayout-data', 'children'),
	Output('CURRENT_ZOOM', 'children'),
	Output('CURRENT_LON', 'children'),
	Output('CURRENT_LAT', 'children')
	],
	[Input('ORBIT_MAP', 'relayoutData')])
def display_relayout_data(relayoutData):
	if relayoutData is not None:
		if "mapbox.zoom" in relayoutData:
			zoom = relayoutData["mapbox.zoom"]
		else:
			zoom = 0.5
		if "mapbox.center" in relayoutData:
			lon = relayoutData["mapbox.center"]["lon"]
			lat = relayoutData["mapbox.center"]["lat"]
		else:
			lon = 0.
			lat = 0.
	else:
		zoom = 0.
		lon = 0.
		lat = 0.
	print('display_relayout_data - relayoutData - {} zoom {}'.format(relayoutData,zoom))
	return json.dumps(relayoutData, indent=2),zoom,lon,lat

@app.callback(Output('REALTIME_interval', 'interval'),
		[Input('INTERVAL_INPUT', 'value')])
def update_interval(interval):
	if interval == '': interval = '5'
	interval = int(interval)*1000
	print('update_interval - interval',interval)
	return interval

@app.callback(
		[
			Output('orbiting-button-basic', 'children'),
			Output('REALTIME_interval', 'disabled')
		],
		[Input('submit-val', 'n_clicks')],
		[
			State('MODE_RADIO', 'value'),
		]
	)
def submit(n_clicks, mode):
	interval = False
	if mode == 'Real Time':
		interval = False
	else:
		interval = True
	return [mode,interval]

@app.callback(Output('LOCALUTC_text', 'children'),
			  [
			  Input('REALTIME_interval', 'n_intervals'),
			  ],
			  )
def update_times(n):
	locnow = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
	utcnow = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
	style = {'padding': '5px', 'fontSize': '16px'}
	return [
		html.Span('Local Time: {}'.format(locnow), style=style),
		html.Span('UTC: {}'.format(utcnow), style=style)
	]

# Multiple components can update everytime interval gets fired.
@app.callback(Output('ORBIT_MAP', 'figure'),
			[
			Input('REALTIME_interval', 'n_intervals'),
			Input('submit-val', 'n_clicks')],
			[
			State('SATELLITE_CHECKLIST', 'value'),
			State('MODE_RADIO', 'value'),
			State('DATE_INPUT', 'value'),
			State('LAT_INPUT', 'value'),
			State('LON_INPUT', 'value'),
			State('MARGIN_INPUT', 'value'),
			State('CURRENT_ZOOM', 'children'),
			State('CURRENT_LON', 'children'),
			State('CURRENT_LAT', 'children'),
			]
	)
	
def update_ORBIT_MAP(n, n_clicks, satnames, mode, date, lat, lon, margin,zoom,curlon,curlat):
	prop_id = dash.callback_context.triggered[0]['prop_id'].split('.')[0]
	lat = float(lat)
	lon = float(lon)
	margin = float(margin)
	print('update_ORBIT_MAP sat - {} prop_id {} mode {} date {} lon {} lat {} zoom {}'.format(satnames,prop_id,mode,date,lon,lat,zoom))
	if mode == 'Real Time':
		return generateRealTime(satnames,zoom,curlon,curlat)
	elif mode == 'One Day':
		data_graph_list = generatePeriod(satnames,date)
	elif mode == 'Predict':
		return generatePredict(satnames,date,lat,lon,margin,zoom,curlon,curlat)
	else:
		data_graph_list = None
		
	print('update_ORBIT_MAP - returning sat - {} prop_id {} mode {} date {} lon {} lat {} zoom {}'.format(satnames,prop_id,mode,date,lon,lat,zoom))
	return {'data':data_graph_list,'layout':ORBIT_MAP_layout}

def generatePredict(satnames,date,lattarget,lontarget,margin,zoom,curlon,curlat):
	data_graph = {}
	for satname in satnames:
		data_graph[satname] = {
		'time': [],
		'lat': [],
		'lon': [],
		'distance': [],
		}
	start_time = datetime.datetime.strptime(date+' 00:00:00','%Y-%m-%d %H:%M:%S')
	#start_time = datetime.datetime.utcnow()

	target = (lattarget,lontarget)
	deltaseg=12
# For each satellite
	for satname in satnames:
		distcur = 9999999.
		distmin = 9999999.
		timemin = None
		latmin = None
		lonmin = None
		timecur = start_time
		loncur, latcur, alt = satorbs[satname].get_lonlatalt(start_time)
		count = 0
		start_loop = time.time()
		while distcur > margin and count < 800:
			count += 1
# Find the first descending node
			timecur,latcur,loncur = findDescendingNode(satname,timecur,latcur,deltaseg)
			timecur,latcur,loncur,distcur = findTargetInCurrentNode(satname,timecur,lattarget,lontarget)
# https://www.geeksforgeeks.org/find-angles-given-triangle/
# beta = acos( ( a^2 + b^2 - c^2 ) / (2ab) )
			if distcur < distmin:
				distmin = distcur
				latmin = latcur
				lonmin = loncur
				timemin = timecur
			poscur = (latcur,loncur)
			#print('generatePredict - satname {} timecur {} target {} poscur {} distcur {:.1f}'.format(satname,timecur,target,poscur,distcur))
		if count < 800:
			data_graph[satname]['lon'].append(loncur)
			data_graph[satname]['lat'].append(latcur)
			data_graph[satname]['time'].append(timecur)
			data_graph[satname]['distance'].append(distcur)
		else:
			data_graph[satname]['lon'].append(lonmin)
			data_graph[satname]['lat'].append(latmin)
			data_graph[satname]['time'].append(timemin)
			data_graph[satname]['distance'].append(distmin)
		elapsed_time = time.time() - start_loop
		ela = str(datetime.timedelta(seconds=elapsed_time))
		print('generatePredict final - satname {} count {} timecur {} elapsed {} distmin {}'.format(satname,count,timecur,ela,distmin))

	data_graph_list = []

# Plot the target
	goTarget = go.Scattermapbox(
			lat=[lattarget],
			lon=[lontarget],
			name='Target',
			mode="markers",
			marker=go.scattermapbox.Marker(
				#symbol=satlegend['TARGET']['symbol'],
				size=satlegend['TARGET']['size'],
				color=satlegend['TARGET']['color']
			),
			text=['Target'],
		)
	data_graph_list.append(goTarget)

# Plot the predicted the position and time of each satellite
	hovertemplate= '<b>%{text}</b> \
					<br>Time:%{customdata[0]} \
					<br>Lat:%{customdata[1]:.2f} \
					<br>Lon:%{customdata[2]:.2f} \
					<br>Distance:%{customdata[3]:.0f}'

	for satname in satnames:
		hoverlist = []
		hoveritems = [data_graph[satname]['time'],data_graph[satname]['lat'],data_graph[satname]['lon'],data_graph[satname]['distance']]
		hoverlist.append(hoveritems)
		goSat = go.Scattermapbox(
				lat=data_graph[satname]['lat'],
				lon=data_graph[satname]['lon'],
				customdata=hoverlist,
				hovertemplate = hovertemplate,
				name=satname,
				mode="markers",
				marker=go.scattermapbox.Marker(
					#symbol=satlegend[satname]['symbol'],
					size=satlegend[satname]['size'],
					color=satlegend[satname]['color']
				),
				text=[satname],
			)
		data_graph_list.append(goSat)

	fig = go.Figure(data_graph_list)
	print('zoom1 - {}'.format(zoom))
	if zoom is None: zoom=4
	print('zoom2 - {}'.format(zoom))
	fig.update_layout(
		hovermode='closest',
		mapbox=dict(
			#accesstoken=mapbox_access_token,
			style="outdoors",
			bearing=0,
			center=go.layout.mapbox.Center(
				lat=lattarget,
				lon=lontarget
			),
			pitch=0,
			zoom=zoom
		)
	)
	"""
	if background == 'USGS':
		fig.update_layout(
			mapbox_style="white-bg",
			mapbox_layers=[
				{
					"below": 'traces',
					"sourcetype": "raster",
					"source": [
						"https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer/tile/{z}/{y}/{x}"
					]
				}
			  ]
		)
	else:
	"""
	fig.update_layout(mapbox_style="open-street-map")
	fig.update_layout(margin={"r":20,"t":20,"l":0,"b":0})
	return fig
	
######################################
def generatePredictold(satnames,date,lattarget,lontarget):
	data_graph = {}
	for satname in satnames:
		data_graph[satname] = {
		'time': [],
		'lat': [],
		'lon': [],
		'distance': [],
		}
	start_time = datetime.datetime.strptime(date+' 00:00:00','%Y-%m-%d %H:%M:%S')
	#start_time = datetime.datetime.utcnow()

	target = (lattarget,lontarget)
	deltaseg=12
# For each satellite
	for satname in satnames:
		distcur = 9999999.
		distmin = 9999999.
		timemin = None
		latmin = None
		lonmin = None
		timecur = start_time
		loncur, latcur, alt = satorbs[satname].get_lonlatalt(start_time)
		count = 0
		start_loop = time.time()
		while distcur > satswath[satname]/1.5 and count < 800:
			count += 1
# Find the first descending node
			timecur,latcur,loncur = findDescendingNode(satname,timecur,latcur,deltaseg)
			timecur,latcur,loncur,distcur = findTargetInCurrentNode(satname,timecur,lattarget,lontarget)
# https://www.geeksforgeeks.org/find-angles-given-triangle/
# beta = acos( ( a^2 + b^2 - c^2 ) / (2ab) )
			if distcur < distmin:
				distmin = distcur
				latmin = latcur
				lonmin = loncur
				timemin = timecur
			poscur = (latcur,loncur)
			print('generatePredict - satname {} timecur {} target {} poscur {} distcur {:.1f}'.format(satname,timecur,target,poscur,distcur))
		if count < 800:
			data_graph[satname]['lon'].append(loncur)
			data_graph[satname]['lat'].append(latcur)
			data_graph[satname]['time'].append(timecur)
			data_graph[satname]['distance'].append(distcur)
		else:
			data_graph[satname]['lon'].append(lonmin)
			data_graph[satname]['lat'].append(latmin)
			data_graph[satname]['time'].append(timemin)
			data_graph[satname]['distance'].append(distmin)
		elapsed_time = time.time() - start_loop
		ela = str(datetime.timedelta(seconds=elapsed_time))
		print('generatePredict final - satname {} count {} timecur {} elapsed {} distmin {}'.format(satname,count,timecur,ela,distmin))
	data_graph_list = []
	print('generatePredict - TARGET {}'.format(satlegend['TARGET']))
	data_graph_list.append(go.Scattergeo(
								lat=[lattarget],
								lon=[lontarget],
								name='Target',
								mode="markers",
								marker=dict(
									symbol=satlegend['TARGET']['symbol'],
									size=satlegend['TARGET']['size'],
									color=satlegend['TARGET']['color'])
								)
							)
	hovertemplate= '<b>%{text}</b> \
					<br>Time:%{customdata[0]} \
					<br>Lat:%{customdata[1]:.2f} \
					<br>Lon:%{customdata[2]:.2f} \
					<br>Distance:%{customdata[3]:.0f}'
	for satname in satnames:
		print('generatePredict - satname {} data_graph {}'.format(satname,data_graph[satname]))
		hoverlist = []
		hoveritems = [data_graph[satname]['time'],data_graph[satname]['lat'],data_graph[satname]['lon'],data_graph[satname]['distance']]
		hoverlist.append(hoveritems)
		data_graph_list.append(go.Scattergeo(
									lat=data_graph[satname]['lat'],
									lon=data_graph[satname]['lon'],
									customdata=hoverlist,
									hovertemplate = hovertemplate,
									text=[satname],
									name=satname,
									legendgroup=satname,
									mode="markers",
									marker=dict(
										symbol=satlegend[satname]['symbol'],
										size=satlegend[satname]['size'],
										color=satlegend[satname]['color'])
									)
								)

	return data_graph_list

###################################################	
def generatePeriod(satnames,date):
	data_graph = {}
	for satname in satnames:
		data_graph[satname] = {
		'time': [],
		'lat': [],
		'lon': [],
		'nowtime': 0,
		'nowlat': 0,
		'nowlon': 0
		}
# For one day evaluate satellite position
	start_time = datetime.datetime.strptime(date+' 00:00:00','%Y-%m-%d %H:%M:%S')
	for i in range(0,24*60-1,5):
		time = start_time + datetime.timedelta(seconds=i*60)
		for satname in satnames:
			lon, lat, alt = satorbs[satname].get_lonlatalt(time)
			data_graph[satname]['lon'].append(lon)
			data_graph[satname]['lat'].append(lat)
			data_graph[satname]['time'].append(time)

# Last position at midnight
	end_time = datetime.datetime.strptime(date+' 23:59:59','%Y-%m-%d %H:%M:%S')
	for satname in satnames:
		lon, lat, alt = satorbs[satname].get_lonlatalt(end_time)
		data_graph[satname]['lon'].append(lon)
		data_graph[satname]['lat'].append(lat)
		data_graph[satname]['time'].append(end_time)
		data_graph[satname]['nowtime'] = end_time
		data_graph[satname]['nowlon'] = lon
		data_graph[satname]['nowlat'] = lat

	hovertemplate= '<b>%{text}</b> \
					<br>Time:%{customdata[0]} \
					<br>Lat:%{customdata[1]:.2f} \
					<br>Lon:%{customdata[2]:.2f}'
	data_graph_list = []
	for satname in satnames:
		#print('update_ORBIT_MAP - satname {} lat {}'.format(satname,data_graph[satname]['nowlat']))
		hoverlist1 = []
		hoveritems = [data_graph[satname]['nowtime'],data_graph[satname]['nowlat'],data_graph[satname]['nowlon']]
		hoverlist1.append(hoveritems)
		data_graph_list.append(go.Scattergeo(
									lat=[data_graph[satname]['nowlat']],
									lon=[data_graph[satname]['nowlon']],
									customdata=hoverlist1,
									hovertemplate = hovertemplate,
									text=[satname],
									name=satname,
									legendgroup=satname,
									mode="markers",
									marker=dict(
										symbol=satlegend[satname]['symbol'],
										size=satlegend[satname]['size'],
										color=satlegend[satname]['color'])
									)
								)
		hoverlist2 = []
		text = []
		for i in range(len(data_graph[satname]['time'])):
			text.append(satname)
			hoveritems = [data_graph[satname]['time'][i],data_graph[satname]['lat'][i],data_graph[satname]['lon'][i]]
			hoverlist2.append(hoveritems)
		data_graph_list.append(go.Scattergeo(
									lat=data_graph[satname]['lat'],
									lon=data_graph[satname]['lon'],
									customdata=hoverlist2,
									hovertemplate = hovertemplate,
									text=text,
									name=satname,
									legendgroup=satname,
									showlegend=False,
									mode='lines',
									line=dict(
										color=satlegend[satname]['color'])
									)
								)
	return data_graph_list

#################################
def generateRealTime(satnames,zoom,curlon,curlat):
	data_graph = {}

	for satname in satnames:
		data_graph[satname] = {
		'time': [],
		'lat': [],
		'lon': [],
		'alt': [],
		'nowtime': 0,
		'nowlat': 0,
		'nowlon': 0,
		}
# Collect some data
	for i in range(10):
		time = datetime.datetime.utcnow() - datetime.timedelta(seconds=i*20)
		for satname in satnames:
			lon, lat, alt = satorbs[satname].get_lonlatalt(time)
			if i == 0:
				data_graph[satname]['nowtime'] = time.strftime("%Y-%m-%d %H:%M:%S")
				data_graph[satname]['nowlon'] = lon
				data_graph[satname]['nowlat'] = lat
			data_graph[satname]['lon'].append(lon)
			data_graph[satname]['lat'].append(lat)
			data_graph[satname]['alt'].append(alt)
			data_graph[satname]['time'].append(time.strftime("%Y-%m-%d %H:%M:%S"))

	hovertemplate= '<b>%{text}</b> \
					<br>Time:%{customdata[0]} \
					<br>Lat:%{customdata[1]:.2f} \
					<br>Lon:%{customdata[2]:.2f}'
	data_graph_list = []
	time = datetime.datetime.utcnow()
	for satname in satnames:
		print('update_ORBIT_MAP - satname {} lat {}'.format(satname,data_graph[satname]['nowlat']))
# Plot the current position of satellite
		hoverlist1 = []
		hoveritems = [data_graph[satname]['nowtime'],data_graph[satname]['nowlat'],data_graph[satname]['nowlon']]
		hoverlist1.append(hoveritems)
		goSat = go.Scattermapbox(
				lat=[data_graph[satname]['nowlat']],
				lon=[data_graph[satname]['nowlon']],
				customdata=hoverlist1,
				hovertemplate = hovertemplate,
				text=[satname],
				name=satname,
				legendgroup=satname,
				mode="markers",
				marker=go.scattermapbox.Marker(
					#symbol=satlegend[satname]['symbol'],
					size=satlegend[satname]['size'],
					color=satlegend[satname]['color']
				),
			)
		data_graph_list.append(goSat)

# Plot the trace of satellite
		hoverlist2 = []
		text = []
		for i in range(len(data_graph[satname]['time'])):
			text.append(satname)
			hoveritems = [data_graph[satname]['time'][i],data_graph[satname]['lat'][i],data_graph[satname]['lon'][i]]
			hoverlist2.append(hoveritems)
		data_graph_list.append(go.Scattermapbox(
				lat=data_graph[satname]['lat'],
				lon=data_graph[satname]['lon'],
				customdata=hoverlist2,
				hovertemplate = hovertemplate,
				text=text,
				name=satname,
				legendgroup=satname,
				showlegend=False,
				mode = "lines",
				#marker = {'size': 10}
				marker=go.scattermapbox.Marker(
				#	#symbol=satlegend[satname]['symbol'],
					size=int(satlegend[satname]['size']/3),
					color=satlegend[satname]['color']
				)
			))
		#data_graph_list.append(goSat)

# Plot the Sun

# subsolar longitude occurs at noon UTC
	hour = time.hour + time.minute / 60.0 + time.second / 3600.0
	sunlon = 15.0 * (12.0 - hour)
	if sunlon > 360.0: sunlon -= 360.0
	if sunlon < 0.0: sunlon += 360.0
	sunlon = round(sunlon,2)
# subsolar latitude is given by the solar declination
	sunra,sunlat = sun_ra_dec(time)
	sunlat = numpy.rad2deg(sunlat)
	sunlat = round(sunlat,2)
	print('sunlon {} at {}'.format(sunlon,time))
	print('sunra {} sunlat {}'.format(sunra,sunlat))

	goSun = go.Scattermapbox(
			lat=[sunlat],
			lon=[sunlon],
			name='Sun',
			mode="markers",
			marker=go.scattermapbox.Marker(
				#symbol=satlegend['TARGET']['symbol'],
				size=satlegend['SUN']['size'],
				color=satlegend['SUN']['color']
			),
			text=['Sun'],
		)
	data_graph_list.append(goSun)

# Build the final figure
	fig = go.Figure(data_graph_list)

	print('zoom1 - {}'.format(zoom))
	if zoom is None: zoom = 0.5
	print('zoom2 - {}'.format(zoom))
	fig.update_layout(
		hovermode='closest',
		mapbox=dict(
			#accesstoken=mapbox_access_token,
			style="outdoors",
			bearing=0,
			center=go.layout.mapbox.Center(
				lat=curlat,
				lon=curlon
			),
			pitch=0,
			zoom=zoom
		)
	)
	"""
	if background == 'USGS':
		fig.update_layout(
			mapbox_style="white-bg",
			mapbox_layers=[
				{
					"below": 'traces',
					"sourcetype": "raster",
					"source": [
						"https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer/tile/{z}/{y}/{x}"
					]
				}
			  ]
		)
	#elif background == 'OpenStreetMap':
	else:
	"""
	fig.update_layout(mapbox_style="open-street-map")
	fig.update_layout(margin={"r":20,"t":22,"l":0,"b":0})
	return fig
	#data_graph_list.append(goSun)
	#return data_graph_list
