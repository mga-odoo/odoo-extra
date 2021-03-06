# -*- encoding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.     
#
##############################################################################

import time
from report import report_sxw

class dm_offer_step(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(dm_offer_step, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'time': time,
        })
        self.context = context
 
report_sxw.report_sxw('report.dm.offer.step', 'dm.offer.step', 
                        'addons/dm/report/dm_offer_step.rml', parser=dm_offer_step)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

