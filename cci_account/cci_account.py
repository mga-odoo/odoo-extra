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
from osv import fields, osv
import time

class account_move_line(osv.osv):

    def search(self, cr, user, args, offset=0, limit=None, order=None, context=None, count=False):
        # will check if the partner/account exists in statement lines if not then display all partner's account.move.line
        for item in args:
            if (item[0] in ('partner_id','account_id')) and (not item[2]):
                args.pop(args.index(item))

        return super(account_move_line,self).search(cr, user, args, offset, limit, order, context, count)

    _inherit = "account.move.line"
    _description = "account.move.line"

account_move_line()


class account_invoice(osv.osv):

    _inherit = "account.invoice"
    _columns = {
        'dept':fields.many2one('hr.department','Department'),
        'invoice_special':fields.boolean('Special Invoice'),
        'internal_note': fields.text('Internal Note'),
        'vat_num' : fields.related('partner_id', 'vat',  type='char', string="VAT"),
    }

    def create(self, cr, uid, vals, context={}):
        if vals.has_key('partner_id') and vals['partner_id']:
            partner = self.pool.get('res.partner').browse(cr, uid, vals['partner_id'], context=context)
            vals.update({'invoice_special':partner.invoice_special})
        return super(account_invoice, self).create(cr, uid, vals, context=context)

    def action_move_create(self, cr, uid, ids, context=None):
        flag = membership_flag = False
        product_ids = []
        move_obj = self.pool.get('account.move')
        move_line_obj = self.pool.get('account.move.line')
        data_invoice = self.browse(cr,uid,ids[0])
        #raise an error if one of the account_invoice_line doesn't have an analytic entry
        for line in data_invoice.invoice_line:
            if not line.analytics_id:
                flag = True
        if flag:
            raise osv.except_osv('Error!','Invoice line should have Analytic Distribution to create Analytic Entries.')
        super(account_invoice, self).action_move_create(cr, uid, ids, context)

        for lines in data_invoice.abstract_line_ids:
            if lines.product_id:
                product_ids.append(lines.product_id.id)
        if product_ids:
            data_product = self.pool.get('product.product').browse(cr,uid,product_ids)
            for product in data_product:
                if product.membership:
                    membership_flag = True
        if data_invoice.partner_id.alert_membership and membership_flag:
            raise osv.except_osv('Error!',data_invoice.partner_id.alert_explanation or 'Partner is not valid')
        
        #create other move lines if the invoice_line is related to a check payment or an AWEX credence
        for inv in self.browse(cr, uid, ids):
            for item in self.pool.get('account.invoice.line').search(cr, uid, [('invoice_id','=',inv.id)]):
                line = self.pool.get('account.invoice.line').browse(cr,uid, [item])[0]
                if line.cci_special_reference:
                    iml = []
                    if inv.type in ('in_invoice', 'in_refund'):
                        ref = inv.reference
                    else:
                        ref = self._convert_ref(cr, uid, inv.number)
                    temp = line.cci_special_reference.split('*')
                    obj = temp[0]
                    obj_id = int(temp[1])
                    obj_ref = self.pool.get(obj).browse(cr, uid, [obj_id])[0]
                    if obj == "event.registration":
                        #acc_id = self.pool.get('account.account').search(cr, uid, [('name','=','Creances AWEX - Cheques Formations et Cheques Langues')])[0]
                        journal_id = self.pool.get('account.journal').search(cr, uid, [('name','=','CFL Journal')])[0]
                        amount = obj_ref.check_amount
                    else:
                        journal_id = self.pool.get('account.journal').search(cr, uid, [('name','=','AWEX Journal')])[0]
                        #acc_id = self.pool.get('account.account').search(cr, uid, [('name','=','Creances AWEX - Cheques Formations et Cheques Langues')])[0]
                        amount = obj_ref.awex_amount
                    acc_id = self.pool.get('account.journal').browse(cr, uid, [journal_id])[0].default_debit_account_id.id
                    iml.append({
                        'type': 'dest',
                        'name': inv['name'] or '/',
                        'price': amount,
                        'account_id': acc_id,
                        'date_maturity': inv.date_due or False,
                        'amount_currency': False,
                        'currency_id': inv.currency_id.id or False,
                        'ref': ref,
                    })
                    iml.append({
                        'type': 'dest',
                        'name': inv['name'] or '/',
                        'price': -(amount),
                        'account_id': inv.account_id.id,
                        'date_maturity': inv.date_due or False,
                        'amount_currency': False,
                        'currency_id': inv.currency_id.id or False,
                        'ref': ref,
                    })
                    date = inv.date_invoice
                    part = inv.partner_id.id
                    new_lines = map(lambda x:(0,0,self.line_get_convert(cr, uid, x, part, date, context={})) ,iml)
                    for item in new_lines:
                        if item[2]['credit']:
                            id1 = item[2]['credit']

                    journal = self.pool.get('account.journal').browse(cr, uid, journal_id)
                    if journal.sequence_id:
                        name = self.pool.get('ir.sequence').get_id(cr, uid, journal.sequence_id.id)

                    move = {'name': name, 'line_id': new_lines, 'journal_id': journal_id}
                    if inv.period_id:
                        move['period_id'] = inv.period_id.id
                        for i in line:
                            i[2]['period_id'] = inv.period_id.id
                    move_id = move_obj.create(cr, uid, move)
                    move_obj.post(cr, uid, [move_id])

                #this function could be improved in order to enable having more than one translation line per invoice
                    id1 = move_line_obj.search(cr, uid, [('move_id','=',move_id),('credit','<>',False)])[0]
                    id2 = move_line_obj.search(cr, uid, [('invoice','=',inv.id),('debit','<>',0)])[0]
                    move_line_obj.reconcile_partial(cr, uid, [id2,id1], 'manual', context=context)

        return True

    def action_number(self, cr, uid, ids, *args):
        res = super(account_invoice,self).action_number(cr, uid, ids, args)
        for inv in self.browse(cr, uid, ids):
            vcs =''
            if inv.number and not inv.name:
                vcs3=str(inv.number).split('/')[1]
                vcs1='0'+ str(inv.date_invoice[2:4])
                if len(str(vcs3))>=5:
                    vcs2=str(inv.number[3]) + str(vcs3[0:5])
                elif len(str(vcs3))==4:
                    vcs2=str(inv.number[3]) + '0' +str(vcs3)
                else:
                    vcs2=str(inv.number[3]) + '00' +str(vcs3)

                vcs4= vcs1 + vcs2 + '0'

                vcs5=int(vcs4)
                check_digit=vcs5%97

                if check_digit==0:
                    check_digit='97'
                if check_digit<=9:
                    check_digit='0'+str(check_digit)
                vcs=vcs1+'/'+vcs2+'/'+ '0' +str(check_digit)

                self.write(cr, uid, [inv.id], {'name':vcs})
                ids = self.pool.get('account.move.line').search(cr, uid, [('move_id','=',inv.move_id.id)])
                self.pool.get('account.move.line').write(cr, uid, ids, {'name':vcs})
        return res

    #raise an error if the partner has the warning 'alert_others' when we choose him in the account_invoice form
    def onchange_partner_id(self, cr, uid, ids, type, partner_id,date_invoice=False, payment_term=False):
        inv_special=False
        if partner_id:
            data_partner = self.pool.get('res.partner').browse(cr,uid,partner_id)
            inv_special=data_partner.invoice_special
            if data_partner.alert_others:
                raise osv.except_osv('Error!',data_partner.alert_explanation or 'Partner is not valid')

        data=super(account_invoice,self).onchange_partner_id( cr, uid, ids, type, partner_id,date_invoice, payment_term)
        data['value']['invoice_special']=inv_special
        return data

account_invoice()


class sale_order(osv.osv):
    _inherit = "sale.order"
    _columns = {
        'dept' :  fields.many2one('hr.department','Department'),
    }

sale_order()


class account_invoice_line(osv.osv):
    _inherit = "account.invoice.line"
    _columns = {
        'cci_special_reference' : fields.char('Special Reference', size=64),
    }
    _defaults = {
        'cci_special_reference': lambda *a : False,
    }
account_invoice_line()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

