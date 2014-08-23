import urllib, json, sys, pprint, re
from datetime import date
from dateutil.rrule import rrule, DAILY
from bs4 import BeautifulSoup as bs


def get_date_range(start_date, end_date):
	"""
	Generates a datetime string "YYYY-MM-DD" from start_date
	to end_date
	"""
	for dt in rrule(DAILY, dtstart=start_date, until=end_date):
		yield dt.strftime("%Y-%m-%d")

def print_set_list(setlist):
	"""
	This function will print the setlist, one song per line
	so as to see it parsed correctly.
	"""
	for sets in setlist:
		for song in sets:
			print song
		print ""

def clean_set(setlist):
	""" 
	This function takes a setlist from phish.net and cleans it up 
	by splitting it into its songs and keeping segue information.

	ex. 
	input: "Set 1: My Soul >  Bathtub Gin,  555,  Pebbles and Marbles[3]"
	return: ['My Soul >', 'Bathtub Gin', '555', 'Pebbles and Marbles']
	"""
	songs = []
	setlist = re.sub(r'\[[0-9]+\]','',setlist.get_text()).strip()
	setlist = setlist.split(r':',1)
	songs.append(setlist[0])
	set_songs = setlist[1].strip().split(r'  ')
	for song in set_songs:
		songs.append(re.sub(r',$','',song))

	return songs

	#for song in songlist:
	#	if ">" in song:
	#		segues = song.strip().split(">")
	#		for i in range(len(segues)-1):
	#			songs.append(re.sub(r'\[[0-9]+\]','',segues[i].lstrip() + ">"))
	#		songs.append(re.sub(r'\[[0-9]+\]','',segues[len(segues)-1].lstrip()))
	#	else:
	#		songs.append(re.sub(r'\[[0-9]+\]','',song.strip()))
	#return songs


with open('test_setlist_file.txt','r') as f:
	data = json.load(f)
	data = data[0]				

showdate = data['showdate']
venue = data['venue']
city = data['city']
state = data['state']
print "Show:", showdate + " - " + venue + " - " + city + ", " + state, "\n"

# first split the text into sets using <p> and class
sets = []
setlist = bs(data['setlistdata'])
for set in setlist.find_all('p', class_=re.compile("pnetset")):
	songs = clean_set(set)
	for song in songs:
		print song
	#print songs
	print ""

















