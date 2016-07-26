# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2008-2012 NaN Projectes de Programari Lliure, S.L.
#                         http://www.NaN-tic.com
# Copyright (C) 2013 Tadeus Prastowo <tadeus.prastowo@infi-nity.com>
#                         Vikasa Infinity Anugrah <http://www.infi-nity.com>
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

import os
import base64
from . import jasper_report
from openerp.exceptions import except_orm
from openerp import models, fields, api, _
import unicodedata
from xml.dom.minidom import getDOMImplementation

src_chars = """ '"()/*-+?¿!&$[]{}@#`'^:;<>=~%,\\"""
src_chars = unicode(src_chars, 'iso-8859-1')
dst_chars = """________________________________"""
dst_chars = unicode(dst_chars, 'iso-8859-1')


class report_xml_file(models.Model):
    _name = 'ir.actions.report.xml.file'

    file = fields.Binary('File', required=True,
                         filters="*.jrxml,*.properties,*.ttf",)
    filename = fields.Char('File Name', size=256)
    report_id = fields.Many2one('ir.actions.report.xml', 'Report',
                                ondelete='cascade')
    default = fields.Boolean('Default')

    @api.model
    def create(self, vals):
        result = super(report_xml_file, self).create(vals)
        ir_actions_report_obj = self.env['ir.actions.report.xml'
                                         ].browse(vals['report_id'])
        ir_actions_report_obj.update()
        return result

    @api.multi
    def write(self, vals):
        result = super(report_xml_file, self).write(vals)
        for attachment in self:
            ir_actions_report_obj = self.env['ir.actions.report.xml'
                                             ].browse([attachment.report_id.id
                                                       ])
            ir_actions_report_obj.update()
        return result


