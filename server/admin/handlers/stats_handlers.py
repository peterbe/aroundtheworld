import random
import time
import datetime
from collections import defaultdict
from .base import SuperuserBaseHandler
from tornado_utils.routes import route


@route('/admin/stats/hits/', name='admin_stats_hits')
class StatsHitsAdminHandler(SuperuserBaseHandler):

    def get(self):
        data = {}
        data['hits'] = self.redis.zrevrange('hits', 0, 100, withscores=True)
        self.render('admin/stats/hits.html', **data)


@route('/admin/stats/spread/', name='admin_stats_spread')
class StatsSpreadAdminHandler(SuperuserBaseHandler):

    def get(self):
        data = {}

        _locations = defaultdict(int)
        for user in self.db.User.collection.find(None, ('current_location',)):
            if user['current_location'] is None:
                continue
            _locations[user['current_location']] += 1

        locations = []
        for _id, count in _locations.items():
            location = self.db.Location.find_one({'_id': _id})
            locations.append((count, location))
        locations.sort(reverse=True)
        data['locations'] = locations
        self.render('admin/stats/spread.html', **data)


class ColorPump(object):
    _colors = (
        '#5C8D87,#994499,#6633CC,#B08B59,#DD4477,#22AA99,'
        '#668CB3,#DD5511,#D6AE00,#668CD9,#3640AD,'
        '#ff5800,#0085cc,#c747a3,#26B4E3,#bd70c7,#cddf54,#FBD178'
        .split(',')
    )
    def __init__(self):
        self.colors = iter(self._colors)

    def next(self):
        try:
            return self.colors.next()
        except StopIteration:
            return "#%s" % "".join([hex(random.randrange(0, 255))[2:]
                                    for i in range(3)])

@route('/admin/stats/numbers/', name='admin_stats_numbers')
class StatsNumbersAdminHandler(SuperuserBaseHandler):

    def get(self):
        data = {}
        if self.get_argument('get', None) == 'users_data':
            self.write({'data': self._get_users_data()})
        elif self.get_argument('get', None) == 'jobs_data':
            self.write({'data': self._get_jobs_data()})
        elif self.get_argument('get', None) == 'awards_data':
            self.write({'data': self._get_awards_data()})
        elif self.get_argument('get', None):
            raise NotImplementedError(self.get_argument('get'))
        else:
            self.render('admin/stats/numbers.html', **data)

    def _get_users_data(self, interval=datetime.timedelta(days=7)):
        #first, = self.db.User.collection.find().sort('add_date').limit(1)
        #first = first['add_date']
        first = datetime.datetime(2012, 6, 1)
        last, = self.db.User.collection.find().sort('add_date', -1).limit(1)
        last = last['add_date']
        date = first
        total_signed_in = 0
        total_anonymous = 0
        points = {
          'Anonymous': [],
          'Signed in': [],
        }
        while date < last:
            next = date + interval
            anonymous = (self.db.User
                         .find({'anonymous': True,
                                'add_date': {'$gte': date, '$lt': next}})
                         .count())
            signed_in = (self.db.User
                         .find({'anonymous': False,
                                'add_date': {'$gte': date, '$lt': next}})
                         .count())
            points['Anonymous'].append((date, anonymous))
            points['Signed in'].append((date, signed_in))
            total_anonymous += anonymous
            total_signed_in += signed_in
            date = next

        colors = iter(["#c05020", "#6060c0"])
        series = []
        for name, data in points.iteritems():
            series.append({
              'color': colors.next(),
              'name': name,
              'data': [{'x': int(time.mktime(a.timetuple())), 'y': b} for (a, b) in data]
            })

        return series

    def _get_jobs_data(self, interval=datetime.timedelta(days=7)):
        #first, = self.db.Job.collection.find().sort('add_date').limit(1)
        #first = first['add_date']
        first = datetime.datetime(2012, 6, 1)
        last, = self.db.Job.collection.find().sort('add_date', -1).limit(1)
        last = last['add_date']
        date = first
        points = defaultdict(list)
        cum_points = defaultdict(int)
        categories = [(x['_id'], x['name']) for x in
                      self.db.Category.collection.find(None, ('_id', 'name'))]
        while date < last:
            next = date + interval
            for category, name in categories:
                count = (self.db.Job.collection
                         .find({'category': category,
                                'add_date': {'$gte': date, '$lt': next}})
                         .count())
                points[name].append((date, count + cum_points.get(category, 0)))
                # uncomment if you want accumulative
                #cum_points[category] += count
            date = next

        colors = ColorPump()
        series = []
        for name, data in points.iteritems():
            series.append({
              'color': colors.next(),
              'name': name,
              'data': [{'x': int(time.mktime(a.timetuple())), 'y': b} for (a, b) in data]
            })

        return series

    def _get_awards_data(self, interval=datetime.timedelta(days=7)):
        first, = self.db.Award.collection.find().sort('add_date').limit(1)
        first = first['add_date'] - interval
        last, = self.db.Award.collection.find().sort('add_date', -1).limit(1)
        last = last['add_date']
        date = first
        points = defaultdict(list)
        cum_points = defaultdict(int)
        types = self.db.Award.collection.find().distinct('type')
        while date < last:
            next = date + interval
            for type_ in types:
                count = (self.db.Award.collection
                         .find({'type': type_,
                                'add_date': {'$gte': date, '$lt': next}})
                         .count())
                points[type_].append((date, count + cum_points.get(type_, 0)))
                # uncomment if you want accumulative
                #cum_points[type_] += count
            date = next

        colors = ColorPump()
        series = []
        for name, data in points.iteritems():
            series.append({
              'color': colors.next(),
              'name': name,
              'data': [{'x': int(time.mktime(a.timetuple())), 'y': b} for (a, b) in data]
            })

        return series
