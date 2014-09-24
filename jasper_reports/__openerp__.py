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

{
    "name" : "Jasper Reports",
    "version" : "1.1.1",
    "description" : '''
    This module integrates Jasper Reports with OpenERP. V6 and v7 compatible version was made by NaN-tic.
    Serpent Consulting Services Pvt Ltd has migrated it to v8. ''',
    "author" : "NaN·tic, Serpent Consulting Services Pvt Ltd",
    "website" : "http://www.nan-tic.com, http://www.serpentcs.com",
    'images' : [
        'images/jasper_reports-hover.png',
        'images/jasper_reports.png'
    ],
    "depends" : ["base"],
    "category" : "Generic Modules/Jasper Reports",
    "demo_xml" : [
        'jasper_demo.xml'
    ],
    "data" : [
        'wizard/jasper_create_data_template.xml',
        'jasper_wizard.xml',
        'report_xml_view.xml',
        'security/ir.model.access.csv',
        'data/jasper_data.xml'
    ],
    "active": False,
    "installable": True,
    'application': True,
}
