import mimetypes
import datetime
import re
import urllib
from pprint import pprint
from collections import defaultdict
from pymongo.objectid import ObjectId
import tornado.escape
from tornado.web import HTTPError
from tornado_utils.routes import route
from .forms import QuestionForm, CategoryForm
from .base import AuthenticatedBaseHandler, AmbassadorBaseHandler
from .base import djangolike_request_dict
from core.handlers import QuizzingHandler


@route('/admin/questions/numbers/', name='admin_questions_numbers')
class QuestionsNumbersHandler(AuthenticatedBaseHandler):

    def get(self):
        data = {}
        categories = ['Jan', 'Feb']
        data['categories_json'] = tornado.escape.json_encode(categories)
        series = defaultdict(list)
        dates = (datetime.datetime(2012, 1, 1),
                 datetime.datetime(2012, 2, 1),
                 datetime.datetime(2012, 3, 1),
                 )
        intervals = []
        _prev = None
        for each in dates:
            if _prev is not None:
                intervals.append((_prev, each))
            _prev = each

        _previous = {}
        for start, end in intervals:
            _counts = defaultdict(int)
            for question in (self.db.Question
                             .find({'published': True,
                                    'add_date': {'$gte': start, '$lt': end}})):
                _counts[question['location']] += 1
            _these_locations = set()
            for location, count in _counts.items():
                series[location].append(_previous.get(location, 0) + count)
                _previous[location] = count
                _these_locations.add(location)
            for location in series.keys():
                if location not in _these_locations:
                    series[location].append(_previous.get(location, 0))

        #print series
        _names = dict((x['_id'], x['city'])
                      for x in self.db.Location.find())
        series = [{'name': _names[x], 'data': y}
                  for x, y in series.items()]
        data['series_json'] = tornado.escape.json_encode(series)
        self.render('admin/questions_numbers.html', **data)


@route('/admin/questions/', name='admin_questions')
class QuestionsAdminHandler(AuthenticatedBaseHandler):
    LIMIT = 20

    def get(self):
        data = {}
        filter_ = {}
        data['q'] = self.get_argument('q', '')
        if data['q']:
            _q = [re.escape(x.strip()) for x in data['q'].split(',')
                  if x.strip()]
            filter_['text'] = re.compile('|'.join(_q), re.I)
        data['all_locations'] = (
          self.db.Location
          .find({'airport_name': {'$ne': None}})
          .sort('code')
        )
        data['all_categories'] = (
          self.db.Category
          .find({'name': {'$nin': ['Geographer']}})
          .sort('name')
        )
        data['points_values'] = self.get_arguments('points_values', [])
        if data['points_values']:
            data['points_values'] = [int(x) for x in data['points_values']]
            filter_['points_value'] = {'$in': data['points_values']}
        data['locations'] = self.get_arguments('locations', [])
        if data['locations']:
            filter_['location'] = {
              '$in': [x['_id'] for x in
                       self.db.Location
                        .find({'code': {'$in': data['locations']}})]
            }

        data['categories'] = self.get_arguments('categories', [])
        if data['categories']:
            filter_['category'] = {
              '$in': [x['_id'] for x in
                       self.db.Category
                        .find({'name': {'$in': data['categories']}})]
            }
        data['authors'] = self.get_arguments('authors', [])
        if data['authors']:
            filter_['author'] = {
              '$in': [ObjectId(x) for x in data['authors']]
            }

        args = dict(self.request.arguments)
        if 'page' in args:
            args.pop('page')
        data['query_string'] = urllib.urlencode(args, True)

        data['page'] = int(self.get_argument('page', 1))
        skip = (data['page'] - 1) * self.LIMIT
        questions = []
        _locations = {}
        _categories = {}
        _users = {}
        data['count'] = self.db.Question.find(filter_).count()
        data['all_pages'] = range(1, data['count'] / self.LIMIT + 2)
        data['filtering'] = bool(filter_)
        for each in (self.db.Question
                     .find(filter_)
                     .sort('add_date', -1)  # newest first
                     .limit(self.LIMIT)
                     .skip(skip)):
            if each['category'] not in _categories:
                _categories[each['category']] = \
                  self.db.Category.find_one({'_id': each['category']})
            if each['location'] not in _locations:
                _locations[each['location']] = \
                  self.db.Location.find_one({'_id': each['location']})
            if each['author'] and each['author'] not in _users:
                _users[each['author']] = \
                  self.db.User.find_one({'_id': each['author']})
            questions.append((
              each,
              _categories[each['category']],
              _locations[each['location']],
              each['author'] and _users[each['author']] or None,
            ))
        data['questions'] = questions
        data['all_authors'] = _users.values()

        self.render('admin/questions.html', **data)


