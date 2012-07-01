import mimetypes
import datetime
import re
import urllib
from cStringIO import StringIO
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
from . import picture_factory

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
                 datetime.datetime(2012, 4, 1),
                 datetime.datetime(2012, 5, 1),
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

        _names = dict((x['_id'], x['city'])
                      for x in self.db.Location.find())
        series = [{'name': _names[x], 'data': y}
                  for x, y in series.items()]
        data['series_json'] = tornado.escape.json_encode(series)
        self.render('admin/questions_numbers.html', **data)


@route('/admin/questions/', name='admin_questions')
class QuestionsAdminHandler(AuthenticatedBaseHandler):

    def get(self):
        data = {}
        filter_ = {}
        data['q'] = self.get_argument('q', '')
        if data['q']:
            _q = [re.escape(x.strip()) for x in data['q'].split(',')
                  if x.strip()]
            filter_['text'] = re.compile('|'.join(_q), re.I)
        data['published'] = self.get_argument('published', '')
        if data['published'] == 'not':
            filter_['published'] = False
        elif data['published'] == 'published':
            filter_['published'] = True
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
        self.trim_all_pages(data['all_pages'], data['page'])
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

@route('/admin/questions/inprogress/', name='admin_questions_in_progress')
class QuestionsInProgressAdminHandler(AuthenticatedBaseHandler):

    def get(self):
        options = {}
        question_statuses = defaultdict(list)
        min_no_countries = QuizzingHandler.NO_QUESTIONS
        _categories = {}  # for optimization
        countries = self.get_relevant_status_countries()
        for country in countries:
            for location in (self.db.Location
                             .find({'country': country,
                                    'airport_name': {'$ne': None}})):
                counts = defaultdict(int)
                for q in self.db.Question.find({'location': location['_id']}):
                    counts[q['category']] += 1
                for cat, count in counts.items():
                    if count >= min_no_countries:
                        continue
                    if cat not in _categories:
                        _categories[cat] = self.db.Category.find_one({'_id': cat})
                    question_statuses[location].append(dict(
                      category=_categories[cat]['name'],
                      count=count,
                      excess=max(0, count - min_no_countries),
                      left=min_no_countries - count,
                      percentage=int(min(100, 100.0 * count / min_no_countries)),
                      close=float(count) / min_no_countries > 0.8 and count < min_no_countries
                    ))
        options['question_statuses'] = sorted(question_statuses.items())
        self.render('admin/questions_in_progress.html', **options)

    def get_relevant_status_countries(self):
        current_user = self.get_current_user()
        if current_user['superuser']:
            return sorted(list(self.db.Location.find().distinct('country')))
        return sorted(list(self.db.Ambassador
                           .find({'user': current_user['_id']})
                           .distinct('country')))


@route('/admin/questions/add/', name='admin_add_question')
class AddQuestionAdminHandler(BaseQuestionAdminHandler):

    def get(self, form=None):
        data = {}
        if form is None:
            initial = {'seconds': 10}
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
            question['seconds'] = int(form.seconds.data)
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


class QuestionStatsMixin(object):
    def get_or_create_answer_stats(self, question):
        created = False
        stats = self.db.QuestionStats.find_one({'question': question['_id']})
        if stats:
            # check if it's older than the last time this question was used
            try:
                last_used, = (self.db.SessionAnswer
                              .find({'question': question['_id']})
                              .sort('add_date', -1)
                              .limit(1))
                if last_used['add_date'] > stats['modify_date']:
                    # stats is too old
                    stats.delete()
            except ValueError:
                pass

        if not stats:
            stats = self._create_answer_stats(question)
            created = True

        return stats, created

    def _create_answer_stats(self, question):
        stats = self.db.QuestionStats()
        stats['question'] = question['_id']
        has_answered = set()
        times = {
          'right': [],
          'wrong': []
        }
        unique_count = 0
        unique_count_timedout = 0
        rights = 0
        wrongs = 0
        for session in (self.db.QuestionSession
                        .find({'category': question['category']},
                              ('user',))
                        .sort('add_date')):
            if session['user'] in has_answered:
                continue
            for answer in (self.db.SessionAnswer
                           .find({'session': session['_id'],
                                  'question': question['_id']},
                                  ('correct', 'time', 'timedout'))
                           .sort('add_date')):
                if answer['timedout']:
                    unique_count_timedout += 1
                else:
                    if answer['time'] is None:
                        continue
                    unique_count += 1
                    times[answer['correct'] and 'right' or 'wrong'].append(answer['time'])
                    if answer['correct']:
                        rights += 1
                    else:
                        wrongs += 1
                has_answered.add(session['user'])

        #stats['times'] = {}
        if times['right']:
            stats['times']['right'] = sum(times['right']) / len(times['right'])
        if times['wrong']:
            stats['times']['wrong'] = sum(times['wrong']) / len(times['wrong'])
        stats['unique_count'] = unique_count
        stats['unique_count_timedout'] = unique_count_timedout
        stats['rights'] = rights
        if rights or wrongs:
            stats['rights_percentage'] = 100. * rights / (rights + wrongs)
        stats['wrongs'] = wrongs
        if rights or wrongs:
            stats['wrongs_percentage'] = 100. * wrongs / (rights + wrongs)
        stats.save()
        return stats


