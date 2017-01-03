# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2008-2012 NaN Projectes de Programari Lliure, S.L.
#                         http://www.NaN-tic.com
# Copyright (C) 2011-Today Serpent Consulting Services Pvt. Ltd.
#                         (<http://www.serpentcs.com>)
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

import csv
import codecs
<<<<<<< HEAD:jasper_reports/JasperReports/record_data_generator.py
from xml.dom.minidom import getDOMImplementation

from .abstract_data_generator import AbstractDataGenerator
=======
from . AbstractDataGenerator import AbstractDataGenerator
>>>>>>> upstream/10.0:jasper_reports/JasperReports/RecordDataGenerator.py


class CsvRecordDataGenerator(AbstractDataGenerator):

    def __init__(self, report, records):
        self.report = report
        self.records = records
        self.temporaryFiles = []

    # CSV file generation using a list of dictionaries provided by
    # the parser function.
<<<<<<< HEAD:jasper_reports/JasperReports/record_data_generator.py
    def generate(self, file_name):

        with open(file_name, 'wb+') as f:
            csv.QUOTE_ALL = True
            field_names = self.report.field_names
            # JasperReports CSV reader requires an extra colon
            # at the end of the line.
            writer = csv.DictWriter(f, field_names + [''], delimiter=',',
                                    quotechar='"')
            header = {}

            for field in field_names + ['']:
                header[field] = field

=======
    def generate(self, fileName):
        f = open(fileName, 'wb+')
        try:
            csv.QUOTE_ALL = True
            fieldNames = self.report.fieldNames()
            # JasperReports CSV reader requires an extra colon
            # at the end of the line.
            writer = csv.DictWriter(f, fieldNames + [''], delimiter=',',
                                    quotechar='"')
            header = {}
            for field in fieldNames + ['']:
                header[field] = field
>>>>>>> upstream/10.0:jasper_reports/JasperReports/RecordDataGenerator.py
            writer.writerow(header)
            error_reported_fields = []

            for record in self.records:

                row = {}
                for field in record:
<<<<<<< HEAD:jasper_reports/JasperReports/record_data_generator.py
                    if field not in self.report.fields:
=======
                    if field not in self.report.fields():
>>>>>>> upstream/10.0:jasper_reports/JasperReports/RecordDataGenerator.py
                        if field not in error_reported_fields:
                            error_reported_fields.append(field)
                        continue

                    value = record.get(field, False)
<<<<<<< HEAD:jasper_reports/JasperReports/record_data_generator.py

=======
>>>>>>> upstream/10.0:jasper_reports/JasperReports/RecordDataGenerator.py
                    if value is False:
                        value = ''
                    elif isinstance(value, unicode):
                        value = value.encode('utf-8')
                    elif isinstance(value, float):
                        value = '%.10f' % value
                    elif not isinstance(value, str):
                        value = str(value)
<<<<<<< HEAD:jasper_reports/JasperReports/record_data_generator.py
                    row[self.report.fields[field]['name']] = value

                writer.writerow(row)
=======
                    row[self.report.fields()[field]['name']] = value
                writer.writerow(row)
        finally:
            f.close()
>>>>>>> upstream/10.0:jasper_reports/JasperReports/RecordDataGenerator.py


class XmlRecordDataGenerator(AbstractDataGenerator):

<<<<<<< HEAD:jasper_reports/JasperReports/record_data_generator.py
    def __init__(self):
        super(XmlRecordDataGenerator, self).__init__()
        self.document = None

    # XML file generation using a list of dictionaries provided by
    # the parser function.
    def generate(self, file_name):

        # Once all records have been calculated, create the XML structure
        self.document = getDOMImplementation().createDocument(None, 'data',
                                                              None)
        top_node = self.document.documentElement

        for record in self.data['records']:
            record_node = self.document.createElement('record')
            top_node.appendChild(record_node)

            for field, value in record.iteritems():
                field_node = self.document.createElement(field)
                record_node.appendChild(field_node)
=======
    # XML file generation using a list of dictionaries provided by
    # the parser function.
    def generate(self, fileName):
        # Once all records have been calculated, create the XML structure
        self.document = getDOMImplementation().createDocument(None, 'data',
                                                              None)
        topNode = self.document.documentElement
        for record in self.data['records']:
            recordNode = self.document.createElement('record')
            topNode.appendChild(recordNode)
            for field, value in record.iteritems():
                fieldNode = self.document.createElement(field)
                recordNode.appendChild(fieldNode)
>>>>>>> upstream/10.0:jasper_reports/JasperReports/RecordDataGenerator.py
                # The rest of field types must be converted into str
                if value is False:
                    value = ''
                elif isinstance(value, str):
                    value = unicode(value, 'utf-8')
                elif isinstance(value, float):
                    value = '%.10f' % value
                elif not isinstance(value, unicode):
                    value = unicode(value)
<<<<<<< HEAD:jasper_reports/JasperReports/record_data_generator.py
=======
                valueNode = self.document.createTextNode(value)
                fieldNode.appendChild(valueNode)
        # Once created, the only missing step is to store the XML into a file
        f = codecs.open(fileName, 'wb+', 'utf-8')
        try:
            topNode.writexml(f)
        finally:
            f.close()
>>>>>>> upstream/10.0:jasper_reports/JasperReports/RecordDataGenerator.py

                value_node = self.document.createTextNode(value)
                field_node.appendChild(value_node)

        # Once created, the only missing step is to store the XML into a file
        with codecs.open(file_name, 'wb+', 'utf-8') as f:
            top_node.writexml(f)
