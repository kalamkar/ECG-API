'''
Created on Apr 26, 2016

@author: abhi
'''

import api
import config
import cloudstorage as gcs
import numpy as np
import StringIO
import uuid
import webapp2

from matplotlib import pyplot
from datastore import Recording

LIST_TEMPLATE = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
        "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
    <head>
        <title>Dovetail Data</title>
        <style type="text/css">
            BODY {font-family: sans-serif; text-align:center;}
        </style>
    </head>
    <body>
        <table border=0><tbody>
%s
        </tbody></table>
    </body>
</html>
"""


class RecordingsAPI(webapp2.RequestHandler):

    def post(self):
        tagstr = self.request.get('tags')
        if not tagstr:
            api.write_error(self.response, 400, 'Missing required parameter: tags')
            return

        tags = tagstr.lower().split(',')
        tags.append(api.get_geo_name(self.request))

        try:
            uploaded_file = self.request.POST['file']
            if not uploaded_file.type:
                api.write_error(self.response, 400, 'Missing content type')
                return
        except:
            uploaded_file = None

        if uploaded_file == None:
            api.write_error(self.response, 400, 'Missing content')
            return

        recording_id = str(uuid.uuid4())
        recording = Recording(uuid=recording_id, tags=tags)
        recording.put_async()

        filename = config.RECORDINGS_BUCKET + recording_id
        gcs_file = gcs.open(filename, mode='w', content_type=uploaded_file.type)
        gcs_file.write(uploaded_file.file.read())
        gcs_file.close()

        api.write_message(self.response, 'success')


    def get(self):
        recording_id = self.request.get('id')
        start = self.request.get('start')
        end = self.request.get('end')

        if not recording_id:
            api.write_error(self.response, 400, 'Missing required parameter: id')
            return

        filename = config.RECORDINGS_BUCKET + recording_id
        data = read(filename)

        if start and end:
            data = data[int(start) * 1000:int(end) * 1000]
        elif start:
            data = data[int(start) * 1000:(int(start) + 5) * 1000]

        figure = get_figure(data)

        output = StringIO.StringIO()
        figure.savefig(output, dpi=100, orientation='landscape', format='png', transparent=True,
                       frameon=False, bbox_inches='tight', pad_inches=0)

        self.response.headers['Content-Type'] = 'image/png'
        self.response.out.write(output.getvalue())
        output.close()


class RecordingsListAPI(webapp2.RequestHandler):

    def get(self):

        output = ''
        for recording in Recording.query():
            output = output + '<tr>'
            output = output + '<td>%s</td>' % (str(recording.create_time))
            output = output + '<td>%s</td>' % (','.join(recording.tags))
            output = output + '<td><a href="/recording?id=%s&start=0&end=5">Chart</a></td>' % (recording.uuid)
            output = output + '</tr>'

        self.response.headers['Content-Type'] = 'text/html'
        self.response.out.write(LIST_TEMPLATE % (output))


def get_figure(ydata):
    fig = pyplot.figure(figsize=(15, 6))
    ax = fig.add_subplot(1, 1, 1)

    ax.set_xticks(np.arange(0, len(ydata), 40), minor=True)
    ax.set_xticks(np.arange(0, len(ydata), 200))
    ax.set_xticklabels([])

    ax.set_yticks(np.arange(0, 255, 25))
    ax.set_yticks(np.arange(0, 255, 5), minor=True)
    ax.set_yticklabels([])

    ax.plot(ydata, linewidth=1)

    ax.grid(which='both', color='r', linestyle='-')
    ax.grid(which='minor', alpha=0.2)
    ax.grid(which='major', alpha=0.5)
    return fig


def read(filename):
    data = []
    gcs_file = gcs.open(filename)
    buff = gcs_file.read()
    gcs_file.close()
    for byte in buff:
        data.append(ord(byte))
    return data


