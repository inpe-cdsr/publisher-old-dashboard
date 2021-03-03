import dash_core_components as dcc
import dash_html_components as html
import dash_table
from dash.dependencies import Input, Output, State
import plotly
import plotly.graph_objs as go
from db import getEngine,db_execute,db_fetchone,db_fetchall
from datetime import datetime as dt
import requests
from app import app

# https://dash.plotly.com/datatable/reference
# Satellites
instrument_map = dict(
                AMAZONIA1 = ['WFI'],
		CBERS4A = ['MUX','WFI','WPM'],
		CBERS4 = ['MUX','AWFI','PAN5M','PAN10M'],
		CBERS2B = ['CCD','WFI','HRC'],
		LANDSAT1 = ['MSS'],
		LANDSAT2 = ['MSS'],
		LANDSAT3 = ['MSS'],
		LANDSAT5 = ['TM'],
		LANDSAT7 = ['ETM'],
		)
band_map = dict(
		MUX = ['nir','red','green','blue'],
		AWFI = ['nir','red','green','blue'],
		WFI = ['nir','red','green','blue'],
		WPM = ['nir','red','green','blue','pan'],
		PAN10M = ['nir','red','green'],
		PAN5M = ['pan'],
		CCD = ['nir'],
		MSS = ['nir'],
		TM = ['nir'],
		ETM = ['nir'],
		)
############ Operation ##############
# Operation Utilities
def get_start_date():
	sql = 'SELECT MIN(launch) as start_date FROM Activities'
	result = db_fetchone(sql,db='operation')
	print('get_start_date - result',result)
	if result is not None and result[0] is not None:
		start_date = result[0].strftime("%Y-%m-%d")
	else:
		start_date = dt.now().strftime("%Y-%m-%d")
	print('get_start_date - result',result,'start_date',start_date)
	return start_date
