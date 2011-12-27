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
    print "SEARCH", repr(search)
    sys.exit(run(search))
