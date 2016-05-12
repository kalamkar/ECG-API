'''
Created on Apr 26, 2016

@author: abhi
'''

import webapp2
from google.appengine.ext import ndb

from recording import RecordingsAPI
from recording import RecordingsDownloadAPI
from recording import RecordingsListAPI

app = ndb.toplevel(webapp2.WSGIApplication([
    ('/recording', RecordingsAPI),
    ('/recording/list', RecordingsListAPI),
    ('/recording/download', RecordingsDownloadAPI)
], debug=False))