# Layouts
# Processing Parameters
df = [
	dict(id='SATELLITE_DROPDOWN',parameter= 'Satellite', type='dropdown',options=list(instrument_map.keys()),default=0),
	dict(id='INSTRUMENT_DROPDOWN',parameter= 'Instrument', type='dropdown',options=[]),
	dict(id='PATH_INPUT',parameter= 'Path', type='input',options=[]),
	dict(id='ROW_INPUT',parameter= 'Row', type='input',options=[]),
	dict(id='PERIOD_DATERANGE',parameter= 'Period', type='daterange',options=[],default=dt.now().strftime("%Y-%m-%d")),
	dict(id='LEVEL_DROPDOWN',parameter= 'Level', type='checklist',options=['2','2B','4']),
	dict(id='RADIOMETRIC_CHECKLIST',parameter= 'Radiometry', type='checklist',options=['DN','SR'],default=[0]),
	dict(id='PROCESSING_DROPDOWN',parameter= 'Action', type='dropdown',options=['Publish','Unzip'],default=0)

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
		if df[i]['type'] == 'dropdown':
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
		elif df[i]['type'] == 'daterange':
			default = df[i]['default'] if 'default' in df[i] else None
			cp = html.Div(
			children=[
				dcc.DatePickerRange(
					id=df[i]['id'],
					display_format='YYYY-MM-DD',
					end_date=default,
					with_portal=True,
					start_date_placeholder_text='YYYY-MM-DD',
					minimum_nights=0
				)
			],
			style={'margin-bottom': '1px','margin-left': '0px','margin-right': '0px', 'width': '100%','padding': '0'},
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

			cp = dcc.Checklist(
				id=df[i]['id'],
				options=options,
				value=default,
				labelStyle={'display': 'inline-block'} if len(df[i]['options'][0]) < 3 else None
			)
			
		td = html.Td(cp,style={"border": "1px black solid" , "margin-left": "0px"})
		row.append(td)
		table_rows.append(html.Tr(row,style={"height":"1px"}))
	tbody = html.Tbody(children=table_rows)
	table = html.Table(children=[thead, tbody], id='my-table', className='row', style={"border":"3px black solid"})
	return table

def renderDatePicker(sd):
	print('renderDatePicker now {}'.format(dt.now().strftime("%Y-%m-%d")))
	dp = dcc.DatePickerSingle( 
		id='TASKS_date', 
		placeholder='Enter a start date...', 
		display_format='YYYY-MM-DD', 
		min_date_allowed=sd, 
		#max_date_allowed=dt.now().strftime("%Y-%m-%d"), 
		initial_visible_month=sd, 
		date=str(sd))
	return dp

columns = ['Task','Dataset','LAUNCHED','STARTED','FINISHED','ERROR','Max','Avg','Min']
layout = html.Div(
		[
			html.Div(
				[
					html.H4('Operation',style={'display': 'flex', 'justify-content': 'left'}),
				],
				style={'width': '100%', 'display': 'flex', 'align-items': 'center', 'justify-content': 'left'}
			),
			html.Div(
				[
					renderTable(df),
					html.Button('Submit', id='submit-val', n_clicks=0),
					html.Div(id='container-button-basic',children='Press submit')
				],
  				className='five columns'
  			),
			html.Div(
				[
					html.Div(
						[
							html.Label('Start Date'),
							renderDatePicker(get_start_date())
						],
						style={'width': '100%', 'display': 'flex', 'align-items': 'center', 'justify-content': 'center'}
					),
					html.Div(
						[
							dcc.Graph(id='TASKS_bargraph', animate=True),
							dcc.Interval(id='TASKS_interval', interval=10*1000)
						],
						style={'width': '100%', 'display': 'flex', 'align-items': 'center', 'justify-content': 'center'}
					),
					html.Div(
						[
							html.Br(),
							html.Label('Operation Statistics',style={"font-weight": "bold"}),
						],
						style={'width': '100%', 'display': 'flex', 'align-items': 'center', 'justify-content': 'center'}
						),
					html.Div(
						[
							dash_table.DataTable(
								id='TASKS_datatable',
								style_header={
        							'backgroundColor': 'rgb(230, 230, 230)',
        							'textAlign': 'center',
        							'fontWeight': 'bold',
        							'width': '100%'
    							},
    							style_cell={'textAlign': 'right'},
								style_cell_conditional=[
								{
									'if': {'column_id': 'Task'},
									'textAlign': 'left'
								}
								],
								columns=[{"name": i, "id": i, "deletable": False, "selectable": False} for i in columns],
							)
						],
						style={'marginLeft': 0, 'marginRight': 0, 'marginTop': 0, 'marginBottom': 0,'width': '100%', 'display': 'flex', 'align-items': 'center', 'justify-content': 'center'}
					),
				],
				className='five columns'
			)
		])

# Operation Callbacks

####################################
@app.callback(Output('INSTRUMENT_DROPDOWN_DIV', 'children'),
			[Input('SATELLITE_DROPDOWN', 'value')])
def update_instrument(sat):
	instrument_options = [{'label': 'All', 'value': 'All'}]
	for inst in instrument_map[sat]:
		instrument_options.append({'label': inst, 'value': inst})
	cp = dcc.Dropdown(
		id='INSTRUMENT_DROPDOWN',
		options=instrument_options,
		value=instrument_options[0]['value'],
		style=dict(width='100%', display='inline-block',verticalAlign="middle")
	)
	return cp

###################################
@app.callback(Output('BAND_DROPDOWN_DIV', 'children'),
			[Input('INSTRUMENT_DROPDOWN', 'value')])
def update_band(inst):
	band_options = []
	if inst is None or inst == 'All':
		band_options.append({'label': 'nir', 'value': 'nir'})
	else:
		for band in band_map[inst]:
			band_options.append({'label': band, 'value': band})
	print('update_band - inst {} band_options {}'.format(inst,band_options))
	cp = dcc.Dropdown(
		id='BAND_DROPDOWN',
		options=band_options,
		value=band_options[0]['value'],
		style=dict(width='100%', display='inline-block',verticalAlign="middle")
	)
	return cp

#####################################
@app.callback(Output('container-button-basic', 'children'),
	[Input('submit-val', 'n_clicks')],
	[
	State('SATELLITE_DROPDOWN', 'value'),
	State('INSTRUMENT_DROPDOWN', 'value'),
	State('PATH_INPUT', 'value'),
	State('ROW_INPUT', 'value'),
	State('PERIOD_DATERANGE', 'start_date'),
	State('PERIOD_DATERANGE', 'end_date'),
	State('LEVEL_DROPDOWN', 'value'),
	State('RADIOMETRIC_CHECKLIST', 'value'),
	State('PROCESSING_DROPDOWN', 'value')
	])
def submit(n_clicks, sat, inst,path,row,start_date,end_date,level,rp,action):
	print('submit - sat {} inst {} clicked {} times'.format(sat,inst,n_clicks))
	if n_clicks == 0:
		return 'Just started'
	keyval = {}
	flags = ''
	query = 'http://inpe_cdsr_publisher_api:5000/'

	keyval['sat'] = sat

# Only register an specific instrument
	if inst is not None and inst != 'All':
		keyval['inst'] = inst

# Path and Row
	if path is not None and path != '':
		keyval['path'] = path
	if row is not None and row != '':
		keyval['row'] = row

# Period
	if start_date is not None:
		keyval['start_date'] = start_date
	if end_date is not None:
		keyval['end_date'] = end_date

# Only register an specific level, if None or both, dont register
	if level is not None and len(level) == 1:
		keyval['level'] = level[0]

# Only register an specific radiometric processing, if None or both, dont register
	if rp is not None and len(rp) == 1:
		keyval['rp'] = rp[0]

# action publish may have positioning as a flag
	if 'Publish' in action:
		query += 'publish?'
		if 'Positioning' in action:
			flags += '&positioning'
	elif 'Positioning' in action:
		query += 'positioning?'
	elif 'Registering' in action:
		query += 'registering?'
	elif 'Upload' in action:
		query += 'upload?'
	elif 'Unzip' in action:
		query += 'unzip?'
	else:
		return 'Please choose an action'

# Build the query
	for key,val in keyval.items():
		query += '{}={}&'.format(key,val)
	query = query[:-1]
	query += flags

	r = requests.get(query)

	print('query: {}\n r.text: {}'.format(query, r.text))
	return 'query: {}\n r.text: {}'.format(query, r.text)

#####################################
@app.callback([Output('TASKS_bargraph', 'figure'),
			Output('TASKS_datatable', 'data')],
			[Input('TASKS_date', 'date'),
			Input('TASKS_interval', 'n_intervals')])
def update_graph_scatter(start_date,input_data):
	#print('update_graph_scatter - start_date',start_date,'input_data',input_data)
	sql = "SELECT task,dataset,MAX(elapsed) as maxe,AVG(elapsed) as avg ,MIN(elapsed) as mine FROM Activities WHERE launch >= '{}' AND status='FINISHED' AND elapsed > 0 GROUP BY task,dataset".format(start_date)
	result = db_fetchall(sql,db='operation')
	#print(result)
# Fill the data graph
	sql = "SELECT task,status,count(*) as amount FROM Activities WHERE launch >= '{}' GROUP BY task,status ORDER BY task".format(start_date)
	result = db_fetchall(sql,db='operation')
	statuscolor = dict(
		ERROR = "rgb(255, 0, 0)",
		FINISHED = "rgb(0, 0, 255)",
		STARTED = "rgb(0, 255, 0)",
		LAUNCHED = "rgb(127, 127, 0)",
	)
	data_graph = {}
	maxy = 0

	if result is None:
		return None, None

	for i in result:
		task = i[0]
		status = i[1]
		amount = i[2]
		maxy = max(maxy,amount)
		if status not in data_graph:
			data_graph[status] = {'x':[task],'y':[amount],'type': 'bar', 'name': status}
		else:
			data_graph[status]['x'].append(task)
			data_graph[status]['y'].append(amount)
	data_graph_list = [go.Bar(x=data_graph[i]['x'],y=data_graph[i]['y'],name=data_graph[i]['name'],marker_color=statuscolor[i]) for i in data_graph]

# Fill the data table
	sql = "SELECT task,dataset,status,count(*) as amount FROM Activities WHERE launch >= '{}' GROUP BY task,dataset,status ORDER BY task,dataset".format(start_date)
	sql = "SELECT task,dataset,status,count(*) as amount,MAX(elapsed) as maxe,AVG(elapsed) as avg ,MIN(elapsed) as mine FROM Activities WHERE launch >= '{}' GROUP BY task,dataset,status ORDER BY dataset,task".format(start_date)

	#print('update_graph_scatter - sql {}'.format(sql))

	result = db_fetchall(sql,db='operation')

	#print('update_graph_scatter - result {}'.format(result))

	data_table_list = []
	for i in result:
		data_table = {}
		task = i[0]
		dataset = i[1]
		status = i[2]
		amount = i[3]
		maxe = i[4]
		avge = i[5]
		mine = i[6]
		data_table['Task'] = task
		data_table['Dataset'] = dataset
		data_table[status] = amount
		data_table['Max'] = maxe
		data_table['Avg'] = int(avge) if avge is not None else None
		data_table['Min'] = mine

		#print('update_graph_scatter - data_table {}'.format(data_table))

		data_table_list.append(data_table)

	return {'data': data_graph_list,'layout' : go.Layout(title='Number of Tasks per Status',yaxis=dict(range=[0,maxy]),)},data_table_list