@route('/admin/questions/(\w{24})/', name='admin_question')
class QuestionAdminHandler(BaseQuestionAdminHandler, QuestionStatsMixin):

    def get(self, _id, form=None):
        data = {}
        data['question'] = self.db.Question.find_one({'_id': ObjectId(_id)})
        if not data['question']:
            raise HTTPError(404)
        if form is None:
            initial = dict(data['question'])
            initial['category'] = str(initial['category'])
            initial['location'] = str(initial['location'])
            #initial['seconds'] = str(initial['seconds'])
            form = QuestionForm(categories=self.categories,
                                locations=self.locations,
                                **initial)
        data['form'] = form
        data['can_delete'] = self.can_delete(data['question'])
        data['rating_total'] = (self.db.QuestionRatingTotal
                              .find_one({'question': data['question']['_id']}))
        data['answer_stats'], __ = self.get_or_create_answer_stats(data['question'])
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
            question['seconds'] = int(form.seconds.data)
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


@route('/admin/questions/(\w{24})/pictures/', name='admin_question_pictures')
class QuestionPicturesAdminHandler(BaseQuestionAdminHandler):

    def get(self, _id, form=None):
        data = {}
        data['question'] = self.db.Question.find_one({'_id': ObjectId(_id)})
        if not data['question']:
            raise HTTPError(404)

        # temporary legacy cleanup
        for x in self.db.QuestionPicture.find({'index': {'$exists': False}}):
            if getattr(x, 'copyright', 0) == 0:
                x['copyright'] = None
            if getattr(x, 'copyright_url', 0) == 0:
                x['copyright_url'] = None
            x['index'] = 0
            x.save()

        data['pictures'] = (self.db.QuestionPicture
                    .find({'question': data['question']['_id']})
                    .sort('index', 1))

        data['count'] = data['pictures'].count()
        data['filtering'] = False
        #data['form'] = form
        data['iterations'] = int(self.get_argument('iterations', 10))
        data['effect'] = int(self.get_argument('effect', 12))
        data['function'] = self.get_argument('function', '')

        #data['can_delete'] = self.can_delete(data['question'])
        self.render('admin/question_pictures.html', **data)

#    @tornado.web.asynchronous
    def post(self, _id):
        data = {}
        question = self.db.Question.find_one({'_id': ObjectId(_id)})
        if not question:
            raise HTTPError(404)

        url = self.reverse_url('admin_question_pictures', str(question['_id']))

        def delete_old():
            for p in (self.db.QuestionPicture
                      .find({'question': question['_id'],
                             'index': {'$gt': 0}})):
                p.delete()

        if self.get_argument('delete', False):
            delete_old()
            self.redirect(url)
            return

        iterations = int(self.get_argument('iterations'))
        effect = int(self.get_argument('effect', 0))

        delete_old()

        original, = self.db.QuestionPicture.find({'question': question['_id'], 'index': 0})
        original_picture = original.fs.get_last_version('original')
        type_ = original_picture.content_type
        c = 1

        function = self.get_argument('function')

        if function == 'blurrer':
            func = lambda x, y, z: picture_factory.blurrer(x, y, z, effect=effect)
        elif function == 'tileshift':
            func = picture_factory.tileshift
        else:
            raise NotImplementedError(function)

        for (payload, format) in func(original_picture, (700, 700),
                                      iterations):
            qp = self.db.QuestionPicture()
            qp['question'] = question['_id']
            qp['index'] = c
            qp.save()
            with qp.fs.new_file('original') as f:
                f.content_type = type_
                payload.save(f, format)

            c += 1

        url = self.reverse_url('admin_question_pictures', str(question['_id']))
        url += '?iterations=%s&effect=%s' % (iterations, effect)
        url += '&function=%s' % function
        self.redirect(url)
        #self.get(_id)


