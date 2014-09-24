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


import openerp
from openerp import release
from openerp import report
from openerp import pooler
from openerp.osv import orm, osv, fields
from openerp import tools
from openerp import netsvc

import os
import tempfile
import logging

from JasperReports import *

# Determines the port where the JasperServer process should listen with its XML-RPC server for incomming calls
tools.config['jasperport'] = tools.config.get('jasperport', 8090)

# Determines the file name where the process ID of the JasperServer process should be stored
tools.config['jasperpid'] = tools.config.get('jasperpid', 'openerp-jasper.pid')

# Determines if temporary files will be removed
tools.config['jasperunlink'] = tools.config.get('jasperunlink', True)

class Report:
    def __init__(self, name, cr, uid, ids, data, context):
        self.name = name
        self.cr = cr
        self.uid = uid
        self.ids = ids
        self.data = data
        self.model = self.data.get('model', False) or context.get('active_model', False)
        self.context = context or {}
        self.pool = pooler.get_pool(self.cr.dbname)
        self.reportPath = None
        self.report = None
        self.temporaryFiles = []
        self.outputFormat = 'pdf'

    def execute(self):
        """
        If self.context contains "return_pages = True" it will return the number of pages
        of the generated report.
        """
        logger = logging.getLogger(__name__)

        # * Get report path *
        # Not only do we search the report by name but also ensure that 'report_rml' field
        # has the '.jrxml' postfix. This is needed because adding reports using the <report/>
        # tag, doesn't remove the old report record if the id already existed (ie. we're trying
        # to override the 'purchase.order' report in a new module). As the previous record is
        # not removed, we end up with two records named 'purchase.order' so we need to destinguish
        # between the two by searching '.jrxml' in report_rml.
        ids = self.pool.get('ir.actions.report.xml').search(self.cr, self.uid, [('report_name', '=', self.name[7:]), ('report_rml', 'ilike', '.jrxml')], context=self.context)
        data = self.pool.get('ir.actions.report.xml').read(self.cr, self.uid, ids[0], ['report_rml', 'jasper_output'])
        if data['jasper_output']:
            self.outputFormat = data['jasper_output']
        self.reportPath = data['report_rml']
        self.reportPath = os.path.join(self.addonsPath(), self.reportPath)
        if not os.path.lexists(self.reportPath):
            self.reportPath = self.addonsPath(path=data['report_rml'])

        # Get report information from the jrxml file
        logger.info("Requested report: '%s'" % self.reportPath)
        self.report = JasperReport(self.reportPath)

        # Create temporary input (XML) and output (PDF) files
        fd, dataFile = tempfile.mkstemp()
        os.close(fd)
        fd, outputFile = tempfile.mkstemp()
        os.close(fd)
        self.temporaryFiles.append(dataFile)
        self.temporaryFiles.append(outputFile)
        logger.info("Temporary data file: '%s'" % dataFile)

        import time
        start = time.time()

        # If the language used is xpath create the xmlFile in dataFile.
        if self.report.language() == 'xpath':
            if self.data.get('data_source', 'model') == 'records':
                generator = CsvRecordDataGenerator(self.report, self.data['records'])
            else:
                generator = CsvBrowseDataGenerator(self.report, self.model, self.pool, self.cr, self.uid, self.ids, self.context)
            generator.generate(dataFile)
            self.temporaryFiles += generator.temporaryFiles

        subreportDataFiles = []
        for subreportInfo in self.report.subreports():
            subreport = subreportInfo['report']
            if subreport.language() == 'xpath':
                message = 'Creating CSV '
                if subreportInfo['pathPrefix']:
                    message += 'with prefix %s ' % subreportInfo['pathPrefix']
                else:
                    message += 'without prefix '
                message += 'for file %s' % subreportInfo['filename']
                logger.info("%s" % message)

                fd, subreportDataFile = tempfile.mkstemp()
                os.close(fd)
                subreportDataFiles.append({
                    'parameter': subreportInfo['parameter'],
                    'dataFile': subreportDataFile,
                    'jrxmlFile': subreportInfo['filename'],
                })
                self.temporaryFiles.append(subreportDataFile)

                if subreport.isHeader():
                    generator = CsvBrowseDataGenerator(subreport, 'res.users', self.pool, self.cr, self.uid, [self.uid], self.context)
                elif self.data.get('data_source', 'model') == 'records':
                    generator = CsvRecordDataGenerator(subreport, self.data['records'])
                else:
                    generator = CsvBrowseDataGenerator(subreport, self.model, self.pool, self.cr, self.uid, self.ids, self.context)
                generator.generate(subreportDataFile)


        # Call the external java application that will generate the PDF file in outputFile
        pages = self.executeReport(dataFile, outputFile, subreportDataFiles)
        elapsed = (time.time() - start) / 60
        logger.info("ELAPSED: %f" % elapsed)

        # Read data from the generated file and return it
        f = open(outputFile, 'rb')
        try:
            data = f.read()
        finally:
            f.close()

        # Remove all temporary files created during the report
        if tools.config['jasperunlink']:
            for file in self.temporaryFiles:
                try:
                    os.unlink(file)
                except os.error, e:
                    logger.warning("Could not remove file '%s'." % file)
        self.temporaryFiles = []

        if self.context.get('return_pages'):
            return (data, self.outputFormat, pages)
        else:
            return (data, self.outputFormat)

    def path(self):
        return os.path.abspath(os.path.dirname(__file__))

    def addonsPath(self, path=False):
        if path:
            report_module = path.split(os.path.sep)[0]
            for addons_path in tools.config['addons_path'].split(','):
                if os.path.lexists(addons_path + os.path.sep + report_module):
                    return os.path.normpath(addons_path + os.path.sep + path)

        return os.path.dirname(self.path())

    def systemUserName(self):
        if os.name == 'nt':
            import win32api
            return win32api.GetUserName()
        else:
            import pwd
            return pwd.getpwuid(os.getuid())[0]

    def dsn(self):
        host = tools.config['db_host'] or 'localhost'
        port = tools.config['db_port'] or '5432'
        dbname = self.cr.dbname
        return 'jdbc:postgresql://%s:%s/%s' % (host, port, dbname)

    def userName(self):
        return tools.config['db_user'] or self.pool['ir.config_parameter'].get_param(self.cr, self.uid, 'db_user') or self.systemUserName()

    def password(self):
        
        return tools.config['db_password'] or self.pool['ir.config_parameter'].get_param(self.cr, self.uid, 'db_password') or ''

    def executeReport(self, dataFile, outputFile, subreportDataFiles):
        locale = self.context.get('lang', 'en_US')

        connectionParameters = {
            'output': self.outputFormat,
            # 'xml': dataFile,
            'csv': dataFile,
            'dsn': self.dsn(),
            'user': self.userName(),
            'password': self.password(),
            'subreports': subreportDataFiles,
        }
        parameters = {
            'STANDARD_DIR': self.report.standardDirectory(),
            'REPORT_LOCALE': locale,
            'IDS': self.ids,
        }
        if 'parameters' in self.data:
            parameters.update(self.data['parameters'])

        server = JasperServer(int(tools.config['jasperport']))
        server.setPidFile(tools.config['jasperpid'])
        return server.execute(connectionParameters, self.reportPath, outputFile, parameters)


