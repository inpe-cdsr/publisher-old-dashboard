import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import plotly
import plotly.graph_objs as go
from db import getEngine,db_execute,db_fetchone,db_fetchall
from datetime import datetime as dt
import base64
import random
import numpy
import math

from app import app

# https://pythonprogramming.net/live-graphs-data-visualization-application-dash-python-tutorial/
# https://dash.plotly.com/dash-core-components/datepickersingle
# https://dash.plotly.com/interactive-graphing
# https://github.com/plotly/dash-sample-apps
# https://github.com/plotly/dash-recipes
# https://plotly.com/python/bubble-maps/
# https://plotly.com/python/scatter-plots-on-maps/
# https://dash.plotly.com/dash-daq
# Uso do pyorbital em dash - https://dash.plotly.com/live-updates
# https://dash.plotly.com/sharing-data-between-callbacks
# https://dash.plotly.com/basic-callbacks States
def encode_image(filename):
	with open(filename, "rb") as image_file:
		encoded_string = base64.b64encode(image_file.read()).decode()
#add the prefix that plotly will want when using the string as source
	encoded_image = "data:image/png;base64," + encoded_string
	return encoded_image

############ Positioning ##############
dataset_options = []
scene_options = []
#dataset_options.append({'label':'All', 'value': 'All'})
sql = 'SELECT DISTINCT(dataset) FROM scenepositioning'
result = db_fetchall(sql,db='operation')
if len(result) > 0:
	for dataset in result:
		dataset_options.append({'label': dataset[0], 'value': dataset[0]})
	sql = "SELECT DISTINCT(sceneid) FROM scenepositioning WHERE dataset='{}'".format(dataset_options[0]['label'])
	result = db_fetchall(sql,db='operation')
	for scene in result:
		scene_options.append({'label': scene[0], 'value': scene[0]})
else:
	dataset_options.append({'label':'All', 'value': 'All'})
	scene_options.append({'label':'All', 'value': 'All'})

scl = [0,"rgb(150,0,90)"],[0.125,"rgb(0, 0, 200)"],[0.25,"rgb(0, 25, 255)"],\
[0.375,"rgb(0, 152, 255)"],[0.5,"rgb(44, 255, 150)"],[0.625,"rgb(151, 255, 0)"],\
[0.75,"rgb(255, 234, 0)"],[0.875,"rgb(255, 111, 0)"],[1,"rgb(255, 0, 0)"]

scl =	[0,"rgb(255,0,0)"], \
		[0.25,"rgb(255, 127, 0)"], \
		[0.5,"rgb(255, 255, 0)"], \
		[0.75,"rgb(127, 255, 0)"], \
		[1,"rgb(0, 255, 0)"]
PASSAGE_MAP_layout = dict(
 		title = 'Scenes', 
		colorbar = True,
		width = 700,
		height = 600,
		autosize = True,
		#showlegend = True,
		name = 'Error',
		geo = dict( 
			showland = True, 
			landcolor = "rgb(255, 255, 220)", 
			showlakes = True, 
			lakecolor = "rgb(100, 100, 255)",
			showocean = True,
      		oceancolor = "rgb(111, 168, 220)",
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
				range= [ -100.0, 20.0 ], 
				dtick = 5 
			), 
			lataxis = dict ( 
				showgrid = True, 
				gridwidth = 0.5, 
				range= [ -70.0, 20.0 ], 
				dtick = 5 
			) 
		))
		
QUICKLOOK_GRAPH_layout = dict(title='Kernels',
				autosize=False,width=600,height=600,          
				xaxis={"visible": False},
				yaxis={"visible": False},
				annotations=[
            	{
                	"text": "No scene selected",
                	"xref": "paper",
                	"yref": "paper",
                	"showarrow": False,
                	"font": {"size": 28}
            	}]
            )
