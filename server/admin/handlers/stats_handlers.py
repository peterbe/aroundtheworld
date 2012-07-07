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
