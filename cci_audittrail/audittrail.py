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
from osv import osv, fields
import time, pooler, copy
import ir

class audittrail_rule(osv.osv):
    _inherit = 'audittrail.rule'

    def __init__(self, pool, cr=None):
        for obj_name in pool.obj_list():
            obj=pool.get(obj_name)
            for field in ('read','write','create','unlink'):
                 setattr(obj, field, self.logging_fct(getattr(obj, field), obj))
        super(audittrail_rule, self).__init__(pool, cr)

    def logging_fct(self, fct_src, obj):
        object_name = obj._name
        object = None
        logged_uids = []
        def get_value_text(cr, uid, field_name, values, object, context={}):
            f_id= self.pool.get('ir.model.fields').search(cr, uid, [('name','=',field_name),('model_id','=',object.id)])
            if f_id:
                field=self.pool.get('ir.model.fields').read(cr, uid, f_id)[0]
                model=field['relation']

                if field['ttype']=='many2one':
                    if values:
                        if type(values)==tuple:
                                values=values[0]
                        val=self.pool.get(model).read(cr, uid, [values], ['name'])
                        if len(val):
                            return val[0]['name']

                elif field['ttype'] == 'many2many':
                    value=[]
                    if values:
                        for id in values:
                            val=self.pool.get(model).read(cr, uid, [id], ['name'])
                            if len(val):
                                value.append(val[0]['name'])
                    return value

                elif field['ttype'] == 'one2many':

                    if values:
                        value=[]
                        for id in values:
                            val=self.pool.get(model).read(cr, uid, [id], ['name'])
                            if len(val):
                                value.append(val[0]['name'])
                        return value
            return values

        def create_log_line(cr, uid, id, object, lines=[]):
            for line in lines:
                f_id= self.pool.get('ir.model.fields').search(cr, uid,[('name','=',line['name']),('model_id','=',object.id)])
                if len(f_id):
                    fields=self.pool.get('ir.model.fields').read(cr, uid, f_id)
                    old_value='old_value' in line and  line['old_value'] or ''
                    new_value='new_value' in line and  line['new_value'] or ''
                    old_value_text='old_value_text' in line and  line['old_value_text'] or ''
                    new_value_text='new_value_text' in line and  line['new_value_text'] or ''

                    if fields[0]['ttype']== 'many2one':
                        if type(old_value)==tuple:
                            old_value=old_value[0]
                        if type(new_value)==tuple:
                            new_value=new_value[0]
                    self.pool.get('audittrail.log.line').create(cr, uid, {"log_id": id, "field_id": f_id[0] ,"old_value":old_value ,"new_value":new_value,"old_value_text":old_value_text ,"new_value_text":new_value_text,"field_description":fields[0]['field_description']})
            return True

        def my_fct( cr, uid, *args, **args2):
            obj_ids= self.pool.get('ir.model').search(cr, uid,[('model','=',object_name)])
            if not len(obj_ids):
                return fct_src(cr, uid, *args, **args2)
            object=self.pool.get('ir.model').browse(cr, uid, obj_ids)[0]
            rule_ids=self.search(cr, uid, [('object_id','=',obj_ids[0]),('state','=','subscribed')])
            if not len(rule_ids):
                return fct_src(cr, uid, *args, **args2)

            field=fct_src.__name__
            for thisrule in self.browse(cr, uid, rule_ids):
                if not getattr(thisrule, 'log_'+field):
                    return fct_src(cr, uid, *args, **args2)
                self.__functions.setdefault(thisrule.id, [])
                self.__functions[thisrule.id].append( (obj,field, getattr(obj,field)) )
                for user in thisrule.user_id:
                            logged_uids.append(user.id)

            if fct_src.__name__ in ('create'):
                res_id =fct_src( cr, uid, *args, **args2)
                new_value=self.pool.get(object.model).read(cr,uid,[res_id],args[0].keys())[0]
                if 'id' in new_value:
                    del new_value['id']
                if not len(logged_uids) or uid in logged_uids:
                    id=self.pool.get('audittrail.log').create(cr, uid, {"method": fct_src.__name__, "object_id": object.id, "user_id": uid, "res_id": res_id,"name": "%s %s %s" % (fct_src.__name__, object.id, time.strftime("%Y-%m-%d %H:%M:%S"))})
                    lines=[]
                    for field in new_value:
                        if new_value[field]:
                            line={
                                  'name':field,
                                  'new_value':new_value[field],
                                  'new_value_text':get_value_text(cr,uid,field,new_value[field],object)
                                  }
                            lines.append(line)
                    create_log_line(cr,uid,id,object,lines)
                return res_id

            if fct_src.__name__ in ('write'):
                res_ids=args[0]
                for res_id in res_ids:
                    old_values=self.pool.get(object.model).read(cr,uid,res_id,args[1].keys())
                    old_values_text={}
                    for field in args[1].keys():
                        old_values_text[field]=get_value_text(cr,uid,field,old_values[field],object)
                    res =fct_src( cr, uid, *args, **args2)
                    if res:
                        new_values=self.pool.get(object.model).read(cr,uid,res_ids,args[1].keys())[0]
                        if not len(logged_uids) or uid in logged_uids:
                            id=self.pool.get('audittrail.log').create(cr, uid, {"method": fct_src.__name__, "object_id": object.id, "user_id": uid, "res_id": res_id,"name": "%s %s %s" % (fct_src.__name__, object.id, time.strftime("%Y-%m-%d %H:%M:%S"))})
                            lines=[]
                            for field in args[1].keys():
                                if args[1].keys():
                                    line={
                                          'name':field,
                                          'new_value':field in new_values and new_values[field] or '',
                                          'old_value':field in old_values and old_values[field] or '',
                                          'new_value_text':get_value_text(cr,uid,field,new_values[field],object),
                                          'old_value_text':old_values_text[field]
                                          }
                                    lines.append(line)
                            create_log_line(cr,uid,id,object,lines)
                    return res

            if fct_src.__name__ in ('read'):
                res_ids=args[0]
                old_values={}
                res =fct_src( cr, uid,*args, **args2)
                if type(res)==list:

                    for v in res:
                        old_values[v['id']]=v
                else:

                    old_values[res['id']]=res
                for res_id in old_values:
                    if not len(logged_uids) or uid in logged_uids:
                        id=self.pool.get('audittrail.log').create(cr, uid, {"method": fct_src.__name__, "object_id": object.id, "user_id": uid, "res_id": res_id,"name": "%s %s %s" % (fct_src.__name__, object.id, time.strftime("%Y-%m-%d %H:%M:%S"))})
                        lines=[]
                        for field in old_values[res_id]:
                            if old_values[res_id][field]:
                                line={
                                          'name':field,
                                          'old_value':old_values[res_id][field],
                                          'old_value_text':get_value_text(cr,uid,field,old_values[res_id][field],object)
                                          }
                                lines.append(line)
                    create_log_line(cr,uid,id,object,lines)
                return res
            if fct_src.__name__ in ('unlink'):
                res_ids=args[0]
                old_values={}
                for res_id in res_ids:
                    old_values[res_id]=self.pool.get(object.model).read(cr,uid,res_id,[])

                for res_id in res_ids:
                    if not len(logged_uids) or uid in logged_uids:
                        id=self.pool.get('audittrail.log').create(cr, uid, {"method": fct_src.__name__, "object_id": object.id, "user_id": uid, "res_id": res_id,"name": "%s %s %s" % (fct_src.__name__, object.id, time.strftime("%Y-%m-%d %H:%M:%S"))})
                        lines=[]
                        for field in old_values[res_id]:
                            if old_values[res_id][field]:
                                line={
                                      'name':field,
                                      'old_value':old_values[res_id][field],
                                      'old_value_text':get_value_text(cr,uid,field,old_values[res_id][field],object)
                                      }
                                lines.append(line)
                        create_log_line(cr,uid,id,object,lines)
                res =fct_src( cr, uid,*args, **args2)
                return res

        return my_fct

audittrail_rule()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

