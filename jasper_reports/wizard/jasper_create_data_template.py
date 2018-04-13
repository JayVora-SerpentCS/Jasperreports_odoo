# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2012 Omar Castiñeira Saavedra <omar@pexego.es>
#                         Pexego Sistemas Informáticos http://www.pexego.es
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

import base64
from odoo import api, fields, models


class CreateDataTemplate(models.TransientModel):

    _name = 'jasper.create.data.template'
    _description = 'create data template'

    @api.multi
    def action_create_xml(self):
        for rec in self:
            for data in rec.read([]):
                model = self.env['ir.model'].browse(data['model'][0])
                xml = self.env['ir.actions.report'].create_xml(
                    model.model, data['depth'])
                base64_str = base64.encodestring(
                    ('%s' % (xml)).encode()).decode().replace('\n', '')
                rec.write({
                    'data': base64_str,
                    'filename': str(rec.model.name) + '_template.xml'
                })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'jasper.create.data.template',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': rec.id,
            'views': [(False, 'form')],
            'target': 'new',
        }

    model = fields.Many2one('ir.model', 'Model', required=True)
    depth = fields.Integer("Depth", required=True, default=1)
    filename = fields.Char('File Name', size=32)
    data = fields.Binary('XML')