# Positioning Layout
layout = html.Div([
	html.Div([
    	html.H4('Positioning'),
		html.Label('- - - - -'),
		html.Label('Date'),
		dcc.DatePickerSingle(
			id='PASSAGE_DATEPICKER',
			placeholder='Enter a passage date...',
			display_format='YYYY-MM-DD',
#			max_date_allowed=dt.now().strftime("%Y-%m-%d"),
#			date='2020-01-10',
			style=dict(width='40%')
		),
		html.Div(id='CURRENT_DATE', style={'display': 'none'}),
		html.Label('Datasets'),
		dcc.Dropdown(
			id='DATASET_DROPDOWN',
			style=dict(width='65%', display='inline-block',verticalAlign="middle")
		),
		html.Label('Scene'),
		dcc.Dropdown(
			id='SCENE_DROPDOWN',
			style=dict(width='75%', display='inline-block',verticalAlign="middle")
		),
		],
			style={'width': '100%', 'display': 'flex', 'align-items': 'center', 'justify-content': 'center'}
		),

	html.Div([
		html.Div(
			dcc.Graph(id='PASSAGE_MAP',
				figure={
					'layout' : PASSAGE_MAP_layout
				}
			),
			style={'width': '50%', 'display': 'inline-block'}
		),
		html.Div(
			dcc.Graph(id='QUICKLOOK_GRAPH',
				figure = {
				  'layout': QUICKLOOK_GRAPH_layout                                       
				}
			),
			style={'width': '39%', 'display': 'inline-block'}
		)
	]),
	html.Div([
# https://dash.plotly.com/dash-core-components
		html.Label('Errors'),
		dcc.RadioItems(
			id='ERRORS_DROPDOWN',
			options=[
				{'label': 'Easting', 'value': 'err_x'},
				{'label': 'Northing', 'value': 'err_y'},
				{'label': 'Cross', 'value': 'err_cross'},
				{'label': 'Along', 'value': 'err_along'}
    		],
			value='err_cross',
			labelStyle={'display': 'inline-block'},
		),
		dcc.Graph(id='ERRORS_GRAPH',style={'width': '100%'}),
	],
	)
])

# VER DATASET_DROPDOWN como input e output
##################################
@app.callback([Output('DATASET_DROPDOWN', 'options'),
			Output('PASSAGE_MAP', 'figure'),
			Output('CURRENT_DATE', 'children')],
			[Input('PASSAGE_DATEPICKER', 'date'),
			Input('DATASET_DROPDOWN', 'value')])
def passage_picker(date,dataset):
	print('passage_picker - You have selected date {} dataset {}'.format(date,dataset))
# Get the datasets available for this date
	dataset_options = []
	sql = "SELECT DISTINCT(dataset) FROM scenepositioning WHERE centertime LIKE '{}%%'".format(date)
	result = db_fetchall(sql,db='operation')
	if len(result) == 0:
		return dataset_options, {'data':[go.Scattergeo()],'layout':PASSAGE_MAP_layout}, date

	for scene in result:
		dataset_options.append({'label': scene[0], 'value': scene[0]})
	print('passage_picker - You got datasets {}'.format(dataset_options))
