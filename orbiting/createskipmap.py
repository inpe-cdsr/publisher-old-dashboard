import datetime
import os
import pyorbital
from pyorbital.orbital import Orbital
import requests
from geopy import distance
from geopy.distance import great_circle,geodesic # https://pypi.org/project/geopy/
import json
import math
from math import sin, cos, sqrt, atan2, radians

# https://stackoverflow.com/questions/19412462/getting-distance-between-two-points-based-on-latitude-longitude

# https://dash.plotly.com/live-updates
# Legends - https://plotly.com/python/legend/

# Orbital loading
satellites = { \
	'AMAZONIA 1':'https://celestrak.com/satcat/tle.php?INTDES=2021-015', \
	'CBERS 4':'https://celestrak.com/satcat/tle.php?INTDES=2014%2D079', \
	'CBERS 4A':'https://celestrak.com/satcat/tle.php?INTDES=2019-093', \
	'LANDSAT 8':'https://celestrak.com/satcat/tle.php?INTDES=2013-008', \
	'SENTINEL-2A':'https://celestrak.com/satcat/tle.php?INTDES=2015-028', \
	'SENTINEL-2B':'https://celestrak.com/satcat/tle.php?INTDES=2017-013' \
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

satnames = ['AMAZONIA 1','CBERS 4A','CBERS 4','LANDSAT 8','SENTINEL-2A','SENTINEL-2B']

satorbs = {}
for satname in satnames:
	satorbs[satname] = getSatOrbital(satname)
	print('satname {} satorb {}'.format(satname,satorbs[satname]))

skipmapname = 'orbiting/skipmap.json'

# Find the target in the descending node
def findTarget(satorb,start_time,lat,lon,deltaseg=3):
	loncur, latcur, alt = satorb.get_lonlatalt(start_time)
	lonpos, latpos, alt = satorb.get_lonlatalt(start_time + datetime.timedelta(seconds=deltaseg))
	deltasegcur = deltaseg
	timecur = start_time
	print('findTarget - time {} ds {} lattarget {:.2f} latcur {:.2f} latpos {:.2f} loncur {:.2f}'.format(timecur,deltasegcur,lat,latcur,latpos,loncur))

# Try to find the Noth Pole (latcur is the higher than the others)
	while latpos > lat:
		deltalat = latpos - lat
# if the satellite is far from target, lets go fast
		if deltalat > 60.:
			deltasegcur = 25*60 # jump 20 minutes
# if the satellite is not so far lets slow down
		elif deltalat > 20.:
			deltasegcur = 5*60 # jump 5 minute
# if the satellite near target lets slow down
		elif deltalat > 1.:
			deltasegcur = 0.5*60 # jump 0.5 minute
		else:
			deltasegcur = deltaseg
		timecur += datetime.timedelta(seconds=deltasegcur)
		latcur = latpos
		loncur = lonpos
		lonpos, latpos, alt = satorb.get_lonlatalt(timecur)
		dl2 = latpos - latcur
		print('findTarget - {} ds {} dl1 {:.0f}  dl2 {:.0f} lt {:.2f} latcur {:.2f} latpos {:.2f} loncur {:.0f}'.format(timecur,deltasegcur,deltalat,dl2,lat,latcur,latpos,loncur))
	return timecur,latcur,loncu
	
# Find the first descending node
def findDescendingNode(satorb,start_time,deltaseg=3):
	lonant, latant, alt = satorb.get_lonlatalt(start_time - datetime.timedelta(seconds=deltaseg))
	loncur, latcur, alt = satorb.get_lonlatalt(start_time)
	lonpos, latpos, alt = satorb.get_lonlatalt(start_time + datetime.timedelta(seconds=deltaseg))
	deltasegcur = deltaseg
	timecur = start_time
	print('findDescendingNode - time {} ds {} latant {:.2f} latcur {:.2f} latpos {:.2f} loncur {:.0f}'.format(timecur,deltasegcur,latant,latcur,latpos,loncur))

# Try to find the Noth Pole (latcur is the higher than the others)
	while not (latcur >= latant and latcur >= latpos):
		deltalat = latpos - latcur
# if the satellite is already in a descending node, lets find the next one quickly
		if deltalat <= 0.:
			deltasegcur = 20*60 # jump 30 minutes
# if the satellite is already in a ascending node below 70 degrees, lets slow down
		elif latpos < 70.:
			deltasegcur = 5*60 # jump 10 minutes
# if the satellite is already in a ascending node below 80 degrees, lets slow down
		elif latpos < 80.:
			deltasegcur = 60 # jump 1 minute
		else:
			deltasegcur = deltaseg
		timecur += datetime.timedelta(seconds=deltasegcur)
		latant = latcur
		lonant = loncur
		latcur = latpos
		loncur = lonpos
		lonpos, latpos, alt = satorb.get_lonlatalt(timecur)
		#print('findDescendingNode - time {} ds {} latant {:.2f} latcur {:.2f} latpos {:.2f} loncur {:.0f}'.format(timecur,deltasegcur,latant,latcur,latpos,loncur))
	return timecur,latcur,loncur
skipmap = {}
#satnames = ['CBERS 4A']

for satname in satnames:
	skipmap[satname] = {'descending':{},'ascending':{}}
	satorb = satorbs[satname]
	deltaseg = 3
	time_start = datetime.datetime.utcnow() - datetime.timedelta(seconds=0)
	timeini,latini,lonini = findDescendingNode(satorb,time_start,deltaseg)

	latant = latini
	lastj = 0
	for j in range(0,60*60,1):
		lastj = j
		timecur = timeini + datetime.timedelta(seconds=j)
		lon, latcur, alt = satorb.get_lonlatalt(timecur)
		#print('sat {} j {} time {} lat {}'.format(satname,j,timecur,latcur))
		if latcur > latant:
			print('sat {} + South Pole time {} lat {}'.format(satname,timecur,latcur))
			break
		latant = latcur
		latcurs = str(math.ceil(latcur))
		if latcurs in skipmap[satname]['descending']: continue
		skipmap[satname]['descending'][latcurs] = j
		southpole = False
		latant2 = latcur
		for i in range(1,100*60,12):
			timecur = timeini + datetime.timedelta(seconds=i+lastj)
			lon, latcur, alt = satorb.get_lonlatalt(timecur)
			#print('sat {} i {} time {} lat {}'.format(satname,i,timecur,latcur))
			if not southpole and latcur < latant2:
				latant2 = latcur
				continue
			southpole = True
			if latcur < latant2:
				#print('sat {} j {} i {} + North Pole time {} lat {}'.format(satname,j,i,timecur,latcur))
				break
			latant2 = latcur
			skipmap[satname]['ascending'][latcurs] = i
	print('sat {} skipmap {}'.format(satname,skipmap[satname]))

with open('orbiting/skipmap.json', 'w') as outfile:
	json.dump(skipmap,outfile,indent=2)

time_start = datetime.datetime.utcnow()
for satname in satnames:
	satorb = satorbs[satname]
	timeini,latini,lonini = findDescendingNode(satorb,time_start,deltaseg)
	latinis = str(math.ceil(latini))
	lattarget = 25.5
	lattargets = str(math.ceil(lattarget))
	skip = skipmap[satname]['descending'][lattargets]
	timecur = timeini + datetime.timedelta(seconds=skip)
	lon, latcur, alt = satorb.get_lonlatalt(timecur)
	print('sat {} time {} skip {} lattarget {} latcur {}'.format(satname,timecur,skipmap[satname]['descending'][lattargets],lattarget,latcur))
	skip = skipmap[satname]['ascending'][lattargets]
	timecur = timecur + datetime.timedelta(seconds=skip)
	lon, latcur, alt = satorb.get_lonlatalt(timecur)
	print('sat {} time {} skip {} North Pole {}'.format(satname,timecur,skipmap[satname]['ascending'][lattargets],latcur))