class xxxBaseQuestionAdminHandler(AuthenticatedBaseHandler):

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
        airports = self.get_argument('airports', 'available')
        data['airports'] = airports
        if airports == 'all':
            _locations = self.db.Location.find({'airport_name': {'$ne': None}})
        else:
            _locations = self.db.Location.find({'available': True})

        for location in _locations.sort('code'):
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


@route('/admin/questions/categories/(\w{24})/', name='admin_category')
class CategoryAdminHandler(BaseQuestionAdminHandler):

    def can_delete(self, category):
        c = self.db.Question.find({'category': category['_id']}).count()
        return not c

    def get(self, _id, form=None):
        data = {}
        data['category'] = self.db.Category.find_one({'_id': ObjectId(_id)})
        if not data['category']:
            raise HTTPError(404)
        if form is None:
            initial = dict(data['category'])
            form = CategoryForm(categories=self.categories, **initial)
        data['form'] = form
        data['can_delete'] = self.can_delete(data['category'])
        self.render('admin/category.html', **data)

    def post(self, _id):
        data = {}
        category = self.db.Category.find_one({'_id': ObjectId(_id)})
        data['category'] = category
        if not data['category']:
            raise HTTPError(404)
        post_data = djangolike_request_dict(self.request.arguments)
        form = CategoryForm(post_data,
                            categories=self.categories,
                            category=data['category'])
        if form.validate():
            category['name'] = form.name.data
            category['manmade'] = form.manmade.data
            category.save()
            self.redirect(self.reverse_url('admin_categories'))
        else:
            self.get(_id, form=form)


@route('/admin/questions/categories/(\w{24})/delete', name='admin_delete_category')
class DeleteCategoryAdminHandler(CategoryAdminHandler):

    def post(self, _id):
        category = self.db.Category.find_one({'_id': ObjectId(_id)})
        assert category
        assert self.can_delete(category)
        category.delete()

        self.redirect(self.reverse_url('admin_categories'))


@route('/admin/questions/ratings/', name='admin_question_ratings')
class QuestionRatingsAdminHandler(AuthenticatedBaseHandler):

    def get(self):
        data = {}
        filter_ = {}

        args = dict(self.request.arguments)
        if 'page' in args:
            args.pop('page')
        data['query_string'] = urllib.urlencode(args, True)

        data['page'] = int(self.get_argument('page', 1))
        skip = (data['page'] - 1) * self.LIMIT
        ratings = []
        _users = {}
        _questions = {}
        _rating_totals = {}
        data['count'] = self.db.QuestionRating.find(filter_).count()
        data['all_pages'] = range(1, data['count'] / self.LIMIT + 2)
        self.trim_all_pages(data['all_pages'], data['page'])
        data['filtering'] = bool(filter_)
        for each in (self.db.QuestionRating
                     .find(filter_)
                     .sort('add_date', -1)  # newest first
                     .limit(self.LIMIT)
                     .skip(skip)):
            if each['user'] not in _users:
                _users[each['user']] = \
                  self.db.User.find_one({'_id': each['user']})
            if each['question'] not in _questions:
                _questions[each['question']] = \
                  self.db.Question.find_one({'_id': each['question']})
            if each['question'] not in _rating_totals:
                _rating_totals[each['question']] = \
                  self._get_question_rating_total(_questions[each['question']])
            ratings.append((
              each,
              _questions[each['question']],
              _users[each['user']],
              _rating_totals[each['question']],
            ))
        data['ratings'] = ratings
        self.render('admin/question_ratings.html', **data)

    def _get_question_rating_total(self, question):
        rating_total = (self.db.QuestionRatingTotal
                        .find_one({'question': question['_id']}))
        if not rating_total:
            data = question.calculate_ratings()
            rating_total = self.db.QuestionRatingTotal()
            rating_total['question'] = question['_id']
            rating_total['average']['all'] = data['average']['all']
            rating_total['average']['right'] = data['average']['right']
            rating_total['average']['wrong'] = data['average']['wrong']
            rating_total['count']['all'] = data['count']['all']
            rating_total['count']['right'] = data['count']['right']
            rating_total['count']['wrong'] = data['count']['wrong']
            rating_total.save()

        return rating_total


@route('/admin/questions/ratings/highscore/',
       name='admin_question_ratings_highscore')