# Get the scenes available for this date
	if dataset is not None:
		sql = "SELECT * FROM scenepositioning WHERE centertime LIKE '{}%%' AND dataset = '{}'".format(date,dataset)
	else:
		sql = "SELECT * FROM scenepositioning WHERE centertime LIKE '{}%%'".format(date)
	result = db_fetchall(sql,db='operation')
	data_graph = {}
	lon = []
	lat = []
	color = []
	text = []
	err_x_mean = []
	err_y_mean = []
	hoverfields = ['band','correlation','kernels','err_x_mean','err_y_mean']
	hoverlist = []
	hovertext = []
	herr_max = 0
	for scene in result:
		id = scene['sceneid']+scene['band']
		print('passage_picker - hoverid {}'.format(id))
		if id not in data_graph:
			data_graph[id] = id
			hoveritems = []
			for field in hoverfields:
				hoveritems.append(scene[field])
			err_tot = int(math.sqrt(scene['err_x_mean']*scene['err_x_mean']+scene['err_y_mean']*scene['err_y_mean']))
			hoveritems.append(err_tot)
			herr_max = max(herr_max,err_tot)
			hovertext.append(scene['sceneid'])
			hoverlist.append(hoveritems)
			lon.append(scene['longitude'])
			lat.append(scene['latitude'])
			err_x_mean.append(scene['err_x_mean'])
			err_y_mean.append(scene['err_y_mean'])
			stext = scene['sceneid']
			text.append(stext)
	print('hoverlist',hoverlist)
	aerr_x_mean = numpy.asarray(err_x_mean, dtype=numpy.int)
	aerr_y_mean = numpy.asarray(err_y_mean, dtype=numpy.int)
	aerr_total = numpy.sqrt(aerr_x_mean*aerr_x_mean+aerr_y_mean*aerr_y_mean).astype(numpy.int)
	err_max = int(numpy.max(aerr_total))
	dtick = herr_max/5.
	color = aerr_total/err_max
	customdata = numpy.stack((aerr_x_mean, aerr_y_mean, aerr_total)).T
	hovertemplate='<b>%{text}</b><br>err_easting:%{customdata[0]:d}<br>err_northing:%{customdata[1]:d}<br>err_total:%{customdata[2]:d}'
	hovertemplate= '<b>%{text}</b> \
					<br>Band:%{customdata[0]} \
					<br>Correlation:%{customdata[1]:.1f} \
					<br>Kernels:%{customdata[2]:d} \
					<br>err_easting:%{customdata[3]:.0f} \
					<br>err_northing:%{customdata[4]:.0f} \
					<br>err_total:%{customdata[5]:d}'
	data_graph_list = [go.Scattergeo(
									lon=lon,
									lat=lat,
									customdata=hoverlist,
									hovertemplate = hovertemplate,
									text=text,
									name = '',
									mode= 'markers',
									marker = dict(
										color = color,
										colorscale = scl,
										symbol = 'square',
										reversescale = True,
										opacity = 1.,
										size = 10,
										colorbar = dict(
											titleside = "right",
											outlinecolor = "rgba(68, 68, 68, 0)",
											ticks = "outside",
											showticksuffix = "last",
											dtick = 0.1
										)
									)
						)]
	return dataset_options, \
			{'data':data_graph_list,'layout':PASSAGE_MAP_layout}, \
			date

# https://dash.plotly.com/interactive-graphing
##################################
@app.callback(Output('QUICKLOOK_GRAPH', 'figure'),
				[Input('PASSAGE_MAP', 'clickData'),
				Input('SCENE_DROPDOWN', 'value'),
				Input('PASSAGE_DATEPICKER', 'date')])
def passage_map_click(clicked_scene,selected_scene,date):
	print('passage_map_click - You have selected clicked_scene {}  selected_scene {} date {}'.format(clicked_scene,selected_scene,date))
	prop_id = dash.callback_context.triggered[0]['prop_id'].split('.')[0]
	print('passage_map_click - triggered by {} {}'.format(prop_id,dash.callback_context.triggered))
	clearmap = True
	if prop_id == 'SCENE_DROPDOWN':
		sceneid = selected_scene
		if sceneid != 'All':
			clearmap = False
	elif prop_id == 'PASSAGE_MAP':
		sceneid = clicked_scene['points'][0]['text'].split('-')[0]
		sdate = date.replace('-','')
		if sceneid.find(sdate) != -1:
			clearmap = False