class report_jasper(report.interface.report_int):
    def __init__(self, name, model, parser=None):
        # Remove report name from list of services if it already
        # exists to avoid report_int's assert. We want to keep the
        # automatic registration at login, but at the same time we
        # need modules to be able to use a parser for certain reports.
        if release.major_version == '5.0':
            if name in openerp.report.interface.report_int._reports:
                del openerp.report.interface.report_int._reports[name]
        else:
            if name in openerp.report.interface.report_int._reports:
                del openerp.report.interface.report_int._reports[name]
#             openerp.report.interface.report_int._reports[name] = 
        super(report_jasper, self).__init__(name)
        self.model = model
        self.parser = parser

    def create(self, cr, uid, ids, data, context):
        name = self.name
        if self.parser:
            d = self.parser(cr, uid, ids, data, context)
            ids = d.get('ids', ids)
            name = d.get('name', self.name)
            # Use model defined in report_jasper definition. Necesary for menu entries.
            data['model'] = d.get('model', self.model)
            data['records'] = d.get('records', [])
            # data_source can be 'model' or 'records' and lets parser to return
            # an empty 'records' parameter while still executing using 'records'
            data['data_source'] = d.get('data_source', 'model')
            data['parameters'] = d.get('parameters', {})
        r = Report(name, cr, uid, ids, data, context)
        # return ( r.execute(), 'pdf' )
        return r.execute()



if release.major_version == '5.0':
    # Version 5.0 specific code

    # Ugly hack to avoid developers the need to register reports
    import pooler
    import report

    def register_jasper_report(name, model):
        name = 'report.%s' % name
        # Register only if it didn't exist another "jasper_report" with the same name
        # given that developers might prefer/need to register the reports themselves.
        # For example, if they need their own parser.
        if name in openerp.report.interface.report_int._reports:
            if isinstance(openerp.report.interface.report_int._reports[name], report_jasper):
                return openerp.report.interface.report_int._reports[name]
            del openerp.report.interface.report_int._reports[name]
        report_jasper(name, model)


    # This hack allows automatic registration of jrxml files without
    # the need for developers to register them programatically.

    old_register_all = report.interface.register_all
    def new_register_all(db):
        value = old_register_all(db)

        cr = db.cursor()
        # Originally we had auto=true in the SQL filter but we will register all reports.
        cr.execute("SELECT * FROM ir_act_report_xml WHERE report_rml ilike '%.jrxml' ORDER BY id")
        records = cr.dictfetchall()
        cr.close()
        for record in records:
            register_jasper_report(record['report_name'], record['model'])
        return value

    report.interface.register_all = new_register_all

def register_jasper_report(report_name, model_name):
    name = 'report.%s' % report_name
    # Register only if it didn't exist another "jasper_report" with the same name
    # given that developers might prefer/need to register the reports themselves.
    # For example, if they need their own parser.
    if name in openerp.report.interface.report_int._reports:
        if isinstance(openerp.report.interface.report_int._reports[name], report_jasper):
            return openerp.report.interface.report_int._reports[name]
        del openerp.report.interface.report_int._reports[name]
    return report_jasper(name, model_name)

class ir_actions_report_xml(osv.osv):
    _inherit = 'ir.actions.report.xml'

    def _lookup_report(self, cr, name):
        """
        Look up a report definition.
        """
        opj = os.path.join
        # First lookup in the deprecated place, because if the report definition
        # has not been updated, it is more likely the correct definition is there.
        # Only reports with custom parser sepcified in Python are still there.
        cr.execute("SELECT * FROM ir_act_report_xml WHERE jasper_report='t' and report_name=%s limit 1", (name,))
        record = cr.dictfetchone()
        if not record:
            return super(ir_actions_report_xml, self)._lookup_report(cr, name)
        #Calling Jasper
        new_report = register_jasper_report(name, record['model'])
        return new_report

# vim:noexpandtab:smartindent:tabstop=8:softtabstop=8:shiftwidth=8:
