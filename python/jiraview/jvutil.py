# -*- coding: utf-8 -*- #
from __future__ import unicode_literals

import csv
import cStringIO
import codecs

UTF8 = 'utf-8'

class Utf8CsvDictWriter:
    def __init__(self, csv_file, columns):
        self.current_line = cStringIO.StringIO()
        self.writer = csv.DictWriter(self.current_line, columns, restval = 'NA', dialect = 'excel')
        self.stream = csv_file
        self.encoder = codecs.getincrementalencoder(UTF8)()

        self.writer.writeheader()

    def writerow(self, row):
        self.writer.writerow( { k : unicode(v).encode('utf-8') if v != None else u'NA'.encode('utf-8') for k,v in row.items() } )
        self.stream.write(self.current_line.getvalue())
        self.current_line.truncate(0)
