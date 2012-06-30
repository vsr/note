#!/usr/bin/env python

import os
import json
from hashlib import sha256
from uuid import uuid4
from random import getrandbits
from datetime import datetime

import webapp2
from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext.webapp import template

providers = {
    'Google': 'www.google.com/accounts/o8/id',
    'Yahoo': 'yahoo.com',
    'MyOpenID': 'myopenid.com'
}

epoch = datetime(1970, 1, 1)
CONTENT_TYPE_JSON = 'application/json'


class Note(db.Model):
    author = db.UserProperty(auto_current_user_add=True)
    text = db.TextProperty()
    date = db.DateTimeProperty(auto_now=True)
    secret_key = db.StringProperty()

    def reset_key(self):
        self.secret_key = sha256(sha256(str(getrandbits(512))).hexdigest() + sha256(uuid4().hex).hexdigest()).hexdigest()
        self.put()
        return self.secret_key


class MainHandler(webapp2.RequestHandler):
    def get(self):
        context = {}
        user = users.get_current_user()
        if user:
            note = Note.get_or_insert(user.nickname(), text='')
            context.update({'is_authenticated': True, 'nickname': user.nickname(),
                'federated_identity': user.federated_identity(), 'email': user.email(),
                'text': note.text, 'last_modified': note.date,
                'logout_url': users.create_logout_url(self.request.uri)})
        else:
            login_urls = []
            for name, uri in providers.items():
                login_urls.append((users.create_login_url(federated_identity=uri), name))
            context.update({'is_authenticated': False, 'login_urls': login_urls})

        path = os.path.join(os.path.dirname(__file__), 'index.html')
        self.response.out.write(template.render(path, context))

    def post(self):
        context = {}
        user = users.get_current_user()
        if user:
            text = self.request.get('text')
            note = Note.get_or_insert(user.nickname(), text=text)
            note.text = text
            note.put()
            self.response.status_int = 302
            self.response.location = '/'
            return

        else:
            self.response.status_int = 401
            login_urls = []
            for name, uri in providers.items():
                login_urls.append((users.create_login_url(federated_identity=uri), name))
            context.update({'is_authenticated': False, 'login_urls': login_urls})

        path = os.path.join(os.path.dirname(__file__), 'index.html')
        self.response.out.write(template.render(path, context))


class LoginHandler(webapp2.RequestHandler):
    """ Handle openid for user defined provider"""
    def get(self):
        idprovider = self.request.get('idprovider')
        login_url = users.create_login_url(federated_identity=idprovider)
        self.response.status_int = 302
        self.response.location = login_url


class SettingsHandler(webapp2.RequestHandler):
    """ For settings page """
    def get(self):
        context = {}
        user = users.get_current_user()
        if user:
            note = Note.get_or_insert(user.nickname(), text='')
            context.update({'is_authenticated': True, 'nickname': user.nickname(),
                'federated_identity': user.federated_identity(), 'email': user.email(),
                'secret_key': note.secret_key, 'host_url': self.request.host_url,
                'logout_url': users.create_logout_url(self.request.uri)})
            path = os.path.join(os.path.dirname(__file__), 'settings.html')
            self.response.out.write(template.render(path, context))
        else:
            self.response.status_int = 302
            self.response.location = '/'

    def post(self):
        user = users.get_current_user()
        if user:
            note = Note.get_or_insert(user.nickname(), text='')
            note.reset_key()
            self.response.status_int = 302
            self.response.location = '/settings'
        else:
            self.response.status_int = 302
            self.response.location = '/'


class ApiHandler(webapp2.RequestHandler):
    """ For API """
    def get(self, secret_key):
        response = {}
        note = Note.all().filter('secret_key =', secret_key).get()
        if note:
            response['text'] = note.text
            response['last_modified'] = int((note.date - epoch).total_seconds())
        else:
            response['error'] = 'Note not found'
            self.response.status_int = 404
        self.response.content_type = CONTENT_TYPE_JSON
        self.response.out.write(json.dumps(response))

    def put(self, secret_key):
        response = {}
        note = Note.all().filter('secret_key =', secret_key).get()
        if note:
            text = self.request.get('text')
            if text:
                note.text = text
                note.put()
                self.response.status_int = 204
                self.response.status_message = u'No Content'
                return
            else:
                response['error'] = "text not provided."
                self.response.status_int = 400
        else:
            response['error'] = 'Note not found'
            self.response.status_int = 404
        self.response.content_type = CONTENT_TYPE_JSON
        self.response.out.write(json.dumps(response))


class AboutHandler(webapp2.RequestHandler):
    """ For about page """
    def get(self):
        path = os.path.join(os.path.dirname(__file__), 'about.html')
        self.response.out.write(template.render(path, {'host_url': self.request.host_url}))


app = webapp2.WSGIApplication([('/', MainHandler),
                               ('/useropenid', LoginHandler),
                               ('/about', AboutHandler),
                               ('/api/note/(\w+)', ApiHandler),
                               ('/settings', SettingsHandler)],
                              debug=True)
