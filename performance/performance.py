import os
import datetime
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import dash_table
import plotly
import plotly.graph_objs as go
import plotly.express as px
import plotly.figure_factory as ff
from datetime import datetime as dt
import numpy
import statistics
import math
import pandas as pd
from db import getEngine,db_execute,db_fetchone,db_fetchall

from app import app

start_time = None
end_time = None

sql = 'SELECT MIN(start_time) as start_time FROM job'
result = db_fetchone(sql,db='mster')
print('get_period - result',result)
if result is not None:
	start_time = result[0].strftime("%Y-%m-%d")
else:
	start_time = dt.now().strftime("%Y-%m-%d")
print('get_period - result',result,'start_time',start_time)

sql = 'SELECT MAX(end_time) as end_time FROM job'
result = db_fetchone(sql,db='mster')
print('get_period - result',result)
if result is not None:
	end_time = result[0].strftime("%Y-%m-%d")
else:
	end_time = dt.now().strftime("%Y-%m-%d")
print('get_period - result',result,'end_time',end_time)

hosts = [{'label':'All', 'value':'All'}]
sql = 'SELECT DISTINCT hostname as hostname FROM job'
results = db_fetchall(sql,db='mster')
print('get_host - results',results)
for result in results:
	if result[0] is None: continue
	host = {'label':result[0], 'value':result[0]}
	hosts.append(host)
print('get_host - hosts',hosts)

kinds = ['d2d','wde','d2g','g2q','g2t','t2r','t2gq']
colors = {'g2q': 'rgb(220, 0, 0)',
		  'g2t': 'rgb(0, 255, 0)',
		  't2r': 'rgb(255, 0, 255)',
		  'wde': 'rgb(255, 180, 0)',
		  'd2d': 'rgb(0, 100, 180)',
		  't2gq': 'rgb(0, 205, 205)',
		  'd2g': 'rgb(0, 50, 255)'}
		  
kindoptions = []
for kind in kinds:
	kindo = {'label':kind, 'value':kind}
	kindoptions.append(kindo)
columns = ['Function','Host','Satellite','Instrument','Level','Min','Avg','Max','Count']

layout = html.Div([
 	html.Div([
    	html.H4('Performance',style=dict(width='20%', display='inline-block',verticalAlign="middle")),
		html.Label('Period'),
		dcc.DatePickerRange(
			id='PERIOD_DATERANGE',
			display_format='YYYY-MM-DD',
			start_date=end_time,
			end_date=end_time,
			with_portal=True,
			start_date_placeholder_text='YYYY-MM-DD',
			minimum_nights=0,
			style=dict(width='35%', display='inline-block',verticalAlign="middle")
			)
	],
	style={'width': '100%', 'display': 'flex', 'align-items': 'center', 'justify-content': 'center'}
		),
 	html.Div([
		html.Label('Function'),
		dcc.Checklist(
			id='KIND_CHECKLIST',
			options=kindoptions,
			value=kinds,
			labelStyle=dict(display='inline-block'),
			style=dict(width='25%', verticalAlign="middle")
		),
		html.Label('Instrument'),
		dcc.Input(
			id='INSTRUMENT_INPUT',
			type='text',
			placeholder="Instrument",
			style=dict(width='15%', verticalAlign="middle")
			),
		html.Label('Passage Date'),
		dcc.Input(
			id='PASSAGE_INPUT',
			type='text',
			#value=datetime.datetime.now().strftime("%Y-%m-%d"),
			placeholder="YYYY-MM-DD",
			style=dict(width='15%', verticalAlign="middle")
			),
		html.Label('Host'),
		dcc.Dropdown(
			id='HOST_DROPDOWN',
			options=hosts,
			value='All',
			style=dict(width='60%', display='inline-block',verticalAlign="middle")
		),
		html.Label('Status'),
		dcc.Dropdown(
			id='STATUS_DROPDOWN',
			options=[dict(label='Executing',value='Executing'),dict(label='Running',value='Running'),dict(label='Waiting',value='Waiting')],
			value='Executing',
			style=dict(width='60%', display='inline-block',verticalAlign="middle")
		),
		html.Button('Submit', id='PERFORMACE_BUTTON', n_clicks=0,
			style=dict(width='10%', display='inline-block',verticalAlign="middle")
		),
	],
	style={'width': '100%', 'display': 'flex', 'align-items': 'center', 'justify-content': 'center'}
	),
		html.Div(
			[
				dash_table.DataTable(
					id='PERFORMANCE_datatable',
					style_header={
						'backgroundColor': 'rgb(230, 230, 230)',
						'textAlign': 'center',
						'fontWeight': 'bold',
						'width': '100%'
					},
					style_cell={'textAlign': 'right'},
					style_cell_conditional=[
					{
						'if': {'column_id': 'Function'},
						'textAlign': 'left'
					}
					],
					columns=[{"name": i, "id": i, "deletable": False, "selectable": True} for i in columns],
				)
			],
			style={'marginLeft': 0, 'marginRight': 0, 'marginTop': 0, 'marginBottom': 0,'width': '100%', 'display': 'flex', 'align-items': 'center', 'justify-content': 'center'}
		),
	dcc.Graph(id='PERFORMANCE_graph'),
])

