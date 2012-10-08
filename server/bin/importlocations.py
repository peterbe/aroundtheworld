#!/usr/bin/env python

import code, re
try:
    import here
except ImportError:
    import sys
    import os.path as op
    sys.path.insert(0, op.abspath(op.join(op.dirname(__file__), '..')))
    import here

from pprint import pprint
import csv
import codecs
from cStringIO import StringIO


def unicode_csv_reader(unicode_csv_data,
                       encoding='utf-8',
                       **kwargs):
    # csv.py doesn't do Unicode; encode temporarily as UTF-8:
    csv_reader = csv.reader(utf_8_encoder(unicode_csv_data, encoding),
                             **kwargs)
    for row in csv_reader:
        # decode UTF-8 back to Unicode, cell by cell:
        yield [unicode(cell, encoding) for cell in row]

def utf_8_encoder(unicode_csv_data, encoding):
    for line in unicode_csv_data:
        yield line.encode(encoding)

def parse(file_name, encoding='utf8'):
    csv_file = codecs.open(file_name, 'r', encoding)
    #reader = csv.reader(csv_file)
    reader = unicode_csv_reader(csv_file, encoding, delimiter=',')

    for row in reader:
        if row[0] == 'CITY':
            continue
        yield row

    csv_file.close()

def is_different(dict1, dict2):
    if not dict2:
        return True

    keys = ('city', 'country', 'locality', 'lat', 'lng',
            'code', 'airport_name')
    for key in keys:
        v1 = dict1[key]
        v2 = dict2[key]
        if v1 != v2:
            return True

    return False

if __name__ == '__main__':
    from models import *
    from bson.objectid import ObjectId, InvalidId

    import settings
    db = connection[settings.DATABASE_NAME]
    import sys, os
    args = sys.argv[1:]
    if '--verbose' in args:
        args.remove('--verbose')
        verbose = True
    elif '-v' in args:
        args.remove('-v')
        verbose = True
    else:
        verbose = False

    filename = os.path.abspath(args[0])


    for row in parse(filename):
        _id = None
        while len(row) < 7:
            row.append(u'')
        try:
            (city, country, lat, lng,
             locality, code, airport_name) = [x.strip() for x in row[:7]]
        except ValueError:
            print
            print row
            print len(row)
            print
            raise
        if len(row) == 8:
            _id = row[7]

        if _id:
            location = db.Location.find_one({'_id': ObjectId(_id)})
        else:
            if code:
                location = db.Location.find_one({'code': code})
            else:
                location = db.Location.find_one({'city': city, 'country': country})
            if not location:
                location = db.Location()

        if hasattr(location, '_id'):
            orig_location = dict(location)
        else:
            orig_location = None

        location['city'] = city
        location['country'] = country
        location['lat'] = float(lat)
        location['lng'] = float(lng)
        if locality:
            location['locality'] = locality
        else:
            location['locality'] = None
        if code:
            location['code'] = code
        else:
            location['code'] = None
        if airport_name:
            location['airport_name'] = airport_name
        else:
            location['airport_name'] = None

        if not is_different(dict(location), orig_location):
            continue

        if verbose:
            d = dict(location)
            if not hasattr(location, '_id'):
                print "*** NEW !! ***"
            del d['add_date']
            del d['modify_date']
            print "\tCity:", repr(location['city'])
            print "\tCountry:", repr(location['country'])
            print "\tLAT:", repr(location['lat'])
            print "\tLNG:", repr(location['lng'])
            print "\tLocality:", repr(location['locality'])
            print "\tCode:", repr(location['code'])
            print "\tAirport name:", repr(location['airport_name'])

            i = raw_input('Save? [Y/a/n] ').strip().lower()
            if i == 'a':
                verbose = False
            elif i == 'n':
                print "SKIP"
                continue
        location.save()

    if verbose:
        print
        print "There are now", db.Location.find().count(), "locations!"
        print db.Location.find({'airport_name': {'$ne': None}}).count(), "with airports"
