import urllib, json, sys, pprint, re, time
import datetime
from dateutil.rrule import rrule, DAILY
from bs4 import BeautifulSoup as bs
from pymongo import MongoClient
import argparse

##------------------------------------##
## These are constant values that the ##
##   API call will need every time    ##
##------------------------------------##
url = "https://api.phish.net/"
endpoint = "api.js"
format='json'
apiver='2.0'

##-----------------------------------##
## Connection information to MongoDB ##
##-----------------------------------##
client = MongoClient()
db = client.phish
pshows = db.phishshows

##---------------------------------------------##
## Date for comparison to see if we should get ##
##   show information and add to database      ##
##---------------------------------------------##
todays_date = datetime.datetime.today().date()
this_year = todays_date.year

def get_show_ids(year, apikey, verbose=False):
    """
    This function will query the phish.net api to get the show ids for 'year'
      and return a list of all the show ids for that year and write them to a 
      a text file. 
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
        print(u"Error: Unable to connect. Invalid URL")
        sys.exit(1)

    response = f.getcode()
    if response == 200:
        data = f.read()
        showlist = json.loads(data)

        ##--------------------------------------------##
        ## Check to make sure this year has shows     ##
        ## if is doesn't call returns a dict with the ##
        ## reason key saying 'No shows found'         ##
        ##--------------------------------------------##
        showids = []
        if isinstance(showlist, dict):
            print(u" > {0} in year {1}".format(showlist["reason"], year))
            return showids

        for show in showlist:
            showid = bs(show['showid']).get_text()
            showids.append(showid)

        if verbose:
            print(u"   {0} shows found for {1}".format(len(showids), year))

        return showids

    else:
        print(u'Error - HTTP Response code: {0}'.format(response))

    f.close()

def get_show(showid, apikey, verbose=False):
    """
    This will get the phish show with showid=showid from
    the phish.net setlist database.
    """

    ##---------------------------------------------------##
    ## First check to see if show is already in database ##
    ##---------------------------------------------------##
    if pshows.find({"showid": showid}).count() != 0:
        print(u" > Showid: {0} - {1} already in database.".format(showid, pshows.find_one({"showid":showid})["showdate"]))
        return

    if verbose:
        print(u" > Getting the setlist for showid: {0}".format(showid))

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
        print(u"Error: Unable to connect. Invalid URL")
        sys.exit(1)

    response = f.getcode()
    if response == 200:
        data = f.read()
        show_data = json.loads(data)[0]

        showdate = bs(show_data["showdate"])
        venue    = bs(show_data["venue"]   )
        city     = bs(show_data["city"]    )
        state    = bs(show_data["state"]   )
        if verbose:
            print(u"   Show: {0} - {1} - {2}, {3}".format(showdate.get_text(), 
                                                          venue.get_text()   , 
                                                          city.get_text()    , 
                                                          state.get_text()))

        ## Only continue if show date happened before today
        shows_date  = datetime.datetime.strptime(show_data["showdate"],"%Y-%m-%d").date()
        if shows_date < todays_date:

            ## First split the text into sets using <p> and class
            songs_played = set()
            sets         = dict()
            sets_string  = dict()
            setdata = bs(show_data["setlistdata"])
            for pset in setdata.find_all('p', class_=re.compile("pnetset")):
                set_name, set_string, set_list = clean_set(pset)
                if verbose:
                    print(u"set_name: {0}".format(set_name))
                    print(u"set_string: {0}".format(set_string))
                    print(u"set_list: {0}".format(set_list))
                for song in set_list:
                    songs_played.add(song)
                sets[set_name] = set_list
                sets_string[set_name] = set_string
    
            del show_data["setlistdata"]
            del show_data["relativetime"]
    
            show_data["setlist_string"] = sets_string
            show_data["setlist"] = sets
            show_data["songs_played"] = list(songs_played)
    
            if verbose:
                pprint.pprint(show_data)

            print(u" > Adding show {0} - {1} - {2}, {3} to database.".format(show_data["showdate"],
                                                                             show_data["venue"]   ,
                                                                             show_data["city"]    ,
                                                                             show_data["state"]))    
            pshows.insert(show_data)
        else:
            print(u" > Show on {0} hasn't happened yet.".format(shows_date))
    
    else:
        print(u'Error - HTTP Response code: {0}'.format(response))
        
    ## close the connection
    f.close()

def clean_set(pn_setlist):
    """ 
    This function takes a setlist from phish.net and cleans it up 
    by splitting it into its songs and keeping segue information.

    ex. 
    input: "Set 1: My Soul >  Bathtub Gin,  555,  Pebbles and Marbles[3]"
    return: ['My Soul >', 'Bathtub Gin', '555', 'Pebbles and Marbles']
    """
    this_set = pn_setlist.get_text().split(r':',1)

    set_name = this_set[0]
    set_string = this_set[1]

    set_list = []
    for song in set_string.strip().split(r'  '):
        song = re.sub(r'->|>','',song).strip()
        song = re.sub(r'\[[0-9]+\]','',song).strip()
        song = re.sub(r',$','',song).strip()
        set_list.append(song)

    return set_name, set_string, set_list

def get_api_key(path_to_key):
    """
    Get the api key for phish.net from the api_keys.json
      file located at the path specified from the command
      line args.
    """
    api_key_file = path_to_key + '/api_keys.json'
    with open(api_key_file) as f:
        apis = json.load(f)
        return apis["phishnet_api"]

if __name__ == '__main__':

    parser = argparse.ArgumentParser(prog="phishNet.py")
    parser.add_argument("-d","--api_dir", help="path to api keys directory"            , required=True              )
    parser.add_argument("-s","--start"  , help="year from where to start getting shows", default=this_year, type=int)
    parser.add_argument("-e","--end"    , help="year from where to stop getting shows" , default=this_year, type=int)
    parser.add_argument("-y","--year"   , help="get shows from only this year"         , default=0        , type=int)
    args = parser.parse_args()

    ##-------------------------------##
    ## Get the api key for phish.net ##
    ##-------------------------------##
    apikey = get_api_key(args.api_dir)

    ##--------------------------------------------------------##
    ## Get the showids for the desired year(s) from phish.net ##
    ##   then add them to the database if not there.          ##
    ##--------------------------------------------------------##
    if args.year != 0:
        args.start = args.end = args.year

    for year in range(args.start, args.end+1):
        print(u' > Getting showids for {0}'.format(year))
        show_ids = get_show_ids(str(year), apikey)
        for id in show_ids:
            get_show(id, apikey)
            time.sleep(1)
        time.sleep(5)

    ##-----------------------------##
    ## Close connection to MongoDB ##
    ##-----------------------------##
    client.close()