@app.callback( [
				Output('PERFORMANCE_datatable', 'data'),
				Output('PERFORMANCE_graph', 'figure')
				],
				[
					Input('PERFORMACE_BUTTON', 'n_clicks')
				],
				[
					State('PERIOD_DATERANGE', 'start_date'),
					State('PERIOD_DATERANGE', 'end_date'),
					State('HOST_DROPDOWN', 'value'),
					State('KIND_CHECKLIST', 'value'),
					State('PASSAGE_INPUT', 'value'),
					State('INSTRUMENT_INPUT', 'value'),
					State('STATUS_DROPDOWN', 'value'),
				]
			  )

def update_tasks_graph(n_clicks,start_date,end_date,host,kinds,pdate,inst,status):
	print('update_tasks_graph',n_clicks,start_date,end_date,host,kinds,pdate,inst,status)
	df = []
	data_table_list = []

	if n_clicks == 0 or len(kinds) == 0:
		return data_table_list,{'data':None,'layout':None}
	kindin = 'kind IN ('
	for kind in kinds:
		kindin += "'{}',".format(kind)
	kindin = kindin[:-1]+')'
	datelike = '1'
	if pdate is not None and pdate != '':
		pdate1 = pdate.replace('-','_')
		pdate2 = pdate.replace('-','')
		datelike = "(info LIKE '%%{}%%' OR info LIKE '%%{}%%')".format(pdate1,pdate2)
	instlike = ''
	if inst is not None and inst != '':
		instlike = " AND info LIKE '%%{}%%'".format(inst)
	periodclause = ''
	if status == 'Executing':
		periodclause = " AND ((start_time >= '{0} 00:00:00'  AND start_time <= '{1} 23:59:59') OR (end_time >= '{0} 00:00:00'  AND end_time <= '{1} 23:59:59'))".format(start_date,end_date)
	elif status == 'Waiting':
		periodclause = " AND running = 1 AND start_time IS NULL AND end_time IS NULL "
	else:
		periodclause = " AND running = 1 AND start_time IS NOT NULL AND end_time IS NULL "

	sql = "SELECT * FROM job WHERE {2} {4} AND {3} AND ((start_time >= '{0} 00:00:00'  AND start_time <= '{1} 23:59:59') OR (end_time >= '{0} 00:00:00'  AND end_time <= '{1} 23:59:59'))".format(start_date,end_date,kindin,datelike,instlike)
	sql = "SELECT * FROM job WHERE {} {} AND {} {}".format(kindin,instlike,datelike,periodclause)
	if host != 'All':
		sql += " AND hostname = '{}'".format(host)
	#sql += ' Order BY hostname,info'
	sql += ' Order BY hostname,start_time'
	print('update_tasks_graph - ',sql)
	results = db_fetchall(sql,db='mster')
	if len(results) == 0:
		return data_table_list,{'data':None,'layout':None}
	count = 0
	idmap = {}
	perfmap = {}
	sats = []
	insts = []
	for result in results:
		count += 1
		id = ''
		if result['hostname'] is not None:
			host = result['hostname'].split('.')[0]
		else:
			host = 'ND'
		kind = result['kind']
		level = ''
# CBERS_4A_DTS2_RAW_2019_12_30.13_17_00_ETC2 d2d
		if kind == 'd2g' or kind == 'g2q'or kind == 'd2d':
# CBERS_4_AWFI_DRD_2020_07_04.02_40_45_CB11 d2g
			parts = result['info'].split('_')
			if parts[0].find('CBERS') == -1: continue
			sat = parts[0]+parts[1]
			inst = parts[2]
			calendardate = parts[4]+parts[5]+parts[6]+parts[7]+parts[8]
			id = '{}_{}_{}@{}'.format(sat,inst,calendardate,host)
		elif kind == 'g2t' or kind == 't2r' or kind == 't2gq':
