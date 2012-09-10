import re
import urllib
from pymongo.objectid import ObjectId
from tornado_utils.routes import route
from tornado.web import HTTPError
from tornado_utils.send_mail import send_email
from .base import SuperuserBaseHandler
from .forms import FeedbackReplyForm
from .base import djangolike_request_dict
import settings


@route('/admin/feedback/', name='admin_feedbacks')
class FeedbacksAdminHandler(SuperuserBaseHandler):

    def get(self):
        data = {}
        filter_ = {'location': {'$ne': None}}
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
        self.trim_all_pages(data['all_pages'], data['page'])
        data['filtering'] = bool(filter_)
        _users = {}
        _locations = {}
        for each in (self.db.Feedback
                     .find(filter_)
                     .sort('add_date', -1)  # newest first
                     .limit(self.LIMIT)
                     .skip(skip)):

            if each['location'] and each['location'] not in _locations:
                _locations[each['location']] = (
                    self.db.Location.find_one({'_id': each['location']})
                )
            if each['user'] and each['user'] not in _users:
                _users[each['user']] = (
                    self.db.User.find_one({'_id': each['user']})
                )
            replies = self.db.Feedback.find({'reply_to': each['_id']})
            documents.append((
                each,
                each['location'] and _locations[each['location']] or None,
                each['user'] and _users[each['user']] or None,
                replies
            ))
        data['documents'] = documents
        self.render('admin/feedbacks.html', **data)


@route('/admin/feedback/(\w{24})/', name='admin_feedback_reply')
class FeedbackReplyAdminHandler(SuperuserBaseHandler):

    def get(self, _id, form=None):
        data = {}
        data['feedback'] = self.db.Feedback.find_one({'_id': ObjectId(_id)})
        if not data['feedback']:
            raise HTTPError(404)
        data['user'] = self.db.User.find_one({'_id': data['feedback']['user']})
        data['user_settings'] = (
            self.db.UserSettings.find_one({'user': data['user']['_id']})
        )
        data['user_location'] = (
            self.db.Location
            .find_one({'_id': data['user']['current_location']})
        )
        data['location'] = (self.db.Location
                            .find_one({'_id': data['feedback']['location']}))
        if form is None:
            initial = {}
            form = FeedbackReplyForm(**initial)
        data['form'] = form
        replies = []
        for each in (self.db.Feedback
                     .find({'reply_to': data['feedback']['_id']})
                     .sort('add_date')):
            replies.append((
                each,
                self.db.User.find_one({'_id': each['user']})
            ))
        data['replies'] = replies

        self.render('admin/feedback_reply.html', **data)

    def post(self, _id):
        feedback = self.db.Feedback.find_one({'_id': ObjectId(_id)})
        post_data = djangolike_request_dict(self.request.arguments)
        form = FeedbackReplyForm(post_data)

        if form.validate():
            current_user = self.get_current_user()
            reply = self.db.Feedback()
            reply['user'] = current_user['_id']
            reply['reply_to'] = feedback['_id']
            reply['comment'] = form.comment.data
            reply['what'] = u'reply'
            reply.save()

            self.set_header('Content-Type', 'text/plain')

            body = self.render_string("admin/feedback_reply.txt", **{
                'feedback': feedback,
                'feedback_location': (
                    self.db.Location.find_one({'_id': feedback['location']})
                ),
                'reply': reply,
                'reply_user': current_user,
            })

            if feedback.get('email'):
                email = feedback['email']
            else:
                user = self.db.User.find_one({'_id': feedback['user']})
                email = user['email']

            if email:
                subject = ("Reply to your feedback on %s"
                           % settings.PROJECT_TITLE)
                send_email(
                    self.application.settings['email_backend'],
                    subject,
                    body,
                    current_user['email'],
                    [email],
                )

                self.push_flash_message(
                    "Email sent!",
                    "Sent to %s" % email,
                    type_='success'
                )

            url = self.reverse_url('admin_feedback_reply', feedback['_id'])
            self.redirect(url)

        else:
            self.get(_id, form=form)