class BaseQuestionAdminHandler(AuthenticatedBaseHandler):

    @property
    def categories(self):
        return (self.db.Category
                .find({'manmade': True})
                .sort('name'))

    @property
    def locations(self):
        user = self.get_current_user()
        filter_ = {'airport_name': {'$ne': None}}
        if not user['superuser']:
            countries = (self.db.Ambassador
                         .find({'user': user['_id']})
                         .distinct('country'))
            assert countries  # no support for mayors yet
            filter_['country'] = {'$in': countries}
        return (self.db.Location
                .find(filter_)
                .sort('code', 1))

    def can_delete(self, question):
        if self.db.SessionAnswer.find({'question': question['_id']}).count():
            return False

        user = self.get_current_user()
        if not user['superuser']:
            if user['_id'] != question['author']:
                return False

        return True


@route('/admin/questions/add/', name='admin_add_question')
class AddQuestionAdminHandler(BaseQuestionAdminHandler):

    def get(self, form=None):
        data = {}
        if form is None:
            initial = {}
            _cutoff = (datetime.datetime.utcnow() -
                       datetime.timedelta(seconds=60 * 10))  # 10 min
            for q in (self.db.Question
                      .find({'author': self.get_current_user()['_id'],
                             'add_date': {'$gt': _cutoff}})
                      .sort('add_date', -1)  # newest first
                      .limit(1)):
                initial['published'] = q['published']
                initial['category'] = str(q['category'])
                initial['location'] = str(q['location'])

            if self.get_argument('category', None):
                cat = self.get_argument('category')
                category = self.db.Category.find_one({'name': cat})
                if category:
                    initial['category'] = str(category['_id'])
            if self.get_argument('location', None):
                location = self.db.Location.find_one({
                  'code': self.get_argument('location')})
                if location:
                    initial['location'] = str(location['_id'])

            form = QuestionForm(categories=self.categories,
                                locations=self.locations,
                                **initial)
        data['form'] = form
        self.render('admin/add_question.html', **data)

    def post(self):
        post_data = djangolike_request_dict(self.request.arguments)
        if self.request.files:
            post_data.update(djangolike_request_dict(self.request.files))
        if 'alternatives' in post_data:
            post_data['alternatives'] = ['\n'.join(post_data['alternatives'])]
        form = QuestionForm(post_data,
                            categories=self.categories,
                            locations=self.locations)
        if form.validate():
            question = self.db.Question()
            question['author'] = self.get_current_user()['_id']
            question['text'] = form.text.data
            question['correct'] = form.correct.data
            question['alternatives'] = [x.strip() for x
                                        in form.alternatives.data.splitlines()
                                        if x.strip()]
            question['alternatives_sorted'] = form.alternatives_sorted.data
            category = (self.db.Category
                        .find_one({'_id': ObjectId(form.category.data)}))
            assert category
            question['category'] = category['_id']
            question['points_value'] = int(form.points_value.data)
            question['published'] = form.published.data
            question['notes'] = form.notes.data.strip()
            question['didyouknow'] = form.didyouknow.data.strip()
            location = (self.db.Location
                        .find_one({'_id': ObjectId(form.location.data)}))
            assert location
            question['location'] = location['_id']
            question.save()
            if form.picture.data:
                picture = self.db.QuestionPicture()
                picture['question'] = question['_id']
                picture.save()

                try:
                    ok = False
                    image = form.picture.data
                    if not any([image['filename'].lower().endswith(x)
                                for x in ('.png', '.jpg', '.jpeg')]):
                        raise HTTPError(400)
                    assert isinstance(image['body'], str), type(image['body'])
                    type_, __ = mimetypes.guess_type(image['filename'])
                    with picture.fs.new_file('original') as f:
                        f.content_type = type_
                        f.write(image['body'])
                    ok = True
                finally:
                    if not ok:
                        picture.delete()
                        self.push_flash_message(
                          'Picture upload failed',
                          text='Check that the requirements for the picture '
                               'is correct',
                          type_='error'
                          )

            count = (self.db.Question
                     .find({'category': category['_id'],
                            'location': location['_id']})
                     .count())
            if count < 10:
                msg = ("%s more questions and people will be able to work as "
                       "a %s in %s" %
                       (11 - count, category['name'], location))
            else:
                msg = ("There are now %s questions of this category in %s" %
                       (count, location))
            self.push_flash_message("Question added!", msg, type_='success')

            self.redirect(self.reverse_url('admin_questions'))
        else:
            self.get(form=form)


@route('/admin/questions/(\w{24})/delete', name='admin_delete_question')
class DeleteQuestionAdminHandler(BaseQuestionAdminHandler):

    def post(self, _id):
        question = self.db.Question.find_one({'_id': ObjectId(_id)})
        assert question
        assert self.can_delete(question)
        for picture in (self.db.QuestionPicture
                        .find({'question': question['_id']})):
            picture.delete()
        question.delete()
        self.redirect(self.reverse_url('admin_questions'))


