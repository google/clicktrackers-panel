# Copyright 2017 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Exposes a HTTP API from performing operations on click-tracking ads in DCM.

Supports hosting on GAE Standard.
"""

from datetime import datetime
from datetime import timedelta
import json
import logging
import os
from urlparse import urlparse
from googleapiclient import discovery
from googleapiclient.errors import HttpError
import jinja2
from oauth2client.contrib import appengine
import webapp2
from google.appengine.api import urlfetch

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    autoescape=True,
    extensions=['jinja2.ext.autoescape'])

# Client should download the credentials and deploy them with the code
# We could use KMS or Datastore, but let's keep it simple for now
CLIENT_SECRETS = os.path.join(os.path.dirname(__file__), 'client_secrets.json')

API_NAME = 'dfareporting'
API_VERSION = 'v2.8'
API_SCOPES = ['https://www.googleapis.com/auth/dfatrafficking']

TIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'

decorator = appengine.oauth2decorator_from_clientsecrets(
    CLIENT_SECRETS, scope=API_SCOPES)

service = discovery.build(API_NAME, API_VERSION)


class MainHandler(webapp2.RequestHandler):

  @decorator.oauth_required
  def get(self):
    credentials = decorator.get_credentials()
    if credentials.access_token_expired:
      credentials.refresh(decorator.http())
    template = JINJA_ENVIRONMENT.get_template('templates/index.html')
    self.response.write(template.render())


class ProfilesHandler(webapp2.RequestHandler):

  @decorator.oauth_required
  def get(self):
    resp = service.userProfiles().list().execute(http=decorator.http())
    self.response.write(json.dumps({'profiles': resp['items']}))


class PlacementsHandler(webapp2.RequestHandler):
  """Handles placement lookup (GET) and click-tracker creation (POST)."""

  @decorator.oauth_required
  def get(self, profile_id, placement_id):
    try:
      http = decorator.http()
      resp = service.placements().get(
          profileId=profile_id, id=placement_id).execute(http=http)
      logging.debug(resp)
      self.response.write(json.dumps({'placement': resp}))
    except HttpError as err:
      upstream_error = json.loads(err.content)['error']
      logging.error(upstream_error)
      resp = {
          'code': upstream_error['code'],
          'message': upstream_error['message']
      }
      self.response.set_status(resp['code'])
      self.response.write(json.dumps(resp))

  @decorator.oauth_required
  def post(self, profile_id, placement_id):
    data = json.loads(self.request.body)
    http = decorator.http()
    placement = service.placements().get(
        profileId=profile_id, id=placement_id).execute(http=http)
    one_year = datetime.now() + timedelta(days=365)
    tracker_urls = {}
    for t in data['trackers']:
      url = urlparse(t['url'])
      ad = service.ads().insert(
          profileId=profile_id,
          body={
              'advertiserId':
                  placement['advertiserId'],
              'campaignId':
                  placement['campaignId'],
              'placementId':
                  placement_id,
              'type':
                  'AD_SERVING_CLICK_TRACKER',
              'clickThroughUrl': {
                  'customClickThroughUrl': url.geturl(),
                  'defaultLandingPage': False
              },
              'name':
                  t['name'],
              'active':
                  True,
              'dynamicClickTracker':
                  True,
              'startTime': (datetime.now() + timedelta(seconds=3))
                           .strftime(TIME_FORMAT),
              'endTime':
                  one_year.strftime(TIME_FORMAT),
              'placementAssignments': [{
                  'placementId': placement_id,
                  'active': True
              }]
          }).execute(http=http)
      tracker_urls[ad['id']] = {'name': t['name']}
    # increase timeout for tag generation
    urlfetch.set_default_fetch_deadline(30)
    tags = service.placements().generatetags(
        profileId=profile_id,
        campaignId=placement['campaignId'],
        placementIds=[placement_id],
        tagFormats=['PLACEMENT_TAG_CLICK_COMMANDS']).execute(http=http)
    for pt in tags['placementTags']:
      if pt['placementId'] == placement_id:
        for td in pt['tagDatas']:
          if td['adId'] in tracker_urls:
            tracker_urls[td['adId']]['clickUrl'] = td['clickTag']
    resp = json.dumps({'uploaded': tracker_urls})
    logging.debug(resp)
    self.response.write(resp)


app = webapp2.WSGIApplication(
    [
        ('/', MainHandler),
        (r'/profiles', ProfilesHandler),
        (r'/profiles/(\d+)/placements/(\d+)', PlacementsHandler),
        (decorator.callback_path, decorator.callback_handler()),
    ],
    debug=True)
