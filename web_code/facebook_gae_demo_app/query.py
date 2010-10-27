#!/usr/bin/env python
#
# Copyright 2010 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""
TODOs:
 * Automatically handle refreshing access token when it expires
   instead of requiring the user to login again to refresh it

Change log:

* Aug 2010 - MAR
** Adapted to examples/oauth/facebookoauth.py to run Graph API
   and FQL queries by adding QueryHandler
** Renamed facebookoauth.py to query.py and added query.html
** Added in ability for app to request extended permissions
"""


"""A barebones AppEngine application that uses Facebook for login.

This application uses OAuth 2.0 directly rather than relying on Facebook's
JavaScript SDK for login. It also accesses the Facebook Graph API directly
rather than using the Python SDK. It is designed to illustrate how easy
it is to use the Facebook Platform without any third party code.

See the "appengine" directory for an example using the JavaScript SDK.
Using JavaScript is recommended if it is feasible for your application,
as it handles some complex authentication states that can only be detected
in client-side code.
"""

# XXX: Provide your own id/secret
FACEBOOK_APP_ID = ""
FACEBOOK_APP_SECRET = ""

import base64
import cgi
import Cookie
import email.utils
import hashlib
import hmac
import logging
import os.path
import time
import urllib
import wsgiref.handlers
import re

from django.utils import simplejson as json
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext.webapp import template

import facebook
from fql import FQL

# you could customize which extended permissions are being requested on the login page
# or by editing the list below. By default, all the ones that make sense for read access
# as described on http://developers.facebook.com/docs/authentication/ are included.
# It would be probably be ridiculous to request this much access if you wanted to launch
# a successful production application.
EXTENDED_PERMS = [
        "user_about_me",
        "friends_about_me",
        "user_activities",
        "friends_activities",
        "user_birthday",
        "friends_birthday",
        "user_education_history",
        "friends_education_history",
        "user_events",
        "friends_events",
        "user_groups",
        "friends_groups",
        "user_hometown",
        "friends_hometown",
        "user_interests",
        "friends_interests",
        "user_likes",
        "friends_likes",
        "user_location",
        "friends_location",
        "user_notes",
        "friends_notes",
        "user_online_presence",
        "friends_online_presence",
        "user_photo_video_tags",
        "friends_photo_video_tags",
        "user_photos",
        "friends_photos",
        "user_relationships",
        "friends_relationships",
        "user_religion_politics",
        "friends_religion_politics",
        "user_status",
        "friends_status",
        "user_videos",
        "friends_videos",
        "user_website",
        "friends_website",
        "user_work_history",
        "friends_work_history",
        "email",
        "read_friendlists",
        "read_requests",
        "read_stream",
        "user_checkins",
        "friends_checkins",
]


class User(db.Model):
    id = db.StringProperty(required=True)
    created = db.DateTimeProperty(auto_now_add=True)
    updated = db.DateTimeProperty(auto_now=True)
    name = db.StringProperty(required=True)
    profile_url = db.StringProperty(required=True)
    access_token = db.StringProperty(required=True)


class BaseHandler(webapp.RequestHandler):
    @property
    def current_user(self):
        """Returns the logged in Facebook user, or None if unconnected."""
        if not hasattr(self, "_current_user"):
            self._current_user = None
            user_id = parse_cookie(self.request.cookies.get("fb_user"))
            if user_id:
                self._current_user = User.get_by_key_name(user_id)
        return self._current_user

    @property
    def graph(self):
        """Returns a Graph API client for the current user."""
        if not hasattr(self, "_graph"):
            if self.current_user:
                self._graph = facebook.GraphAPI(self.current_user.access_token)
            else:
                self._graph = facebook.GraphAPI()
        return self._graph


class HomeHandler(BaseHandler):
    def get(self):
        path = os.path.join(os.path.dirname(__file__), "oauth.html")
        args = dict(current_user=self.current_user)
        self.response.out.write(template.render(path, args))


class LoginHandler(BaseHandler):
    def get(self):
        verification_code = self.request.get("code")
        args = dict(client_id=FACEBOOK_APP_ID, redirect_uri=self.request.path_url)
        if self.request.get("code"):
            args["client_secret"] = FACEBOOK_APP_SECRET
            args["code"] = self.request.get("code")
            response = cgi.parse_qs(urllib.urlopen(
                "https://graph.facebook.com/oauth/access_token?" +
                urllib.urlencode(args)).read())
            access_token = response["access_token"][-1]

            # Download the user profile and cache a local instance of the
            # basic profile info
            profile = json.load(urllib.urlopen(
                "https://graph.facebook.com/me?" +
                urllib.urlencode(dict(access_token=access_token))))
            user = User(key_name=str(profile["id"]), id=str(profile["id"]),
                        name=profile["name"], access_token=access_token,
                        profile_url=profile["link"])
            user.put()
            set_cookie(self.response, "fb_user", str(profile["id"]),
                       expires=time.time() + 30 * 86400)
            self.redirect("/")
        else:
            args["scope"] = ",".join(EXTENDED_PERMS)
            self.redirect(
                "https://graph.facebook.com/oauth/authorize?" +
                urllib.urlencode(args))


class LogoutHandler(BaseHandler):
    def get(self):
        set_cookie(self.response, "fb_user", "", expires=time.time() - 86400)
        self.redirect("/")


class QueryHandler(BaseHandler):

    def do_graph_query(self, q):
        # eval a query of the form self.graph.get_connections("me", "friends")
        try:
            results = json.dumps(eval("self.graph."+urllib.unquote(q)), sort_keys=True, indent=4)

            # escape angle brackets. don't escape ampersands since
            # they appear in urls that we want to use as link targets
            results = results.replace("<", "&lt;").replace(">", "&gt;")

            # unescape forward slashes in urls
            results = results.replace(r"\/", "/")

            #wrap anchor tags:
            #XXX: It is possible to proxy all of these links back through the server so that all responses
            #     have id values and hyperlinks wrapped. As it's written right now, however, requests are not
            #     proxied which means that respones returned directly from Facebook will not contain clickable links.
            #     Another possibility is to write a GreaseMonkey script, browser extension, or bookmarklet to do this 
            #     client-side in the browser

            # wrap links in anchor tags
            results = re.sub('"(http[^"]*)', lambda m: '"<a href="%s" target="_blank">%s</a>' % ((m.groups()[0],)*2), results)

            # wrap id values in anchor tags
            results = re.sub('"id": "([\d_]+)"', lambda m: '"id": "<a href="/query?q=' + urllib.quote('get_object(\"%s\",metadata=1)' % (m.groups()[0],)) + '" target="_blank">%s</a>"' % (m.groups()[0],), results)

            return results
        except facebook.GraphAPIError, e:
            return str(e)

    def do_fql_query(self, q):
        fql = FQL(self.current_user.access_token)
        return json.dumps(fql(query=urllib.unquote(q)), sort_keys=True, indent=4)

    def do_fql_multiquery(self, q):
        fql = FQL(self.current_user.access_token)
        return json.dumps(fql.multi(queries=json.loads(urllib.unquote(q))), sort_keys=True, indent=4)

    def get(self):
        path = os.path.join(os.path.dirname(__file__), "query.html")
        args = self.request.GET.copy()
        q = args.get('q')
        args.update(access_token=self.current_user.access_token)

        if q:
            q = q.strip()
            try:
                results = self.do_graph_query(q)
            except Exception, e:
                results = "Unhandled Exception: " + str(e)

            args.update(dict(results=results))
        self.response.out.write(template.render(path, args))

    def post(self):
        path = os.path.join(os.path.dirname(__file__), "query.html")
        args = self.request.POST.copy()
        q = args.get('q')
        args.update(access_token=self.current_user.access_token)

        if q:
            q = q.strip()
            try:
                if q.startswith("{"):
                    results = self.do_fql_multiquery(q)
                elif q.lower().startswith("select"):
                    results = self.do_fql_query(q)
                else:
                    results = self.do_graph_query(q)
            except Exception, e:
                results = "Unhandled Exception: " + str(e)

        else:
            results = "No query provided"

        args.update(dict(results=results))
        self.response.out.write(template.render(path, args))


def set_cookie(response, name, value, domain=None, path="/", expires=None):
    """Generates and signs a cookie for the give name/value"""
    timestamp = str(int(time.time()))
    value = base64.b64encode(value)
    signature = cookie_signature(value, timestamp)
    cookie = Cookie.BaseCookie()
    cookie[name] = "|".join([value, timestamp, signature])
    cookie[name]["path"] = path
    if domain: cookie[name]["domain"] = domain
    if expires:
        cookie[name]["expires"] = email.utils.formatdate(
            expires, localtime=False, usegmt=True)
    response.headers._headers.append(("Set-Cookie", cookie.output()[12:]))


def parse_cookie(value):
    """Parses and verifies a cookie value from set_cookie"""
    if not value: return None
    parts = value.split("|")
    if len(parts) != 3: return None
    if cookie_signature(parts[0], parts[1]) != parts[2]:
        logging.warning("Invalid cookie signature %r", value)
        return None
    timestamp = int(parts[1])
    if timestamp < time.time() - 30 * 86400:
        logging.warning("Expired cookie %r", value)
        return None
    try:
        return base64.b64decode(parts[0]).strip()
    except:
        return None


def cookie_signature(*parts):
    """Generates a cookie signature.

    We use the Facebook app secret since it is different for every app (so
    people using this example don't accidentally all use the same secret).
    """
    hash = hmac.new(FACEBOOK_APP_SECRET, digestmod=hashlib.sha1)
    for part in parts: hash.update(part)
    return hash.hexdigest()


def main():
    util.run_wsgi_app(webapp.WSGIApplication([
        (r"/", HomeHandler),
        (r"/auth/login", LoginHandler),
        (r"/auth/logout", LogoutHandler),
        (r"/query", QueryHandler),
    ], debug=True))


if __name__ == "__main__":
    main()