@route('/admin/questions/(\w{24})/', name='admin_question')
class QuestionAdminHandler(BaseQuestionAdminHandler):

    def get(self, _id, form=None):
        data = {}
        data['question'] = self.db.Question.find_one({'_id': ObjectId(_id)})
        if not data['question']:
            raise HTTPError(404)
        if form is None:
            initial = dict(data['question'])
            initial['category'] = str(initial['category'])
            initial['location'] = str(initial['location'])
            form = QuestionForm(categories=self.categories,
                                locations=self.locations,
                                **initial)
        data['form'] = form
        data['can_delete'] = self.can_delete(data['question'])
        self.render('admin/question.html', **data)

    def post(self, _id):
        data = {}
        question = self.db.Question.find_one({'_id': ObjectId(_id)})
        data['question'] = question
        post_data = djangolike_request_dict(self.request.arguments)
        if 'alternatives' in post_data:
            post_data['alternatives'] = ['\n'.join(post_data['alternatives'])]
        if self.request.files:
            post_data.update(djangolike_request_dict(self.request.files))
        form = QuestionForm(post_data,
                            categories=self.categories,
                            locations=self.locations)
        if form.validate():
            question['text'] = form.text.data
            question['correct'] = form.correct.data
            question['alternatives'] = [x.strip() for x
                                        in form.alternatives.data.splitlines()
                                        if x.strip()]
            question['alternatives_sorted'] = form.alternatives_sorted.data
            category = (self.db.Category
                        .find_one({'_id': ObjectId(form.category.data)}))
            assert category
            question['category'] = category['_id']
            question['points_value'] = int(form.points_value.data)
            question['published'] = form.published.data
            question['notes'] = form.notes.data.strip()
            question['didyouknow'] = form.didyouknow.data.strip()
            location = (self.db.Location
                        .find_one({'_id': ObjectId(form.location.data)}))
            assert location
            question['location'] = location['_id']
            question.save()

            if form.picture.data:
                if question.has_picture():
                    picture = question.get_picture()
                    picture.delete()
                picture = self.db.QuestionPicture()
                picture['question'] = question['_id']
                picture.save()

                try:
                    ok = False
                    image = form.picture.data
                    if not any([image['filename'].lower().endswith(x)
                                for x in ('.png', '.jpg', '.gif', '.jpeg')]):
                        raise HTTPError(400)
                    assert isinstance(image['body'], str), type(image['body'])
                    type_, __ = mimetypes.guess_type(image['filename'])
                    with picture.fs.new_file('original') as f:
                        f.content_type = type_
                        f.write(image['body'])
                    ok = True
                finally:
                    if not ok:
                        picture.delete()
                        self.push_flash_message(
                          'Picture upload failed',
                          text=('Check that the requirements for the picture '
                                'is correct'),
                          type_='error'
                          )

            self.redirect(self.reverse_url('admin_questions'))
        else:
            self.get(_id, form=form)


class BaseQuestionAdminHandler(AuthenticatedBaseHandler):

    @property
    def categories(self):
        return self.db.Category.find({'name': {'$nin': ['Geographer']}})

    @property
    def locations(self):
        user = self.get_current_user()
        filter_ = {'airport_name': {'$ne': None}}
        if not user['superuser']:
            countries = (self.db.Ambassador
                         .find({'user': user['_id']})
                         .distinct('country'))
            assert countries  # no support for mayors yet
            filter_['country'] = {'$in': countries}
        return (self.db.Location
                .find(filter_)
                .sort('code', 1))


@route('/admin/questions/categories/add/', name='admin_add_category')
class AddCategoryAdminHandler(BaseQuestionAdminHandler):

    def get(self, form=None):
        data = {}
        if form is None:
            initial = {}
            form = CategoryForm(categories=self.categories,
                                **initial)
        data['form'] = form
        self.render('admin/add_category.html', **data)

    def post(self):
        post_data = djangolike_request_dict(self.request.arguments)
        form = CategoryForm(post_data,
                            categories=self.categories)
        if form.validate():
            category = self.db.Category()
            category['name'] = form.name.data
            category['manmade'] = True
            category.save()
            url = self.reverse_url('admin_add_question')
            url += '?category=%s' % category['_id']
            self.redirect(url)
        else:
            self.get(form=form)


@route('/admin/questions/categories/', name='admin_categories')
class CategoriesAdminHandler(BaseQuestionAdminHandler):

    def get(self):
        data = {}
        counts = {}
        categories = []
        locations = []
        location_counts = {}
        for location in (self.db.Location
                         .find({'airport_name': {'$ne': None}})
                         .sort('code')):
            locations.append(location)
            location_counts[location['code']] = 0

        for category in (self.db.Category
                         .find({'manmade': True})
                         .sort('name')):
            counts[category['name']] = {}
            categories.append(category)
            for location in locations:
                count = (self.db.Question
                         .find({'category': category['_id'],
                                'location': location['_id']})
                         .count())
                counts[category['name']][location['code']] = count
                location_counts[location['code']] += count
        data['categories'] = categories
        data['locations'] = locations
        data['counts'] = counts
        data['location_counts'] = location_counts
        data['min_no_questions'] = QuizzingHandler.NO_QUESTIONS
        self.render('admin/categories.html', **data)
