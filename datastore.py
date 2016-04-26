'''
Created on Apr 26, 2016

@author: abhi
'''

from google.appengine.ext import ndb


# Top level object representing an ECG recording
class Recording(ndb.Model):
    uuid = ndb.StringProperty()
    tags = ndb.StringProperty(repeated=True)
    create_time = ndb.DateTimeProperty(auto_now_add=True)

