from unittest import TestCase
from core.models import User, connection
from .base import DatabaseTestCaseMixin

class ModelsTestCase(TestCase, DatabaseTestCaseMixin):

    def setUp(self):
        self.db = connection.test
        super(ModelsTestCase, self).setUp()
        self.setup_connection()

    def tearDown(self):
        self.teardown_connection()

    def test_question_check_answer(self):
        from core.models import Question
        q = Question()
        q['correct'] = u'Yes'
        self.assertTrue(q.check_answer('yes'))
        self.assertTrue(not q.check_answer('no'))

        q['alternatives'] = [u'Maybe', u'Perhaps']
        self.assertTrue(q.check_answer('yes', alternatives_are_correct=True))
        self.assertTrue(q.check_answer('maybe', alternatives_are_correct=True))
        self.assertTrue(q.check_answer('perhaps', alternatives_are_correct=True))
        self.assertTrue(not q.check_answer('inte', alternatives_are_correct=True))

        # now with edit distance
        # too short
        self.assertTrue(not q.check_answer('yeah'))
        # sufficiently long
        q['correct'] = u'Correct'
        self.assertTrue(q.check_answer('corect'))
        self.assertTrue(not q.check_answer('korecct'))
