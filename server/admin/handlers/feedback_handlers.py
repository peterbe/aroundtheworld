import re
import urllib
from pymongo.objectid import ObjectId
from tornado_utils.routes import route
from .base import djangolike_request_dict, SuperuserBaseHandler


@route('/admin/feedback/', name='admin_feedbacks')
class FeedbacksAdminHandler(SuperuserBaseHandler):
    LIMIT = 20

    def get(self):
        data = {}
        filter_ = {}
        data['q'] = self.get_argument('q', '')
        if data['q']:
            _q = [re.escape(x.strip()) for x in data['q'].split(',')
                  if x.strip()]
            filter_['comment'] = re.compile('|'.join(_q), re.I)

        data['all_whats'] = (self.db.Feedback
                             .find()
                             .distinct('what'))
        data['all_whats'].sort()
        data['whats'] = self.get_arguments('whats', [])
        if data['whats']:
            filter_['what'] = {'$in': data['whats']}
        args = dict(self.request.arguments)
        if 'page' in args:
            args.pop('page')
        data['query_string'] = urllib.urlencode(args, True)

        data['page'] = int(self.get_argument('page', 1))
        skip = max(0, data['page'] - 1) * self.LIMIT
        documents = []
        data['count'] = self.db.Feedback.find(filter_).count()
        data['all_pages'] = range(1, data['count'] / self.LIMIT + 2)
        data['filtering'] = bool(filter_)
        _users = {}
        _locations = {}
        for each in (self.db.Feedback
                     .find(filter_)
                     .sort('add_date', -1)  # newest first
                     .limit(self.LIMIT)
                     .skip(skip)):

            if each['location'] and each['location'] not in _locations:
                _locations[each['location']] = \
                  self.db.Location.find_one({'_id': each['location']})
            if each['user'] and each['user'] not in _users:
                _users[each['user']] = \
                  self.db.User.find_one({'_id': each['user']})
            documents.append((
              each,
              each['location'] and _locations[each['location']] or None,
              each['user'] and _users[each['user']] or None
            ))
        data['documents'] = documents
        self.render('admin/feedbacks.html', **data)