# If the date has changed, clear QUICKLOOK_GRAPH because clickData keeps coming (the latest click)
	if clearmap:
		return {
			'data':None,
			'layout':QUICKLOOK_GRAPH_layout
			}

	print('passage_map_click - You have selected {} -> {}'.format(clicked_scene,sceneid))
	sql = "SELECT * FROM scenepositioning WHERE sceneid = '{}'".format(sceneid)
	result = db_fetchall(sql,db='operation')
	thumbnail = None
	for k in result:
		ymax = k['ymax']
		ymin = k['ymin']
		xmax = k['xmax']
		xmin = k['xmin']
		thumbnail = k['thumbnail']
		break
	print('passage_map_click',xmin,xmax,ymin,ymax)
	sql = "SELECT * FROM kernelpositioning WHERE status is NULL AND sceneid = '{}'".format(sceneid)
	sql = "SELECT * FROM kernelpositioning WHERE  sceneid = '{}'".format(sceneid)
	result = db_fetchall(sql,db='operation')
	print('passage_map_click - You got {} kernels'.format(len(result)))
	data_graph = {}
	for k in result:
		key = '{}_{}_R{}_{}'.format(k['sceneid'],k['band'],k['resampling'],k['method'])
		key = '{}_R{}_{}'.format(k['band'],k['resampling'],k['method'])
		if key not in data_graph:
			data_graph[key] = {'x':[],'y':[],'ms':[],'text':[]}
		data_graph[key]['x'].append(k['kernel_x'])
		data_graph[key]['y'].append(k['kernel_y'])
		data_graph[key]['ms'].append(int(20*k['correlation']))
		stext = '{:.2f} e_x = {:.0f} e_y = {:.0f}'.format(k['correlation'],k['err_x'],k['err_y'])
		data_graph[key]['text'].append(stext)
	print('passage_map_click - You got thumbnail {} {} '.format(sql,thumbnail))
	images = None
	if thumbnail is None:
		images = [{                        
					 'sizing': 'stretch', 'xref': 'paper', 'yref': 'paper', 'x':0,'y':1, 'layer':'below',
					 'sizex':1,'sizey':1,'opacity':1
					}]
	else:
		images = [{'source': encode_image('{}'.format(thumbnail)),                          
					 'sizing': 'stretch', 'xref': 'paper', 'yref': 'paper', 'x':0,'y':1, 'layer':'below',
					 'sizex':1,'sizey':1,'opacity':1
					}]
	data_graph_list = [go.Scatter(x=data_graph[key]['x'],y=data_graph[key]['y'],text=data_graph[key]['text'],marker_size=data_graph[key]['ms'],name=key,hoverinfo='text',mode= 'markers') for key in data_graph]
	return {
			'data':data_graph_list,
			'layout':go.Layout(
				title='Kernels '+sceneid,
				yaxis=dict(title='Northing',range=[ymin,ymax]),
				xaxis=dict(title='Easting',range=[xmin,xmax]),
				autosize = False, width = 600, height = 600,
				images = images
			)
	}

##################################
@app.callback(Output('SCENE_DROPDOWN', 'options'),
			#[Input('PASSAGE_DATEPICKER', 'date'),
			[Input('CURRENT_DATE', 'children'),
            Input('DATASET_DROPDOWN', 'value')])
def dataset_dropdown(date,dataset):
	print('dataset_dropdown - You have selected  date {} dataset {}'.format(date,dataset))
	scene_options = []
	scene_options.append({'label':'All', 'value': 'All'})
	if dataset == 'All':
		sql = "SELECT * FROM scenepositioning"
	else:
		sql = "SELECT * FROM scenepositioning WHERE dataset = '{}' AND centertime LIKE '{}%%'".format(dataset,date)
	result = db_fetchall(sql,db='operation')
	for scene in result:
		sid = '{}-{}-{}'.format(scene['sceneid'],scene['resampling'],scene['method'])
		sid = scene['sceneid']
		scene_option = {'label': sid, 'value': sid}
		if scene_option not in scene_options:
			scene_options.append({'label': sid, 'value': sid})
	print('dataset_dropdown - You got scenes {}'.format(scene_options))
	return scene_options


"""
def passage_map_click(clicked_scene,selected_scene,date):
	print('passage_map_click - You have selected clicked_scene {}  selected_scene {} date {}'.format(clicked_scene,selected_scene,date))
	prop_id = dash.callback_context.triggered[0]['prop_id'].split('.')[0]
	print('passage_map_click - triggered by {} {}'.format(prop_id,dash.callback_context.triggered))
	clearmap = True
	if prop_id == 'SCENE_DROPDOWN':
		sceneid = selected_scene
		if sceneid != 'All':
			clearmap = False
	elif prop_id == 'PASSAGE_MAP':
		sceneid = clicked_scene['points'][0]['text'].split('-')[0]
		sdate = date.replace('-','')
		if sceneid.find(sdate) != -1:
			clearmap = False
# If the date has changed, clear QUICKLOOK_GRAPH because clickData keeps coming (the latest click)
	if clearmap:
		return {
			'data':None,
			'layout':QUICKLOOK_GRAPH_layout
			}

	print('passage_map_click - You have selected {} -> {}'.format(clicked_scene,sceneid))
"""





##################################
@app.callback(Output('ERRORS_GRAPH', 'figure'),
            [Input('SCENE_DROPDOWN', 'value'),
            Input('DATASET_DROPDOWN', 'value'),
            Input('ERRORS_DROPDOWN', 'value'),
			Input('PASSAGE_MAP', 'clickData')],
			[State('PASSAGE_DATEPICKER', 'date')],
            )