# Inherit ir.actions.report.xml and add an action to be able to store
# .jrxml and .properties files attached to the report so they can be
# used as reports in the application.
class report_xml(models.Model):
    _inherit = 'ir.actions.report.xml'

    jasper_output = fields.Selection([('html', 'HTML'), ('csv', 'CSV'),
                                      ('xls', 'XLS'), ('rtf', 'RTF'),
                                      ('odt', 'ODT'), ('ods', 'ODS'),
                                      ('txt', 'Text'), ('pdf', 'PDF')],
                                     'Jasper Output', default='pdf')
    jasper_file_ids = fields.One2many('ir.actions.report.xml.file',
                                      'report_id', 'Files', help='')
    jasper_model_id = fields.Many2one('ir.model', 'Model', help='')
    jasper_report = fields.Boolean('Is Jasper Report?')

    @api.model
    def create(self, vals):
        if self._context and self._context.get('jasper_report'):
            vals['model'] = self.env['ir.model'
                                     ].browse(vals['jasper_model_id']).model
            vals['type'] = 'ir.actions.report.xml'
            vals['report_type'] = 'pdf'
            vals['jasper_report'] = True
        return super(report_xml, self).create(vals)

    @api.multi
    def write(self, vals):
        if self._context and self._context.get('jasper_report'):
            if 'jasper_model_id' in vals:
                vals['model'] = self.env['ir.model'
                                         ].browse(vals['jasper_model_id'
                                                       ]).model
            vals['type'] = 'ir.actions.report.xml'
            vals['report_type'] = 'pdf'
            vals['jasper_report'] = True
        return super(report_xml, self).write(vals)

    @api.multi
    def update(self):
        if self._context is None:
            self._context = {}
        pool_values = self.env['ir.values']
        for report in self:
            has_default = False
            # Browse attachments and store .jrxml and .properties
            # into jasper_reports/custom_reportsdirectory. Also add
            # or update ir.values data so they're shown on model views.for
            # attachment in self.env['ir.attachment'].browse(attachmentIds)
            for attachment in report.jasper_file_ids:
                content = attachment.file
                fileName = attachment.filename
                if not fileName or not content:
                    continue
                path = self.save_file(fileName, content)
                if '.jrxml' in fileName:
                    if attachment.default:
                        if has_default:
                            raise except_orm(_('Error'),
                                             _('There is more than one \
                                             report marked as default'))
                        has_default = True
                        # Update path into report_rml field.
                        my_obj = self.browse([report.id])
                        my_obj.write({'report_rml': path})
                        ser_arg = [('value', '=',
                                    'ir.actions.report.xml,%s' % report.id)]
                        valuesId = pool_values.search(ser_arg)
                        data = {
                            'name': report.name,
                            'model': report.model,
                            'key': 'action',
                            'object': True,
                            'key2': 'client_print_multi',
                            'value': 'ir.actions.report.xml,%s' % report.id
                        }
                        if not valuesId.ids:
                            valuesId = pool_values.create(data)
                        else:
                            for pool_obj in pool_values.browse(valuesId.ids):
                                pool_obj.write(data)
                                valuesId = valuesId[0]

            if not has_default:
                raise except_orm(_('Error'),
                                 _('No report has been marked as default! \
                                 You need atleast one jrxml report!'))

            # Ensure the report is registered so it can be used immediately
            jasper_report.register_jasper_report(report.report_name,
                                                 report.model)
        return True

    def save_file(self, name, value):
        path = os.path.abspath(os.path.dirname(__file__))
        path += '/custom_reports/%s' % name
        f = open(path, 'wb+')
        try:
            f.write(base64.decodestring(value))
        finally:
            f.close()
        path = 'jasper_reports/custom_reports/%s' % name
        return path

    def normalize(self, text):
        if isinstance(text, unicode):
            text = text.encode('utf-8')
        return text

    def unaccent(self, text):
        if isinstance(text, str):
            text = unicode(text, 'utf-8')
        output = text
        for c in xrange(len(src_chars)):
            if c >= len(dst_chars):
                break
            output = output.replace(src_chars[c], dst_chars[c])
        output = unicodedata.normalize('NFKD', output).encode('ASCII',
                                                              'ignore')
        return output.strip('_').encode('utf-8')

    @api.model
    def generate_xml(self, pool, modelName, parentNode, document, depth,
                     first_call):
        if self._context is None:
            self._context = {}
        # First of all add "id" field
        fieldNode = document.createElement('id')
        parentNode.appendChild(fieldNode)
        valueNode = document.createTextNode('1')
        fieldNode.appendChild(valueNode)
        language = self._context.get('lang')
        if language == 'en_US':
            language = False

        # Then add all fields in alphabetical order
        model = pool.get(modelName)
        fields = model._columns.keys()
        fields += model._inherit_fields.keys()
        # Remove duplicates because model may have fields with the
        # same name as it's parent
        fields = sorted(list(set(fields)))
        for field in fields:
            name = False
            if language:
                # Obtain field string for user's language.
                name = self.env['ir.translation']._get_source(
                    '{model},{field}'.format(model=modelName, field=field),
                    'field', language)
            if not name:
                # If there's not description in user's language,
                # use default (english) one.
                if field in model._columns.keys():
                    name = model._columns[field].string
                else:
                    name = model._inherit_fields[field][2].string

            if name:
                name = self.unaccent(name)
            # After unaccent the name might result in an empty string
            if name:
                name = '%s-%s' % (self.unaccent(name), field)
            else:
                name = field
            fieldNode = document.createElement(name)

            parentNode.appendChild(fieldNode)
            if field in pool.get(modelName)._columns:
                fieldType = model._columns[field]._type
            else:
                fieldType = model._inherit_fields[field][2]._type
            if fieldType in ('many2one', 'one2many', 'many2many'):
                if depth <= 1:
                    continue
                if field in model._columns:
                    newName = model._columns[field]._obj
                else:
                    newName = model._inherit_fields[field][2]._obj
                self.generate_xml(pool, newName, fieldNode, document,
                                  depth - 1, False)
                continue

            value = field
            if fieldType == 'float':
                value = '12345.67'
            elif fieldType == 'integer':
                value = '12345'
            elif fieldType == 'date':
                value = '2009-12-31 00:00:00'
            elif fieldType == 'time':
                value = '12:34:56'
            elif fieldType == 'datetime':
                value = '2009-12-31 12:34:56'

            valueNode = document.createTextNode(value)
            fieldNode.appendChild(valueNode)

        if depth > 1 and modelName != 'Attachments':
            # Create relation with attachments
            fieldNode = document.createElement('%s-Attachments' % self.
                                               unaccent(_('Attachments')))
            parentNode.appendChild(fieldNode)
            self.generate_xml(pool, 'ir.attachment', fieldNode, document,
                              depth - 1, False)

        if first_call:
            # Create relation with user
            fieldNode = document.createElement('%s-User' % self.unaccent
                                               (_('User')))
            parentNode.appendChild(fieldNode)
            self.generate_xml(pool, 'res.users', fieldNode, document,
                              depth - 1, False)

            # Create special entries
            fieldNode = document.createElement('%s-Special' % self.unaccent
                                               (_('Special')))
            parentNode.appendChild(fieldNode)

            newNode = document.createElement('copy')
            fieldNode.appendChild(newNode)
            valueNode = document.createTextNode('1')
            newNode.appendChild(valueNode)

            newNode = document.createElement('sequence')
            fieldNode.appendChild(newNode)
            valueNode = document.createTextNode('1')
            newNode.appendChild(valueNode)

            newNode = document.createElement('subsequence')
            fieldNode.appendChild(newNode)
            valueNode = document.createTextNode('1')
            newNode.appendChild(valueNode)

    @api.model
    def create_xml(self, model, depth):
        if self._context is None:
            self._context = {}
        document = getDOMImplementation().createDocument(None, 'data', None)
        topNode = document.documentElement
        recordNode = document.createElement('record')
        topNode.appendChild(recordNode)
        self.generate_xml(self.pool, model, recordNode, document, depth, True)
        topNode.toxml()
        return topNode.toxml()