class QuestionRatingsHighscoreAdminHandler(AuthenticatedBaseHandler):

    def get(self):
        data = {}
        filter_ = {}

        args = dict(self.request.arguments)
        if 'page' in args:
            args.pop('page')
        data['query_string'] = urllib.urlencode(args, True)

        data['page'] = int(self.get_argument('page', 1))
        skip = (data['page'] - 1) * self.LIMIT
        totals = []
        _questions = {}
        data['count'] = self.db.QuestionRatingTotal.find(filter_).count()
        data['all_pages'] = range(1, data['count'] / self.LIMIT + 2)
        self.trim_all_pages(data['all_pages'], data['page'])

        data['filtering'] = bool(filter_)
        sort_key = self.get_argument('sort_key', 'average.all')
        sort_order = int(self.get_argument('sort_order', -1))
        data['sort_key'] = sort_key
        data['sort_order'] = sort_order
        for each in (self.db.QuestionRatingTotal
                     .find(filter_)
                     .sort(sort_key, sort_order)
                     .limit(self.LIMIT)
                     .skip(skip)):
            if each['question'] not in _questions:
                _questions[each['question']] = \
                  self.db.Question.find_one({'_id': each['question']})
            totals.append((
              each,
              _questions[each['question']],
            ))
        data['totals'] = totals
        self.render('admin/question_ratings_highscore.html', **data)


@route('/admin/questions/ratings/bias/',
       name='admin_question_ratings_bias')
class QuestionRatingsBiasAdminHandler(AuthenticatedBaseHandler):

    def get(self):
        data = {}
        all = []
        rights = []
        wrongs = []
        for each in self.db.QuestionRatingTotal.find():
            if not each['average']['all']:
                #print "Broken", repr(each)
                continue
            all.append(each['average']['all'])
            if each['average']['right']:
                rights.append(each['average']['right'])
            if each['average']['wrong']:
                wrongs.append(each['average']['wrong'])

        data['all'] = sum(all) / len(all)
        data['right'] = sum(rights) / len(rights)
        data['wrong'] = sum(wrongs) / len(wrongs)
        self.render('admin/question_ratings_bias.html', **data)


@route('/admin/questions/stats/', name='admin_question_stats')
class QuestionStatsAdminHandler(AuthenticatedBaseHandler, QuestionStatsMixin):

    def get(self):
        data = {}
        filter_ = {}

        args = dict(self.request.arguments)
        if 'page' in args:
            args.pop('page')
        data['query_string'] = urllib.urlencode(args, True)

        data['page'] = int(self.get_argument('page', 1))
        skip = (data['page'] - 1) * self.LIMIT
        statss = []
        _questions = {}
        data['count'] = self.db.QuestionStats.find(filter_).count()
        data['all_pages'] = range(1, data['count'] / self.LIMIT + 2)
        self.trim_all_pages(data['all_pages'], data['page'])

        data['filtering'] = bool(filter_)
        sort_key = self.get_argument('sort_key', 'unique_count')
        sort_order = int(self.get_argument('sort_order', -1))
        data['sort_key'] = sort_key
        data['sort_order'] = sort_order
        for each in (self.db.QuestionStats
                     .find(filter_)
                     .sort(sort_key, sort_order)
                     .limit(self.LIMIT)
                     .skip(skip)):
            if each['question'] not in _questions:
                _questions[each['question']] = \
                  self.db.Question.find_one({'_id': each['question']})
            question = _questions[each['question']]
            pv = each.get('question_points_value')
            if not pv:
                each['question_points_value'] = question['points_value']
                each.save()
                pv = question['points_value']
            try:
                expected_percentage = 100 - 100.0 * pv / 6
                actual_percentage = round(100.0 * each['rights'] /
                                          (each['unique_count'] +
                                           each['unique_count_timedout']), 1)
                diff = abs(actual_percentage - expected_percentage)
                if actual_percentage > expected_percentage:
                    too_something = 'too easy'
                else:
                    too_something = 'too hard'
                if diff > 20.0:
                    verdict = (too_something, 'important')
                elif diff > 10.0:
                    verdict = (too_something, 'warning')
                else:
                    verdict = ('fine', 'success')
            except ZeroDivisionError:
                verdict = None
            statss.append((
              each,
              question,
              verdict
            ))
        data['statss'] = statss
        data['no_questions'] = self.db.Question.find({'published': True}).count()
        self.render('admin/question_stats.html', **data)

    def post(self):
        max_count = 100
        count = 0
        for question in self.db.Question.find({'published': True}):
            __, created = self.get_or_create_answer_stats(question)
            if created:
                count += 1
                if count >= max_count:
                    self.push_flash_message("Capped",
                      "Capped stats creation to %d" % max_count)
                    break

        self.redirect(self.reverse_url('admin_question_stats'))
