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
