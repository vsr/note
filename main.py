#!/usr/bin/env python

import os
import webapp2
from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext.webapp import template

providers = {
    'Google': 'www.google.com/accounts/o8/id',
    'Yahoo': 'yahoo.com',
    'MyOpenID': 'myopenid.com'
}


class Note(db.Model):
    author = db.UserProperty(auto_current_user_add=True)
    text = db.TextProperty()
    date = db.DateTimeProperty(auto_now=True)


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
            context.update({'is_authenticated': True, 'nickname': user.nickname(),
                'federated_identity': user.federated_identity(), 'email': user.email(),
                'text': text, 'last_modified': note.date,
                'logout_url': users.create_logout_url(self.request.uri)})

        else:
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


class AboutHandler(webapp2.RequestHandler):
    """ For about page """
    def get(self):
        path = os.path.join(os.path.dirname(__file__), 'about.html')
        self.response.out.write(template.render(path, {}))


app = webapp2.WSGIApplication([('/', MainHandler),
                               ('/useropenid', LoginHandler),
                               ('/about', AboutHandler)],
                              debug=True)
