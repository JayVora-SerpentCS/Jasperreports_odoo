# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (C) 2017-Today Serpent Consulting Services Pvt. Ltd.
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
import odoo
import odoo.tools.config as Config


def gevent_server_init(self, app):
    """"To overwrite the openerp gevent server __init__ method and changed
    xmlrpc port no instead of the longpolling port  """

    self.port = Config['xmlrpc_port']
    self.httpd = None
    self.app = app
    # config
    self.interface = Config['xmlrpc_interface'] or '0.0.0.0'
    # runtime
    self.pid = os.getpid()


odoo.service.server.GeventServer.__init__ = gevent_server_init


def prefork_server_init(self, app):
    """"To overwrite the openerp prefork server __init__ method and changed
    longpolling port no instead of the xmlrpc port  """

    self.address = Config['xmlrpc'] and \
        (Config['xmlrpc_interface'] or '0.0.0.0', Config['longpolling_port'])
    self.population = Config['workers']
    self.timeout = Config['limit_time_real']
    self.limit_request = Config['limit_request']
    # working vars
    self.beat = 4
    self.app = app
    self.pid = os.getpid()
    self.socket = None
    self.workers_http = {}
    self.workers_cron = {}
    self.workers = {}
    self.generation = 0
    self.queue = []
    self.long_polling_pid = None


odoo.service.server.PreforkServer.__init__ = prefork_server_init
