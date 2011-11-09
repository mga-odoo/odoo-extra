# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2008-2009 SIA "KN dati". (http://kndati.lv) All Rights Reserved.
#                    General contacts <info@kndati.lv>
#    Copyright (C) 2011 Domsense s.r.l. (<http://www.domsense.com>).
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
{
    "name":"Server Migration",
    "description": "This module is intended to migrate data from one OpenERP installation and another",
    "version":"1.1",
    "author":"KN dati, SIA, Agile Business Group",
    "category":"base",
    "depends":["base"],
    "demo_xml":[],
    "init_xml":[],
    "update_xml" : [
        "migration_view.xml",
        "wizard/load_config.xml",
        "security/ir.model.access.csv",
        ],
    "active":False,
    "installable":True,
}
