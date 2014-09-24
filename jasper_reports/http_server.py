# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2008-2012 NaN Projectes de Programari Lliure, S.L.
#                         http://www.NaN-tic.com
# Copyright (c) 2012 Omar Castiñeira Saavedra <omar@pexego.es>
#                         Pexego Sistemas Informáticos http://www.pexego.es
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
from openerp.service.websrv_lib import reg_http_service
from BaseHTTPServer import BaseHTTPRequestHandler
from openerp import netsvc
from openerp import tools

class Message:
    def __init__(self):
        self.status = False

class JasperHandler(BaseHTTPRequestHandler):
    cache = {}

    def __init__(self, request, client_address, server):
        pass
        #print "REQUEST: ", dir(request)
        #print "DIR SELF: ", dir(self)

    #def __getattr__(self, name):
        #print "NAME: ", name
        #return JasperHandler.__getattr__(self, name)

    def do_OPTIONS(self):
        pass

    def parse_request(self, *args, **kwargs):
        #self.headers = Message()
        #self.request_version = 'HTTP/1.1'
        #self.command = 'OPTIONS'

        path = self.raw_requestline.replace('GET','').strip().split(' ')[0]
        try:
            result = self.execute(path)
        except Exception, e:
            result = '<error><exception>%s</exception></error>' % (e.args, )
        self.wfile.write( result )
        return True

    def execute(self, path):
        #print "PATH: ", path
        path = path.strip('/')
        path = path.split('?')
        model = path[0]
        arguments = {}
        for argument in path[-1].split('&'):
            argument = argument.split('=')
            arguments[ argument[0] ] = argument[-1]

        use_cache = tools.config.get('jasper_cache', True)
        database = arguments.get('database', tools.config.get('jasper_database', 'stable8') )
        user = arguments.get('user', tools.config.get('jasper_user', 'admin') )
        password = arguments.get('password', tools.config.get('jasper_password', 'a') )
        depth = int( arguments.get('depth', tools.config.get('jasper_depth', 3) ) )
        language = arguments.get('language', tools.config.get('jasper_language', 'en'))
        # Check if data is in cache already
        key = '%s|%s|%s|%s|%s' % (model, database, user, depth, language)
        if key in self.cache:
            return self.cache[key]

        context = {
            'lang': language,
        }

        uid = netsvc.dispatch_rpc('common', 'login', (database, user, password))
        result = netsvc.dispatch_rpc('object', 'execute', (database, uid, password, 'ir.actions.report.xml', 'create_xml', model, depth, context))

        if use_cache:
            self.cache[key] = result

        return result

reg_http_service('/jasper/', JasperHandler)
