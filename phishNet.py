import urllib, json, sys, pprint, re, time
from datetime import date
from dateutil.rrule import rrule, DAILY
from bs4 import BeautifulSoup as bs
from pymongo import MongoClient

## These are constant values that the 
## API call will need every time
url = "https://api.phish.net/"
endpoint = "api.js"
format='json'
apiver='2.0'

## Get this from the file
apikey = ""

## this is the driver for the connection to the mongodb
client = MongoClient()
db = client.phish
pshows = db.phishshows

def clean_set(setlist):
	""" 
	This function takes a setlist from phish.net and cleans it up 
	by splitting it into its songs and keeping segue information.

	ex. 
	input: "Set 1: My Soul >  Bathtub Gin,  555,  Pebbles and Marbles[3]"
	return: ['My Soul >', 'Bathtub Gin', '555', 'Pebbles and Marbles']
	"""
	songslist = []
	setlist = setlist.get_text().split(r':',1)
	songslist.append(setlist[0])
	songs_string = setlist[1]
	for song in setlist[1].strip().split(r'  '):
		song = re.sub(r'->|>','',song).strip()
		song = re.sub(r'\[[0-9]+\]','',song).strip()
		songslist.append(re.sub(r',$','',song).strip())
	return songslist, songs_string

def get_show_ids(year):
	"""
	This function will query the phish.net api to get the show ids for 'year'
	and return a list of all the show ids for that year.
	"""
	method = 'pnet.shows.query'
	params = urllib.urlencode( {
		'api': apiver,
		'format': format,
		'method': method,
		'apikey': apikey,
		'year': year
	})

	try:
		f = urllib.urlopen(url + endpoint + "?%s" % params)
	except IOError:
		print "Error: Unable to connect. Invalid URL"
		sys.exit(1)

	response = f.getcode()
	if response == 200:
		data = f.read()
		showlist = json.loads(data)

		## check to make sure this year has shows
		## if is doesn't call returns a dict with the
		## reason key saying 'No shows found'
		if isinstance(showlist, dict):
			print showlist['reason'], "in year:", year
			return

		showids = []
		for show in showlist:
			showid = bs(show['showid']).get_text()
			showids.append(showid)

		with open('PhishShowIds/phish_showid_%s.txt' % year,'w') as f:
			for showid in showids:
				f.write(year + "," + showid + '\n')

	else:
		print 'Error - HTTP Response code:', response

def get_show(showid, verbose=False):
	"""
	This will get the phish show with showid=showid from
	the phish.net setlist database.
	"""
	print "Getting the setlist for showid:"	, showid

	method='pnet.shows.setlists.get'
	params = urllib.urlencode( {
		'api': apiver,
		'format': format,
		'method': method,
		'apikey': apikey,
		'showid': showid
	})

	try:
		f = urllib.urlopen(url + endpoint + "?%s" % params )
	except IOError:
		print "Error: Unable to connect. Invalid URL"
		sys.exit(1)

	response = f.getcode()
	if response == 200:
		data = f.read()
		show_data = json.loads(data)[0]


		showdate = bs(show_data['showdate'])
		venue = bs(show_data['venue'])
		city = bs(show_data['city'])
		state = bs(show_data['state'])
		if verbose:
			print "Show:", showdate.get_text()+ " - " +venue.get_text()+ " - " +city.get_text()+ ", " +state.get_text(), "\n"

		## first split the text into sets using <p> and class
		sets = dict()
		set_string = dict()
		setlist = bs(show_data['setlistdata'])
		for pset in setlist.find_all('p', class_=re.compile("pnetset")):
			songs, sstring = clean_set(pset)
			sets[songs[0]] = list(songs[1:])
			set_string[songs[0]] = sstring

		del show_data['setlistdata']

		show_data['setlist'] = sets
		show_data['songs'] = set_string

		add_show_to_db(show_data)

		if verbose:
			pprint.pprint(show_data)

	else:
		print 'Error - HTTP Response code: ', response

	## close the connection
	f.close()

def add_show_to_db(show_info):
	"""
	Add the show_info object to the database
	"""
	pshows.insert(show_info)

if __name__ == '__main__':

	for year in range(2009,2015):
		with open('PhishShowIds/phish_showid_%d.txt'%year,'r') as f:
			for line in f:
				showid = line.strip().split(',')[1]
				get_show(showid)
				time.sleep(3)

	#for year in range(1983):
	#print 'getting showids for', '1983'
	#get_show_ids(str(1983))
	#time.sleep(10)


