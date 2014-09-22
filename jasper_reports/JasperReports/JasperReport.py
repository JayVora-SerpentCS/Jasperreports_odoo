# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2008-2012 NaN Projectes de Programari Lliure, S.L.
#                         http://www.NaN-tic.com
# Copyright (C) 2013 Tadeus Prastowo <tadeus.prastowo@infi-nity.com>
#                         Vikasa Infinity Anugrah <http://www.infi-nity.com>
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

import os
from lxml import etree
import re

try:
    import release
    from tools.safe_eval import safe_eval
    import tools
except ImportError:
    import openerp
    from openerp import release
    from openerp.tools.safe_eval import safe_eval
    from openerp import tools

dataSourceExpressionRegExp = re.compile( r"""\$P\{(\w+)\}""" )

class JasperReport:
    def __init__(self, fileName='', pathPrefix=''):
        self._reportPath = fileName
        self._pathPrefix = pathPrefix.strip()
        if self._pathPrefix and self._pathPrefix[-1] != '/':
            self._pathPrefix += '/'

        self._language = 'xpath'
        self._relations = []
        self._fields = {}
        self._fieldNames = []
        self._subreports = []
        self._datasets = []
        self._copies = 1
        self._copiesField = False
        self._isHeader = False
        if fileName:
            self.extractProperties()

    def language(self):
        return self._language

    def fields(self):
        return self._fields

    def fieldNames(self):
        return self._fieldNames

    def subreports(self):
        return self._subreports

    def datasets(self):
        return self._datasets

    def relations(self):
        return self._relations

    def copiesField(self):
        return self._copiesField

    def copies(self):
        return self._copies

    def isHeader(self):
        return self._isHeader

    def subreportDirectory(self):
        return os.path.join( os.path.abspath(os.path.dirname( self._reportPath )), '' )

    def standardDirectory(self):
        jasperdir = tools.config.get('jasperdir')
        if jasperdir:
            if jasperdir.endswith( os.sep ):
                return jasperdir
            else:
                return os.path.join( jasperdir, '' )
        return os.path.join( os.path.abspath(os.path.dirname(__file__)), '..', 'report', '' )

    def extractFields(self, fieldTags, ns):
        # fields and fieldNames
        fields = {}
        fieldNames = []
        #fieldTags = doc.xpath( '/jr:jasperReport/jr:field', namespaces=nss )
        for tag in fieldTags:
            name = tag.get('name')
            type = tag.get('class')
            children = tag.getchildren()
            path = tag.findtext('{%s}fieldDescription' % ns, '').strip()
            # Make the path relative if it isn't already
            if path.startswith('/data/record/'):
                path = self._pathPrefix + path[13:]
            # Remove language specific data from the path so:
            # Empresa-partner_id/Nom-name becomes partner_id/name
            # We need to consider the fact that the name in user's language
            # might not exist, hence the easiest thing to do is split and [-1]
            newPath = []
            for x in path.split('/'):
                newPath.append( x.split('-')[-1] )
            path = '/'.join( newPath )
            if path in fields:
                print "WARNING: path '%s' already exists in report. This is not supported by the module. Offending fields: %s, %s" % (path, fields[path]['name'], name)
            fields[ path ] = {
                'name': name,
                'type': type,
            }
            fieldNames.append( name )
        return fields, fieldNames

    def extractProperties(self):
        # The function will read all relevant information from the jrxml file

        doc = etree.parse( self._reportPath )

        # Define namespaces
        ns = 'http://jasperreports.sourceforge.net/jasperreports'
        nss = {'jr': ns}

        # Language

        # Note that if either queryString or language do not exist the default (from the constructor)
        # is XPath.
        langTags = doc.xpath( '/jr:jasperReport/jr:queryString', namespaces=nss )
        if langTags:
            if langTags[0].get('language'):
                self._language = langTags[0].get('language').lower()

        # Relations
        relationTags = doc.xpath( '/jr:jasperReport/jr:property[@name="OPENERP_RELATIONS"]', namespaces=nss )
        if relationTags and 'value' in relationTags[0].keys():
            relation = relationTags[0].get('value').strip()
            if relation.startswith('['):
                self._relations = safe_eval( relationTags[0].get('value'), {} )
            else:
                self._relations = [x.strip() for x in relation.split(',')]
            self._relations = [self._pathPrefix + x for x in self._relations]
        if not self._relations and self._pathPrefix:
            self._relations = [self._pathPrefix[:-1]]

        # Repeat field
        copiesFieldTags = doc.xpath( '/jr:jasperReport/jr:property[@name="OPENERP_COPIES_FIELD"]', namespaces=nss )
        if copiesFieldTags and 'value' in copiesFieldTags[0].keys():
            self._copiesField = self._pathPrefix + copiesFieldTags[0].get('value')

        # Repeat
        copiesTags = doc.xpath( '/jr:jasperReport/jr:property[@name="OPENERP_COPIES"]', namespaces=nss )
        if copiesTags and 'value' in copiesTags[0].keys():
            self._copies = int(copiesTags[0].get('value'))

        self._isHeader = False
        headerTags = doc.xpath( '/jr:jasperReport/jr:property[@name="OPENERP_HEADER"]', namespaces=nss )
        if headerTags and 'value' in headerTags[0].keys():
            self._isHeader = True

        fieldTags = doc.xpath( '/jr:jasperReport/jr:field', namespaces=nss )
        self._fields, self._fieldNames = self.extractFields( fieldTags, ns )

        # Subreports
        # Here we expect the following structure in the .jrxml file:
        #<subreport>
        #  <dataSourceExpression><![CDATA[$P{REPORT_DATA_SOURCE}]]></dataSourceExpression>
        #  <subreportExpression class="java.lang.String"><![CDATA[$P{STANDARD_DIR} + "report_header.jasper"]]></subreportExpression>
        #</subreport>
        subreportTags = doc.xpath( '//jr:subreport', namespaces=nss )
        for tag in subreportTags:
            dataSourceExpression = tag.findtext('{%s}dataSourceExpression' % ns, '')
            if not dataSourceExpression:
                continue
            dataSourceExpression = dataSourceExpression.strip()
            m = dataSourceExpressionRegExp.match( dataSourceExpression )
            if not m:
                continue
            dataSourceExpression = m.group(1)
            if dataSourceExpression == 'REPORT_DATA_SOURCE':
                continue

            subreportExpression = tag.findtext('{%s}subreportExpression' % ns, '')
            if not subreportExpression:
                continue
            subreportExpression = subreportExpression.strip()
            subreportExpression = subreportExpression.replace('$P{STANDARD_DIR}', '"%s"' % self.standardDirectory() )
            subreportExpression = subreportExpression.replace('$P{SUBREPORT_DIR}', '"%s"' % self.subreportDirectory() )
            try:
                subreportExpression = safe_eval( subreportExpression, {} )
            except:
                print "COULD NOT EVALUATE EXPRESSION: '%s'" % subreportExpression
                # If we're not able to evaluate the expression go to next subreport
                continue
            if subreportExpression.endswith('.jasper'):
                subreportExpression = subreportExpression[:-6] + 'jrxml'

            # Model
            model = ''
            modelTags = tag.xpath( '//jr:reportElement/jr:property[@name="OPENERP_MODEL"]', namespaces=nss )
            if modelTags and 'value' in modelTags[0].keys():
                model = modelTags[0].get('value')

            pathPrefix = ''
            pathPrefixTags = tag.xpath( '//jr:reportElement/jr:property[@name="OPENERP_PATH_PREFIX"]', namespaces=nss )
            if pathPrefixTags and 'value' in pathPrefixTags[0].keys():
                pathPrefix = pathPrefixTags[0].get('value')

            isHeader = False
            headerTags = tag.xpath( '//jr:reportElement/jr:property[@name="OPENERP_HEADER"]', namespaces=nss )
            if headerTags and 'value' in headerTags[0].keys():
                isHeader = True

            # Add our own pathPrefix to subreport's pathPrefix
            subPrefix = []
            if self._pathPrefix:
                subPrefix.append( self._pathPrefix )
            if pathPrefix:
                subPrefix.append( pathPrefix )
            subPrefix = '/'.join( subPrefix )

            subreport = JasperReport( subreportExpression, subPrefix )
            self._subreports.append({
                'parameter': dataSourceExpression,
                'filename': subreportExpression,
                'model': model,
                'pathPrefix': pathPrefix,
                'report': subreport,
                'depth': 1,
            })
            for subsubInfo in subreport.subreports():
                subsubInfo['depth'] += 1
                # Note hat 'parameter' (the one used to pass report's DataSource) must be
                # the same in all reports
                self._subreports.append( subsubInfo )

        # Dataset
        # Here we expect the following structure in the .jrxml file:
        #<datasetRun>
        #  <dataSourceExpression><![CDATA[$P{REPORT_DATA_SOURCE}]]></dataSourceExpression>
        #</datasetRun>
        datasetTags = doc.xpath( '//jr:datasetRun', namespaces=nss )
        for tag in datasetTags:
            dataSourceExpression = tag.findtext('{%s}dataSourceExpression' % ns, '')
            if not dataSourceExpression:
                continue
            dataSourceExpression = dataSourceExpression.strip()
            m = dataSourceExpressionRegExp.match( dataSourceExpression )
            if not m:
                continue
            dataSourceExpression = m.group(1)
            if dataSourceExpression == 'REPORT_DATA_SOURCE':
                continue
            subDatasetName = tag.get('subDataset')
            if not subDatasetName:
                continue

            # Relations
            relations = []
            relationTags = tag.xpath( '../../jr:reportElement/jr:property[@name="OPENERP_RELATIONS"]', namespaces=nss )
            if relationTags and 'value' in relationTags[0].keys():
                relation = relationTags[0].get('value').strip()
                if relation.startswith('['):
                    relations = safe_eval( relationTags[0].get('value'), {} )
                else:
                    relations = [x.strip() for x in relation.split(',')]
                relations = [self._pathPrefix + x for x in relations]
            if not relations and self._pathPrefix:
                relations = [self._pathPrefix[:-1]]

            # Repeat field
            copiesField = None
            copiesFieldTags = tag.xpath( '../../jr:reportElement/jr:property[@name="OPENERP_COPIES_FIELD"]', namespaces=nss )
            if copiesFieldTags and 'value' in copiesFieldTags[0].keys():
                copiesField = self._pathPrefix + copiesFieldTags[0].get('value')

            # Repeat
            copies = None
            copiesTags = tag.xpath( '../../jr:reportElement/jr:property[@name="OPENERP_COPIES"]', namespaces=nss )
            if copiesTags and 'value' in copiesTags[0].keys():
                copies = int(copiesTags[0].get('value'))

            # Model
            model = ''
            modelTags = tag.xpath( '../../jr:reportElement/jr:property[@name="OPENERP_MODEL"]', namespaces=nss )
            if modelTags and 'value' in modelTags[0].keys():
                model = modelTags[0].get('value')

            pathPrefix = ''
            pathPrefixTags = tag.xpath( '../../jr:reportElement/jr:property[@name="OPENERP_PATH_PREFIX"]', namespaces=nss )
            if pathPrefixTags and 'value' in pathPrefixTags[0].keys():
                pathPrefix = pathPrefixTags[0].get('value')

            # We need to find the appropriate subDataset definition for this dataset run.
            subDataset = doc.xpath( '//jr:subDataset[@name="%s"]' % subDatasetName, namespaces=nss )[0]
            fieldTags = subDataset.xpath( 'jr:field', namespaces=nss )
            fields, fieldNames = self.extractFields( fieldTags, ns )

            dataset = JasperReport()
            dataset._fields = fields
            dataset._fieldNames = fieldNames
            dataset._relations = relations
            dataset._copiesField = copiesField
            dataset._copies = copies
            self._subreports.append({
                'parameter': dataSourceExpression,
                'model': model,
                'pathPrefix': pathPrefix,
                'report': dataset,
                'filename': 'DATASET',
            })

# vim:noexpandtab:smartindent:tabstop=8:softtabstop=8:shiftwidth=8:
