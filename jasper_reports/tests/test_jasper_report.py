# -*- coding: utf-8 -*-
import base64
import mock
from odoo.tests.common import TransactionCase
from odoo.modules.module import get_module_resource
# from odoo.addons.jasper_reports.controllers.main import ReportController
# from odoo.addons.web.controllers.main import ReportController


class TestJasperReport(TransactionCase):

    def setUp(self):
        super(TestJasperReport, self).setUp()
        # File path
        path = get_module_resource('jasper_reports', 'tests', 'user.jrxml')
        # Opening file
        file = open(path, 'rb')
        # Reading
        file_content = file.read()
        # Converting as base64
        report_file = base64.b64encode(file_content)

        self.JasperReport = self.env['ir.actions.report']
        self.users_modal = self.env['ir.model'].search([
            ('model', '=', 'res.users')]).id
        self.report_data = self.JasperReport.create({
            'name': 'Jasper Test Report',
            'model': 'res.users',
            'jasper_model_id': self.users_modal,
            'jasper_output': 'pdf',
            'report_name': 'res_users_jasper',
            'jasper_report': True,
            'jasper_file_ids': [
                (0, 0, {
                    'default': True,
                    'filename': 'user.jrxml',
                    'file': report_file,
                })
            ]
        })

    def test_report(self):
        with mock.patch('odoo.addons.jasper_reports.controllers.main.'
                        'ReportController') as ReportController:
            return ReportController.report_routes(
                                                  self,
                                                  reportname=self.
                                                  report_data.report_name,
                                                  converter="jasper")
