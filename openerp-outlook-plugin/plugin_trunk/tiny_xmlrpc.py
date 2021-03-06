import xmlrpclib
import sys
import socket
import os
import pythoncom
import time
from manager import ustr

waittime = 10
wait_count = 0
wait_limit = 12

def execute(connector, method, *args):
    global wait_count
    res = False
    try:
        res = getattr(connector,method)(*args)
    except socket.error,e:
        if e.args[0] == 111:
            if wait_count > wait_limit:
                print "Server is taking too long to start, it has exceeded the maximum limit of %d seconds."%(wait_limit)
                clean()
                sys.exit(1)
            print 'Please wait %d sec to start server....'%(waittime)
            wait_count += 1
            time.sleep(waittime)
            res = execute(connector, method, *args)
        else:
            return res
    wait_count = 0
    return res

class XMLRpcConn(object):
    __name__ = 'XMLRpcConn'
    _com_interfaces_ = ['_IDTExtensibility2']
    _public_methods_ = ['GetDBList', 'login', 'GetAllObjects', 'GetObjList', 'InsertObj', 'DeleteObject', \
                        'ArchiveToOpenERP', 'IsCRMInstalled', 'GetPartners', 'GetObjectItems', \
                        'CreateCase', 'MakeAttachment', 'CreateContact', 'CreatePartner', 'getitem', 'setitem', \
                        'SearchPartnerDetail', 'WritePartnerValues', 'GetAllState', 'GetAllCountry' ]
    _reg_clsctx_ = pythoncom.CLSCTX_INPROC_SERVER
    _reg_clsid_ = "{C6399AFD-763A-400F-8191-7F9D0503CAE2}"
    _reg_progid_ = "Python.OpenERP.XMLRpcConn"
    _reg_policy_spec_ = "win32com.server.policy.EventHandlerPolicy"
    def __init__(self,server='localhost',port=8069,uri='http://localhost:8069'):
        self._server=server
        self._port=port
        self._uri=uri
        self._obj_list=[]
        self._dbname=''
        self._uname='admin'
        self._pwd='a'
        self._login=False
        self._running=False
        self._uid=False
        self._iscrm=True
        self.partner_id_list=None
        self.protocol=None
    def getitem(self, attrib):
        v=self.__getattribute__(attrib)
        return str(v)

    def setitem(self, attrib, value):
        return self.__setattr__(attrib, value)

    def GetDBList(self):
        conn = xmlrpclib.ServerProxy(self._uri + '/xmlrpc/db')
        try:
            db_list = execute(conn, 'list')
            if db_list == False:
                self._running=False
                return []
            else:
                self._running=True
        except:
            db_list=-1
            self._running=True
        return db_list

    def login(self,dbname, user, pwd):
        self._dbname = dbname
        self._uname = user
        self._pwd = pwd
        conn = xmlrpclib.ServerProxy(str(self._uri) + '/xmlrpc/common')
        uid = execute(conn,'login',dbname, ustr(user), ustr(pwd))
        return uid

    def GetAllObjects(self):
        conn = xmlrpclib.ServerProxy(self._uri+ '/xmlrpc/object')
        ids = execute(conn,'execute',self._dbname,int(self._uid),self._pwd,'ir.model','search',[])
        objects = execute(conn,'execute',self._dbname,int(self._uid),self._pwd,'ir.model','read',ids,['model'])
        obj_list = [item['model'] for item in objects]
        return obj_list

    def GetObjList(self):
        self._obj_list=list(self._obj_list)
        self._obj_list.sort(reverse=True)
        return self._obj_list

    def InsertObj(self, obj_title,obj_name,image_path):
        self._obj_list=list(self._obj_list)
        self._obj_list.append((obj_title,obj_name,ustr(image_path).encode('iso-8859-1')))
        self._obj_list.sort(reverse=True)

    def DeleteObject(self,sel_text):
        self._obj_list=list(self._obj_list)
        for obj in self._obj_list:
            if obj[0] == sel_text:
                self._obj_list.remove(obj)
                break

    def ArchiveToOpenERP(self, recs, mail):
        import win32ui, win32con
        conn = xmlrpclib.ServerProxy(self._uri + '/xmlrpc/object')
        import eml
        msg = ""
        ext_msg = ""
        eml_path=eml.generateEML(mail)
        att_name = ustr(eml_path.split('\\')[-1])
        cnt=1
        flag=False
        for rec in recs: #[('res.partner', 3, 'Agrolait')]
            cnt+=1
            obj = rec[0]
            obj_id = rec[1]
            ids=execute(conn,'execute',self._dbname,int(self._uid),self._pwd,'ir.attachment','search',[('res_id','=',obj_id),('name','=',att_name)])
            object_ids = execute ( conn,'execute',self._dbname,int(self._uid),self._pwd,'ir.model','search',[('model','=',obj)])
            object_name = execute( conn,'execute',self._dbname,int(self._uid),self._pwd,'ir.model','read',object_ids,['name'])[0]['name']
            sub = ustr(mail.Subject)
            if ids:
                name=execute(conn,'execute',self._dbname,int(self._uid),self._pwd,obj,'read',obj_id,['name'])['name']
                ext_msg+="""  - File "{0}.eml" is already archived to {1} "{2}" .
""".format(sub,object_name,name)
                continue
            if len(sub) > 60:
                l = 60 - len(sub)
                sub = sub[0:l]
            res={}
            res['res_model'] = obj
            content = "".join(open(eml_path,"r").readlines()).encode('base64')
            res['name'] = att_name
            res['datas_fname'] = sub+".eml"
            res['datas'] = content
            res['res_id'] = obj_id
            execute(conn,'execute',self._dbname,int(self._uid),self._pwd,'ir.attachment','create',res)
            msg+="""  - File "{0}.eml"  archived to {1} "{2}".
""".format(sub,object_name,str(rec[2]))
            flag=True
        if flag:
            t = "Mail archived to OpenERP.\nArchive Summary : \n"
            if ext_msg != "" :
                t+="\nAlready Attached Documents : \n"+ext_msg +"\n"
            t+="Newly Attachment Documents:\n"+msg
            win32ui.MessageBox(t,"Archive To OpenERP",win32con.MB_ICONINFORMATION)

        return flag

    def IsCRMInstalled(self):
        conn = xmlrpclib.ServerProxy(self._uri+ '/xmlrpc/object')
        id = execute(conn,'execute',self._dbname,int(self._uid),self._pwd,'ir.model','search',[('model','=','crm.lead')])
        return id

    def GetPartners(self):
        conn = xmlrpclib.ServerProxy(self._uri+ '/xmlrpc/object')
        ids=[]
        ids = execute(conn,'execute',self._dbname,int(self._uid),self._pwd,'res.partner','search',[])
        ids.sort()
        obj_list=[]
        obj_list.append((-999, ustr('')))
        for id in ids:
            object = execute(conn,'execute',self._dbname,int(self._uid),self._pwd,'res.partner','read',[id],['id','name'])[0]
            obj_list.append((object['id'], ustr(object['name']).encode('iso-8859-1')))
        return obj_list

    def GetObjectItems(self, search_list=[], search_text=''):
        import win32ui
        res = []
        conn = xmlrpclib.ServerProxy(self._uri+ '/xmlrpc/object')
        for obj in search_list:
            object_ids = execute ( conn,'execute',self._dbname,int(self._uid),self._pwd,'ir.model','search',[('model','=',obj)])
            object_name = execute( conn,'execute',self._dbname,int(self._uid),self._pwd,'ir.model','read',object_ids,['name'])[0]['name']
            if obj == "res.partner.address":
                ids = execute(conn,'execute',self._dbname,int(self._uid),self._pwd,obj,'search',['|',('name','ilike',ustr(search_text)),('email','ilike',ustr(search_text))])
                recs = execute(conn,'execute',self._dbname,int(self._uid),self._pwd,obj,'read',ids,['id','name','street','city'])
                for rec in recs:
                    name = ustr(rec['name']).encode('iso-8859-1')
                    if rec['street']:
                        name += ', ' + ustr(rec['street']).encode('iso-8859-1')
                    if rec['city']:
                        name += ', ' + ustr(rec['city']).encode('iso-8859-1')
                    res.append((obj,rec['id'],name,object_name))
            else:
                ids = execute(conn,'execute',self._dbname,int(self._uid),self._pwd,obj,'search',[('name','ilike',ustr(search_text))])
                recs = execute(conn,'execute',self._dbname,int(self._uid),self._pwd,obj,'read',ids,['id','name'])
                for rec in recs:
                    name = ustr(rec['name']).encode('iso-8859-1')
                    res.append((obj,rec['id'],name,object_name))
        return res

    def CreateCase(self, section, mail, partner_ids, with_attachments=True):
        res={}
        import win32ui
        section=str(section)
        partner_ids=eval(str(partner_ids))
        conn = xmlrpclib.ServerProxy(self._uri+ '/xmlrpc/object')
        res['name'] = ustr(mail.Subject)
        res['description'] = ustr(mail.Body)
        res['partner_name'] = ustr(mail.SenderName)
        res['email_from'] = ustr(mail.SenderEmailAddress)

        if partner_ids:
            for partner_id in partner_ids:
                res['partner_id'] = partner_id
                partner_addr = execute(conn,'execute',self._dbname,int(self._uid),self._pwd,'res.partner','address_get',[partner_id])
                res['partner_address_id'] = partner_addr['default']
                id=execute(conn,'execute',self._dbname,int(self._uid),self._pwd,section,'create',res)
                if section == 'project.issue':
                    execute(conn,'execute',self._dbname,int(self._uid),self._pwd,section,'convert_to_bug',[id])
                recs=[(section,id,'')]
                if with_attachments:
                    self.MakeAttachment(recs, mail)
        else:
            id=execute(conn,'execute',self._dbname,int(self._uid),self._pwd,section,'create',res)
            recs=[(section,id,'')]
            if with_attachments:
                self.MakeAttachment(recs, mail)

    def MakeAttachment(self, recs, mail):
        attachments = mail.Attachments
        conn = xmlrpclib.ServerProxy(self._uri+ '/xmlrpc/object')
        att_folder_path = os.path.abspath(os.path.dirname(__file__)+"\\dialogs\\resources\\attachments\\")
        if not os.path.exists(att_folder_path):
            os.makedirs(att_folder_path)
        for rec in recs: #[('res.partner', 3, 'Agrolait')]
            obj = rec[0]
            obj_id = rec[1]
            res={}
            res['res_model'] = obj
            for i in xrange(1, attachments.Count+1):
                fn = ustr(attachments[i].FileName).encode('iso-8859-1')
                if len(fn) > 64:
                    l = 64 - len(fn)
                    f = fn.split('.')
                    fn = f[0][0:l] + '.' + f[-1]
                att_path = os.path.join(att_folder_path,fn)
                attachments[i].SaveAsFile(att_path)
                f=open(att_path,"rb")
                content = "".join(f.readlines()).encode('base64')
                f.close()
                res['name'] = ustr(attachments[i].DisplayName)
                res['datas_fname'] = ustr(fn)
                res['datas'] = content
                res['res_id'] = obj_id
                execute(conn,'execute',self._dbname,int(self._uid),self._pwd,'ir.attachment','create',res)

    def CreateContact(self, sel=None, res=None):
        res=eval(str(res))

        self.partner_id_list=eval(str(self.partner_id_list))
        if self.partner_id_list.get(sel,-999) != -999:
            res['partner_id'] = self.partner_id_list[sel]
        conn = xmlrpclib.ServerProxy(self._uri+ '/xmlrpc/object')
        id = execute(conn,'execute',self._dbname,int(self._uid),self._pwd,'res.partner.address','create',res)
        return id

    def CreatePartner(self, res):
        res=eval(str(res))
        conn = xmlrpclib.ServerProxy(self._uri+ '/xmlrpc/object')
        ids = execute(conn,'execute',self._dbname,int(self._uid),self._pwd,'res.partner','search',[('name','=',res['name'])])
        if ids:
            return False
        id = execute(conn,'execute',self._dbname,int(self._uid),self._pwd,'res.partner','create',res)
        return id

    def SearchPartnerDetail(self, search_email_id):
        import win32ui
        res_vals = []
        address = {}
        conn = xmlrpclib.ServerProxy(self._uri+ '/xmlrpc/object')
        address_id = execute(conn, 'execute', self._dbname, int(self._uid), self._pwd, 'res.partner.address', 'search', [('email','ilike',ustr(search_email_id))])
        if not address_id :
            return
        address = execute(conn, 'execute', self._dbname, int(self._uid), self._pwd, 'res.partner.address','read',address_id[0],['id','partner_id','name','street','street2','city','state_id','country_id','phone','mobile','email','fax','zip'])
        for key, vals in address.items():
            res_vals.append([key,vals])
        return res_vals

    def WritePartnerValues(self, new_vals):
        import win32ui
        flag = -1
        new_dict = dict(new_vals)
        email=new_dict['email']
        conn = xmlrpclib.ServerProxy(self._uri+ '/xmlrpc/object')
        address_id = execute( conn, 'execute', self._dbname, int(self._uid), self._pwd, 'res.partner.address', 'search', [('email','=',ustr(email))])
        if not address_id:
            return flag
        address = execute( conn, 'execute', self._dbname, int(self._uid), self._pwd, 'res.partner.address','read',address_id[0],['id','partner_id','state_id','country_id'])
        vals_res_address={ 'name' : new_dict['name'],
                           'street':new_dict['street'],
                           'street2' : new_dict['street2'],
                           'city' : new_dict['city'],
                           'phone' : new_dict['phone'],
                           'mobile' : new_dict['mobile'],
                           'fax' : new_dict['fax'],
                           'zip' : new_dict['zip'],
                         }
        if new_dict['partner_id'] != -1:
            vals_res_address['partner_id'] = new_dict['partner_id']
        if new_dict['state_id'] != -1:
            vals_res_address['state_id'] = new_dict['state_id']
        if new_dict['country_id'] != -1:
            vals_res_address['country_id'] = new_dict['country_id']
        temp = execute( conn, 'execute', self._dbname, int(self._uid), self._pwd, 'res.partner.address', 'write', address_id, vals_res_address)
        if temp:
            flag=1
        else:
            flag=0
        return flag

    def GetAllState(self):
        import win32ui
        state_list = []
        state_ids = []
        conn = xmlrpclib.ServerProxy(self._uri+ '/xmlrpc/object')
        state_ids = execute( conn, 'execute', self._dbname, int(self._uid), self._pwd, 'res.country.state', 'search', [])
        for state_id in state_ids:
            obj = execute( conn, 'execute', self._dbname, int(self._uid), self._pwd, 'res.country.state', 'read', [state_id],['id','name'])[0]
            state_list.append((obj['id'], ustr(obj['name']).encode('iso-8859-1')))
        return state_list

    def GetAllCountry(self):
        import win32ui
        country_list = []
        country_ids = []
        conn = xmlrpclib.ServerProxy(self._uri+ '/xmlrpc/object')
        country_ids = execute( conn, 'execute', self._dbname, int(self._uid), self._pwd, 'res.country', 'search', [])
        for country_id in country_ids:
            obj = execute( conn, 'execute', self._dbname, int(self._uid), self._pwd, 'res.country','read', [country_id], ['id','name'])[0]
            country_list.append((obj['id'], ustr(obj['name']).encode('iso-8859-1')))
        return country_list
