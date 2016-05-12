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
            TABLE {width: 100%%; text-align: left;}
            TH {text-align:center;}
        </style>
    </head>
    <body>
        <table border=0><tbody>
        <tr>
            <th>Upload Date</th>
            <th>Tags</th>
            <th>Duration</th>
            <th>&nbsp;</th>
            <th>&nbsp;</th>
        </tr>
%s
        </tbody></table>
    </body>
</html>
"""


class RecordingsAPI(webapp2.RequestHandler):

    def post(self):
        tags = clean_tags(self.request.get('tags'))
        if not tags:
            api.write_error(self.response, 400, 'Missing required parameter: tags')
            return

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
        filename = config.RECORDINGS_BUCKET + recording_id

        gcs_file = gcs.open(filename, mode='w', content_type=uploaded_file.type)
        gcs_file.write(uploaded_file.file.read())
        gcs_file.close()

        stat = gcs.stat(filename)
        recording = Recording(uuid=recording_id, tags=tags,
                              duration=stat.st_size / config.SAMPLES_PER_SEC)
        recording.put_async()

        api.write_message(self.response, 'success')


    def get(self):
        recording_id = self.request.get('id')
        start = self.request.get('start')
        end = self.request.get('end')
        flip = self.request.get('flip')
        grid = self.request.get('grid')

        if not recording_id:
            api.write_error(self.response, 400, 'Missing required parameter: id')
            return

        filename = config.RECORDINGS_BUCKET + recording_id
        data = read(filename)

        if start and end:
            start_index = int(start) * config.SAMPLES_PER_SEC
            end_index = int(end) * config.SAMPLES_PER_SEC
            data = data[start_index:end_index]
        elif start:
            start_index = int(start) * config.SAMPLES_PER_SEC
            end_index = (int(start) + 10) * config.SAMPLES_PER_SEC
            data = data[start_index:end_index]

        if flip:
            data = [(255 - value) for value in data]

        figure = get_figure(data, grid)

        output = StringIO.StringIO()
        figure.savefig(output, dpi=100, orientation='landscape', format='png', transparent=True,
                       frameon=False, bbox_inches='tight', pad_inches=0)

        self.response.headers['Content-Type'] = 'image/png'
        self.response.out.write(output.getvalue())
        output.close()


class RecordingsListAPI(webapp2.RequestHandler):

    def get(self):

        output = ''
        for recording in Recording.query().order(-Recording.create_time):
            output += '<tr>'
            output += '<td>%s</td>' % (recording.create_time.strftime('%c'))
            output += '<td>%s</td>' % (', '.join(recording.tags))
            output += '<td>%d seconds</td>' % (recording.duration)
            output += '<td><a href="/recording?id=%s&start=0&end=10">Chart</a></td>' % (recording.uuid)
            output += '<td><a href="/recording/download?id=%s">Download</a></td>' % (recording.uuid)
            output += '</tr>'

        self.response.headers['Content-Type'] = 'text/html'
        self.response.out.write(LIST_TEMPLATE % (output))


class RecordingsDownloadAPI(webapp2.RequestHandler):

    def get(self):
        recording_id = self.request.get('id')
        if not recording_id:
            api.write_error(self.response, 400, 'Missing required parameter: id')
            return

        filename = config.RECORDINGS_BUCKET + recording_id
        data = read(filename)

        recording = Recording.query(Recording.uuid == recording_id).get()
        filename = str(' '.join(recording.tags)) + '.raw'

        self.response.headers['Content-Type'] = 'application/binary'
        self.response.headers['Content-Disposition'] = 'attachment; filename="%s"' % (filename)
        self.response.out.write(data)


def get_figure(ydata, show_grid=False):
    fig = pyplot.figure(figsize=(15, 6))
    ax = fig.add_subplot(1, 1, 1)

    ax.set_xticklabels([])
    ax.set_yticklabels([])
    if show_grid:
        ax.set_xticks(np.arange(0, len(ydata), 8), minor=True)
        ax.set_xticks(np.arange(0, len(ydata), 40))

        ax.set_yticks(np.arange(0, 275, 25))
        ax.set_yticks(np.arange(0, 275, 5), minor=True)

    ax.plot(ydata, linewidth=1)
    ax.axis([0, len(ydata), 0, 275])

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

def clean_tags(tagstr):
    tags = []
    if not tagstr:
        return tags
    for tag in tagstr.lower().split(','):
        tag = tag.strip()
        if tag:
            tags.append(tag)
    return tags