def show_errors_graph(selected_scene,dataset,error,clicked_scene,date):
	print('show_errors_graph - You have selected scene {} dataset {} error {} date {} clicked_scene {}'.format(selected_scene,dataset,error,date,clicked_scene))
# when loading dash
	prop_id = dash.callback_context.triggered[0]['prop_id'].split('.')[0]
	print('show_errors_graph - triggered by {} {}'.format(prop_id,dash.callback_context.triggered))
	clearmap = True
	if prop_id == 'SCENE_DROPDOWN':
		sceneid = selected_scene
		if sceneid != 'All':
			clearmap = False
	elif prop_id == 'PASSAGE_MAP':
		print('show_errors_graphxxxx - clicked_scene[points] - {}'.format(clicked_scene))
		sceneid = clicked_scene['points'][0]['text'].split('-')[0]
		sdate = date.replace('-','')
		if sceneid.find(sdate) != -1:
			clearmap = False
# If the date has changed, clear QUICKLOOK_GRAPH because clickData keeps coming (the latest click)
	if clearmap:
		return {'data':None,'layout':None}


	print('show_errors_graph - You have selected {} -> {}'.format(clicked_scene,sceneid))

	if sceneid is None:
		print('show_errors_graph - sceneid is None')
		return {'data':None,'layout':None}
		#return {'data':None,'layout':go.Layout(title='Errors',yaxis=dict(title='Error',range=[0.,100]),xaxis=dict(title='Column',range=[0,1000]),)}
	if sceneid == 'All':
		if dataset is not None:
			sql = "SELECT * FROM kernelpositioning WHERE status is NULL AND dataset = '{}' AND centertime LIKE '{}%%'".format(dataset,date)
		else:
			sql = "SELECT * FROM kernelpositioning WHERE status is NULL AND centertime LIKE '{}%%'".format(date)
	else:
		if dataset is not None:
#			sql = "SELECT * FROM kernelpositioning WHERE status is NULL AND sceneid = '{}' AND dataset = '{}'".format(sceneid,dataset)
			sql = "SELECT * FROM kernelpositioning WHERE sceneid = '{}' AND dataset = '{}'".format(sceneid,dataset)
		else:	
			sql = "SELECT * FROM kernelpositioning WHERE status is NULL AND sceneid = '{}'".format(sceneid)
	print('show_errors_graph - sql {}'.format(sql))
	result = db_fetchall(sql,db='operation')
	print('show_errors_graph - You got {} kernels'.format(len(result)))
	data_graph = {}
	maxy = -999999
	miny = 999999
	maxcol = 0
	print('miny',miny,'maxy',maxy)
	if error is None:
		error = 'err_cross'
	for k in result:
		key = '{}_{}_R{}_{}'.format(k['sceneid'],k['band'],k['resampling'],k['method'])
		if k['sceneid'].find('MUX') != -1:
			maxcol = max(maxcol,6000)
		elif k['sceneid'].find('WFI') != -1:
			maxcol = max(maxcol,12000)
		elif k['sceneid'].find('WPM') != -1:
			if k['band'] != 'pan':
				maxcol = max(maxcol,12000)
			else:
				maxcol = max(maxcol,48000)
		if key not in data_graph:
			data_graph[key] = {'x':[],'y':[],'ms':[]}
		data_graph[key]['x'].append(k['col'])
		data_graph[key]['y'].append(k[error])
		data_graph[key]['ms'].append(int(20*k['correlation']))
		maxy = max(maxy,k[error])
		miny = min(miny,k[error])
	print('miny',miny,'maxy',maxy)
	deltay = (maxy - miny) * 0.05
	maxy += deltay
	miny -= deltay
	print('miny',miny,'maxy',maxy)
	data_graph_list = [go.Scatter(x=data_graph[key]['x'],y=data_graph[key]['y'],marker_size=data_graph[key]['ms'],name=key,mode= 'markers') for key in data_graph]
	return {'data':data_graph_list,'layout':go.Layout(title='Errors',yaxis=dict(title=error,range=[miny,maxy]),xaxis=dict(title='Column',range=[0,maxcol]),)}
