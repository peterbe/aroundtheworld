#!/usr/bin/env python
from geopy import geocoders

def run(search):
    g = geocoders.Google()
    results = g.geocode(search, exactly_one=False)
    for place, (lat, lng) in results:
        print "PLACE", place
        print "LAT", lat
        print "LNG", lng
        print
    return 0

if __name__ == '__main__':
    import sys
    search = ' '.join(sys.argv[1:])
    if search:
        search = [search]
    else:
        search = [x.strip() for x in sys.stdin.read().splitlines()
                  if x.strip()]
    for each in search:
        run(each)
        print
    #sys.exit()
