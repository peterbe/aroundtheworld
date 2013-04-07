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

        _all_locations = {}
        _locations = defaultdict(int)
        for user in self.db.User.collection.find(None, ('current_location',)):
            if user['current_location'] is None:
                continue
            _locations[user['current_location']] += 1
        locations = []
        for _id, count in _locations.items():
            if _id not in _all_locations:
                _all_locations[_id] = (
                    self.db.Location.find_one({'_id': _id})
                )
            location = _all_locations[_id]
            if not location['available']:
                continue
            locations.append((count, location))
        locations.sort(reverse=True)
        data['locations'] = locations

        _flights_to = defaultdict(int)
        _destinations = defaultdict(int)
        for each in self.db.Flight.collection.find(None, ('to', 'user')):
            _flights_to[each['to']] += 1
            _destinations[each['user']] += 1
        flights_to = []
        for _id, count in _flights_to.items():
            if _id not in _all_locations:
                _all_locations[_id] = (
                    self.db.Location.find_one({'_id': _id})
                )
            location = _all_locations[_id]
            if not location['available']:
                continue
            flights_to.append((count, location))
        flights_to.sort(reverse=True)
        data['flights_to'] = flights_to

        destinations = defaultdict(int)
        for count in _destinations.values():
            destinations[count] += 1

        #destinations = [(count) for (count, x) in destinations.items()]
        total_flights = sum(destinations.values())
        destinations = [(x, round(100. * y / total_flights, 1), y)
                        for (x, y) in destinations.items()]
        destinations.sort()
        data['destinations'] = destinations

        data['no_anonymous'] = self.db.User.find({'anonymous': True}).count()
        data['not_anonymous'] = self.db.User.find({'anonymous': False}).count()
        total = data['no_anonymous'] + data['not_anonymous']
        data['no_anonymous_percentage'] = round(
            100.0 * data['no_anonymous'] / total
        )
        data['not_anonymous_percentage'] = round(
            100.0 * data['not_anonymous'] / total
        )

        could_subscribe = data['not_anonymous']
        not_subscribed = self.db.UserSettings.find({'unsubscribe_emails': True}).count()
        data['subscribed'] = could_subscribe - not_subscribed
        data['not_subscribed'] = not_subscribed
        total = data['subscribed'] + data['not_subscribed']
        data['subscribed_percentage'] = round(
            100.0 * data['subscribed'] / total
        )
        data['not_subscribed_percentage'] = round(
            100.0 * data['not_subscribed'] / total
        )

        """
        flights_to = defaultdict(int)
        destinations_to = defaultdict(int)
        _locations = {}
        for flight in self.db.Flight.find(None, ('to', 'user')):
            #print flight['to']
            if flight['to'] not in _locations:
                _locations[flight['to']] = (
                    self.db.Location.collection
                    .find_one({'_id': flight['to']})['name']
                )

            flights_to[_locations[flight['to']]] += 1
        print flights_to
        """
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
        since = datetime.datetime(2012, 6, 1)
        if self.get_argument('since', None):
            since = datetime.datetime.strptime(
                self.get_argument('since'),
                '%Y-%m-%d'
            )
        data['since'] = since.strftime('%Y-%m-%d')
        if self.get_argument('get', None) == 'users_data':
            self.write({'data': self._get_users_data(since=since)})
        elif self.get_argument('get', None) == 'jobs_data':
            self.write({'data': self._get_jobs_data(since=since)})
        elif self.get_argument('get', None) == 'awards_data':
            self.write({'data': self._get_awards_data(since=since)})
        elif self.get_argument('get', None) == 'miles_travelled_data':
            self.write({'data': self._get_miles_travelled_data(since=since)})
        elif self.get_argument('get', None):
            raise NotImplementedError(self.get_argument('get'))
        else:
            data['users'] = self._get_users(since, interval=None)
            data['friendships'] = self._get_friendships(since, interval=None)
            self.render('admin/stats/numbers.html', **data)

    def _get_users(self, since, interval=datetime.timedelta(days=7)):
        first = since
        last, = self.db.User.collection.find().sort('add_date', -1).limit(1)
        last = last['add_date']
        data = []
        date = first
        prev_signed_in = None
        prev_anonymous = None

        while date < last:
            next = date
            if interval:
                next += interval
            else:
                # monthly increment
                while next.month == date.month:
                    next += datetime.timedelta(days=1)
            anonymous = (self.db.User
                         .find({'anonymous': True,
                                'add_date': {'$gte': date, '$lt': next}})
                         .count())
            signed_in = (self.db.User
                         .find({'anonymous': False,
                                'add_date': {'$gte': date, '$lt': next}})
                         .count())

            if prev_signed_in is None:
                signed_in_diff = None
            else:
                signed_in_diff = signed_in - prev_signed_in
            if prev_anonymous is None:
                anonymous_diff = None
            else:
                anonymous_diff = anonymous - prev_anonymous
            data.append({
                'date': date.strftime('%d %b %Y'),
                'signed_in': signed_in,
                'signed_in_diff': signed_in_diff if signed_in_diff is not None else '--',
                'anonymous': anonymous,
                'anonymous_diff': anonymous_diff if anonymous_diff is not None else '--',
            })
            prev_signed_in = signed_in
            prev_anonymous = anonymous
            date = next

        return data

    def _get_friendships(self, since, interval=datetime.timedelta(days=7)):
        _first = datetime.datetime(2012, 9, 14, 0, 0, 0)  # the day is was launched
        first = max(since, _first)
        last, = self.db.Friendship.collection.find().sort('add_date', -1).limit(1)
        last = last['add_date']
        data = []
        date = first
        prev_not_mutual = None
        prev_mutual = None
        while date < last:
            next = date
            if interval:
                next += interval
            else:
                # monthly increment
                while next.month == date.month:
                    next += datetime.timedelta(days=1)
            not_mutual = (self.db.Friendship
                          .find({'add_date': {'$gte': date, '$lt': next}})
                          .count())
            mutual = (self.db.Friendship
                      .find({'mutual': True,
                             'add_date': {'$gte': date, '$lt': next}})
                      .count())

            if prev_not_mutual is None:
                not_mutual_diff = None
            else:
                not_mutual_diff = not_mutual - prev_not_mutual
            if prev_mutual is None:
                mutual_diff = None
            else:
                mutual_diff = mutual - prev_mutual
            data.append({
                'date': date.strftime('%d %b %Y'),
                'not_mutual': not_mutual,
                'not_mutual_diff': not_mutual_diff if not_mutual_diff is not None else '--',
                'mutual': mutual,
                'mutual_diff': mutual_diff if mutual_diff is not None else '--',
            })
            prev_not_mutual = not_mutual
            prev_mutual = mutual
            date = next

        return data

    def _get_users_data(self, since=None, interval=datetime.timedelta(days=7)):
        first = since and since or datetime.datetime(2012, 6, 1)
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

    def _get_jobs_data(self, since=None, interval=datetime.timedelta(days=7)):
        first = since and since or datetime.datetime(2012, 6, 1)
        last, = self.db.Job.collection.find().sort('add_date', -1).limit(1)
        last = last['add_date']
        date = first
        points = defaultdict(list)
        cum_points = defaultdict(int)
        categories = [(x['_id'], x['name']) for x in
                      self.db.Category.collection.find(None, ('_id', 'name'))]
        _categories = dict(categories)
        while date < last:
            next = date + interval
            counts = defaultdict(int)
            for job in (self.db.Job.collection
                         .find({'add_date': {'$gte': date, '$lt': next}},
                               ('category',))):
                counts[job['category']] += 1

            for category, name in categories:
                count = counts[category]
                points[name].append((date, count + cum_points.get(category, 0)))

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

    def _get_awards_data(self, since=None, interval=datetime.timedelta(days=7)):
        if since:
            first = since
        else:
            first, = self.db.Award.collection.find().sort('add_date').limit(1)
            first = first['add_date']
        first = first - interval
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

    def _get_miles_travelled_data(self, since=None, intervals=12):
        min_ = 0.0
        bands = defaultdict(int)
        max_ = 10000

        chunk = (max_ - min_) / intervals
        data = []

        colors = ColorPump()

        series = []
        for i in range(intervals):
            a, b = i * chunk, (i + 1) * chunk
            a = int(round(a / 1000.0) * 1000)
            b = int(round(b / 1000.0) * 1000)
            if b == max_:
                b *= 10
            filter_ = {'miles_total': {'$gte': a, '$lt': b}}
            if since:
                filter_['add_date'] = {'$gte': since}
            c = (self.db.UserSettings
                 .find(filter_)
                 .count())
            data = []
            for j in range(intervals):
                data.append({'x': j, 'y': c if i == j else 0})
            series.append({
              'name': '%d to %d' % (a, b),
              'color': colors.next(),
              'data': data
            })
        return series
