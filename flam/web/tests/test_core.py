# encoding: utf-8
#
# Copyright (C) 2008-2009 Alec Thomas <alec@swapoff.org
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.
#
# Author: Alec Thomas <alec@swapoff.org>

import unittest
import logging

from flam import log
from flam.web.core import wsgi_application, Response, Request
from werkzeug import Client, create_environ


log.setLevel(logging.FATAL)


class TestApplication(unittest.TestCase):
    def setUp(self):
        self.app = wsgi_application(log_level=logging.FATAL)
        self.client = Client(wsgi_application(), Response)

    def test_csrf_without_token(self):
        response = self.client.post('/')
        self.assertTrue('Invalid form token' in response.data)
        self.assertEqual(response.status_code, 400)

    def test_csrf_with_valid_token(self):
        # TODO Add a form request handler. This will need some refactoring of
        # web.core. Yaks ahoy.
        response = self.client.get('/')
        response = self.client.post('/', data={
            'username': 'foo',
            '__FORM_TOKEN': 'one',
            })



if __name__ == '__main__':
    unittest.main()
