# -*- coding: utf-8 -*-

import dash
from dash.dependencies import Output, Input
import dash_core_components as dcc
import dash_html_components as html
from os import environ
from flask import Flask, redirect
from app import app
from operation import operation
from performance import performance
from orbiting import orbiting

import logging

logging.basicConfig(format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s', level=logging.INFO)

SERVER_HOST = environ.get('SERVER_HOST', '0.0.0.0')
SERVER_PORT = int(environ.get('SERVER_PORT', 8050))
DEBUG_MODE = bool(environ.get('DEBUG_MODE', 'True'))

# https://dash.plotly.com/urls - Multi-Page Apps and URL Support

app.layout = html.Div([
	dcc.Location(id='url', refresh=False),
	html.Div(id='page-content')
])

options = html.Div([
    html.H3('Dashboard Options'),
    html.Div(id='operation-display-value'),
    dcc.Link('Go to Operation', href='/publisher-dashboard/operation'),
    html.Div(id='performance-display-value'),
    dcc.Link('Go to Performance', href='/publisher-dashboard/performance'),
    html.Div(id='orbiting-display-value'),
    dcc.Link('Go to Orbiting', href='/publisher-dashboard/orbiting'),

])

@app.callback(Output('page-content', 'children'),
			  [Input('url', 'pathname')])
def display_page(pathname):
	if pathname == '/publisher-dashboard/operation':
		return operation.layout
	elif pathname == '/publisher-dashboard/performance':
		return performance.layout
	elif pathname == '/publisher-dashboard/orbiting':
		return orbiting.layout
	else:
		return options

if __name__ == '__main__':
	app.run_server(debug=DEBUG_MODE, host=SERVER_HOST, port=SERVER_PORT)
