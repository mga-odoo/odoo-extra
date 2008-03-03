##############################################################################
#
# Copyright (c) 2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
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

import ir
import time
import os
import netsvc
import xmlrpclib
import netsvc
import pooler
import urllib
import base64

import wizard
from osv import osv

_export_done_form = '''<?xml version="1.0"?>
<form string="Initial import">
    <separator string="Taxes exported" colspan="4" />
    <field name="taxes_new"/>
    <newline/>
    <field name="taxes_update"/>
</form>'''

_export_done_fields = {
    'taxes_new': {'string':'New Taxes', 'type':'float', 'readonly': True},
    'taxes_update': {'string':'Updated Taxes', 'type':'float', 'readonly': True},

}
taxes_new = 0
taxes_update = 0
def _do_export(self, cr, uid, data, context):
    self.pool = pooler.get_pool(cr.dbname)
    ids = self.pool.get('esale_joomla.web').search(cr, uid, [])
    self.tax_new = 0
    self.tax_update = 0

    for website in self.pool.get('esale_joomla.web').browse(cr, uid, ids):
        logids = self.pool.get('esale_joomla.web.exportlog').search(cr,uid,[('web_id','=',website.id),('log_type','=','tax')],order='log_date desc')
        if len(logids):
            lastExportDate = self.pool.get('esale_joomla.web.exportlog').browse(cr,uid,logids)[0].log_date
        else:
            lastExportDate = 'False'
        server = xmlrpclib.ServerProxy("%s/tinyerp-synchro.php" % website.url)

        taxes_ids=self.pool.get('account.tax').search(cr, uid, [])

        def _add_taxes(tax):

                esale_joomla_id2 = self.pool.get('esale_joomla.tax').search(cr, uid, [('web_id','=',website.id),('tax_id','=',tax.id)])
                esale_joomla_id = 0
                if esale_joomla_id2:
                    esale_joomla_id = self.pool.get('esale_joomla.tax').browse(cr, uid, esale_joomla_id2[0]).esale_joomla_id



                webtax={
                    'esale_joomla_id': esale_joomla_id,
                    'name': tax.name,
                    'type': tax.type,
                    'rate': tax.amount,
                    'include_base_amount':tax.include_base_amount,
                    'sequence':tax.sequence,

                }
                if tax.company_id and len(tax.company_id.partner_id.address)>0:
                    if tax.company_id.partner_id.address[0].country_id :
                        webtax['country']=tax.company_id.partner_id.address[0].country_id.name
                    if tax.company_id.partner_id.address[0].state_id :
                        webtax['state']=tax.company_id.partner_id.address[0].state_id.name




                osc_id=server.set_tax(webtax)
                if osc_id!=esale_joomla_id:
                    if esale_joomla_id:
                        self.pool.get('esale_joomla.tax').write(cr, uid, [esale_joomla_id], {'esale_joomla_id': osc_id})
                        self.tax_update += 1
                    else:
                        self.pool.get('esale_joomla.tax').create(cr, uid, {'tax_id': tax.id, 'web_id': website.id, 'esale_joomla_id': osc_id, 'name': tax.name })
                        self.tax_new += 1
                else:
                    self.tax_update += 1

        for tax in self.pool.get('account.tax').browse(cr, uid, taxes_ids, context=context):
           _add_taxes(tax)

        self.pool.get('esale_joomla.web.exportlog').create(cr,uid,{'name': 'Taxes Export ' + time.strftime('%Y-%m-%d %H:%M:%S'),'web_id':website.id,'log_type':'tax'})

    return {'taxes_new':self.tax_new, 'taxes_update':self.tax_update}


class wiz_esale_joomla_tax(wizard.interface):
    states = {
        'init': {
            'actions': [_do_export],
            'result': {'type': 'form', 'arch': _export_done_form, 'fields': _export_done_fields, 'state': [('end', 'End')] }
        }
    }
wiz_esale_joomla_tax('esale_joomla.tax');
