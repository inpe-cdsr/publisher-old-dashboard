import datetime
import os
import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly
from dash.dependencies import Input, Output
import pyorbital
from pyorbital.orbital import Orbital
import requests
from app import app

satellites = { \
	'CBERS 4':'https://celestrak.com/satcat/tle.php?INTDES=2014%2D079', \
	'CBERS 4A':'https://celestrak.com/satcat/tle.php?INTDES=2019-093', \
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
			print('getTLE - Content-Length not found in {} {}'.format(link,response.text))
		size = int(response.headers['Content-Length'].strip())
		print('getTLE - file {} size {} Bytes'.format(tlefile,size))
		down = open(tlefile, 'wb')
		for buf in response.iter_content(1024):
			if buf:
				down.write(buf)
		down.close()
	return Orbital(satellite,tlefile)

satnames = ['CBERS 4','CBERS 4A']
satorbs = {}
for satname in satnames:
	satorbs[satname] = getSatOrbital(satname)
	print('satname {} satorb {}'.format(satname,satorbs[satname]))

satname = 'CBERS 4'
# https://dash.plotly.com/live-updates

layout = html.Div(
	html.Div([
		html.H4('{} Orbiting'.format(satname)),
		html.Div(id='live-update-text'),
		dcc.Graph(id='live-update-graph'),
		dcc.Interval(
			id='interval-component',
			interval=5*1000, # in milliseconds
			n_intervals=0
		)
	])
)

@app.callback(Output('live-update-text', 'children'),
			  [Input('interval-component', 'n_intervals')])
def update_metrics(n):
	lon, lat, alt = satorbs[satname].get_lonlatalt(datetime.datetime.now())
	style = {'padding': '5px', 'fontSize': '16px'}
	return [
		html.Span('Longitude: {0:.2f}'.format(lon), style=style),
		html.Span('Latitude: {0:.2f}'.format(lat), style=style),
		html.Span('Altitude: {0:0.2f}'.format(alt), style=style)
	]


# Multiple components can update everytime interval gets fired.
@app.callback(Output('live-update-graph', 'figure'),
			  [Input('interval-component', 'n_intervals')])
def update_graph_live(n):
	data = {
		'time': [],
		'Latitude': [],
		'Longitude': [],
		'Altitude': []
	}

# Collect some data
	for i in range(180):
		time = datetime.datetime.now() - datetime.timedelta(seconds=i*20)
		lon, lat, alt = satorbs[satname].get_lonlatalt(time)
		data['Longitude'].append(lon)
		data['Latitude'].append(lat)
		data['Altitude'].append(alt)
		data['time'].append(time)

	# Create the graph with subplots
	fig = plotly.subplots.make_subplots(rows=2, cols=1, vertical_spacing=0.2)
	fig['layout']['margin'] = {
		'l': 30, 'r': 10, 'b': 30, 't': 10
	}
	fig['layout']['legend'] = {'x': 0, 'y': 1, 'xanchor': 'left'}

	fig.append_trace({
		'x': data['time'],
		'y': data['Altitude'],
		'name': 'Altitude',
		'mode': 'lines+markers',
		'type': 'scatter'
	}, 1, 1)
	fig.append_trace({
		'x': data['Longitude'],
		'y': data['Latitude'],
		'text': data['time'],
		'name': 'Longitude vs Latitude',
		'mode': 'lines+markers',
		'type': 'scatter'
	}, 2, 1)

	return fig