# CBERS_4_AWFI_20200211_186_105.h5/L4
# CBERS_4_AWFI_20200211_160_099.png
			parts = result['info'].split('_')
			sat = parts[0]+parts[1]
			inst = parts[2]
			if kind == 'g2t': level = result['info'].split('/')[1]
			id = '{}{}_{}_{}/{}@{}'.format(parts[0],parts[1],parts[2],parts[3],level,host)
		elif kind == 'wde':
# CBERS_4A_PAN_CCD3_RAW_2019_12_30.13_17_00_ETC2
			parts = result['info'].split('_')
			sat = parts[0]+parts[1]
			inst = parts[2]+parts[3]
			id = result['info']+'@'+host
		if result['finished'] == 1 and result['exit_status'] != 0: id = 'ERROR-'+id
		if id not in idmap:
			idmap[id]=0
		idmap[id] += 1
		
		if status == 'Executing':
			if result['finished'] == 1 and result['exit_status'] == 0:
				start = numpy.datetime64(result['start_time'])
				end = numpy.datetime64(result['end_time'])
				elapsed = int((end-start).astype(numpy.float)/1000./1000./60.)
				if kind not in perfmap:
					perfmap[kind] = {}
				if host not in perfmap[kind]:
					perfmap[kind][host] = {}
				if sat not in perfmap[kind][host]:
					perfmap[kind][host][sat] = {}
				if inst not in perfmap[kind][host][sat]:
					perfmap[kind][host][sat][inst] = {}
				if level not in perfmap[kind][host][sat][inst]:
					perfmap[kind][host][sat][inst][level] = []
				perfmap[kind][host][sat][inst][level].append(elapsed)
			finish = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S") if result['end_time'] is None else result['end_time']
			task = dict(Task=id, Start=result['start_time'], Finish=finish, Resource=kind)
			df.append(task)
		elif status == 'Running':
			start = numpy.datetime64(result['start_time'])
			finish = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
			end = numpy.datetime64(finish)
			elapsed = int((end-start).astype(numpy.float)/1000./1000./60.)
			if kind not in perfmap:
				perfmap[kind] = {}
			if host not in perfmap[kind]:
				perfmap[kind][host] = {}
			if sat not in perfmap[kind][host]:
				perfmap[kind][host][sat] = {}
			if inst not in perfmap[kind][host][sat]:
				perfmap[kind][host][sat][inst] = {}
			if level not in perfmap[kind][host][sat][inst]:
				perfmap[kind][host][sat][inst][level] = []
			perfmap[kind][host][sat][inst][level].append(elapsed)
			task = dict(Task=id, Start=result['start_time'], Finish=finish, Resource=kind)
			df.append(task)
		elif status == 'Waiting':
			start = numpy.datetime64(result['creation_time'])
			finish = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
			end = numpy.datetime64(finish)
			elapsed = int((end-start).astype(numpy.float)/1000./1000./60.)
			if kind not in perfmap:
				perfmap[kind] = {}
			if host not in perfmap[kind]:
				perfmap[kind][host] = {}
			if sat not in perfmap[kind][host]:
				perfmap[kind][host][sat] = {}
			if inst not in perfmap[kind][host][sat]:
				perfmap[kind][host][sat][inst] = {}
			if level not in perfmap[kind][host][sat][inst]:
				perfmap[kind][host][sat][inst][level] = []
			perfmap[kind][host][sat][inst][level].append(elapsed)
			task = dict(Task=id, Start=start, Finish=finish, Resource=kind)
			df.append(task)

	print('update_tasks_graph - results - {} ids {}'.format(len(results),len(idmap)))
	height = 200+30*len(idmap)
	for kind in perfmap:
		for host in perfmap[kind]:
			for sat in perfmap[kind][host]:
				for inst in perfmap[kind][host][sat]:
					for level in perfmap[kind][host][sat][inst]:
						data_table = {}
						data_table['Function'] = kind
						data_table['Host'] = host
						data_table['Satellite'] = sat
						data_table['Instrument'] = inst
						data_table['Level'] = level
						data_table['Avg'] = int(statistics.mean(perfmap[kind][host][sat][inst][level]))
						data_table['Min'] = min(perfmap[kind][host][sat][inst][level])
						data_table['Max'] = max(perfmap[kind][host][sat][inst][level])
						data_table['Count'] = len(perfmap[kind][host][sat][inst][level])
						#print('update_tasks_graph - data_table {}'.format(data_table))
						data_table_list.append(data_table)
	
	if len(df) > 0:
		fig = ff.create_gantt(df, title='Tasks by time', colors=colors, index_col='Resource', show_colorbar=True, group_tasks=True,showgrid_x=True,height=height)
		return data_table_list,fig
	return data_table_list,{'data':None,'layout':None}

