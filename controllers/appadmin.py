# coding: utf8

# ##########################################################
# ## make sure administrator is on localhost
# ###########################################################

import os
import socket
import datetime
import copy
import gluon.contenttype
import gluon.fileutils

# ## critical --- make a copy of the environment

global_env = copy.copy(globals())
global_env['datetime'] = datetime

http_host = request.env.http_host.split(':')[0]
remote_addr = request.env.remote_addr
try:
    hosts = (http_host, socket.gethostname(),
             socket.gethostbyname(http_host),
             '::1','127.0.0.1','::ffff:127.0.0.1')   
except:
    hosts = (http_host, )

if request.env.http_x_forwarded_for or request.env.wsgi_url_scheme\
     in ['https', 'HTTPS']:
    session.secure()
elif remote_addr not in hosts:
    raise HTTP(200, T('appadmin is disabled because insecure channel'))
if not gluon.fileutils.check_credentials(request):
    redirect(URL(a='admin', c='default', f='index'))

ignore_rw = True
response.view = 'appadmin.html'
response.menu = [[T('design'), False, URL('admin', 'default', 'design',
                 args=[request.application])], [T('db'), False,
                 URL(r=request, f='index')], [T('state'), False,
                 URL(r=request, f='state')]]

# ##########################################################
# ## auxiliary functions
# ###########################################################


def get_databases(request):
    dbs = {}
    for (key, value) in global_env.items():
        cond = False
        try:
            cond = isinstance(value, GQLDB)
        except:
            cond = isinstance(value, SQLDB)
        if cond:
            dbs[key] = value
    return dbs


databases = get_databases(None)


def eval_in_global_env(text):
    exec ('_ret=%s' % text, {}, global_env)
    return global_env['_ret']


def get_database(request):
    if request.args and request.args[0] in databases:
        return eval_in_global_env(request.args[0])
    else:
        session.flash = T('invalid request')
        redirect(URL(r=request, f='index'))


def get_table(request):
    db = get_database(request)
    if len(request.args) > 1 and request.args[1] in db.tables:
        return (db, request.args[1])
    else:
        session.flash = T('invalid request')
        redirect(URL(r=request, f='index'))


def get_query(request):
    try:
        return eval_in_global_env(request.vars.query)
    except Exception:
        return None


def query_by_table_type(tablename,db=db,request=request):
    keyed = hasattr(db[tablename],'_primarykey')
    if keyed:
        firstkey = db[tablename][db[tablename]._primarykey[0]]
        cond = '>0'
        if firstkey.type in ['string', 'text']:
            cond = '!=""'
        qry = '%s.%s.%s%s' % (request.args[0], request.args[1], firstkey.name, cond)
    else:
        qry = '%s.%s.id>0' % tuple(request.args[:2])
    return qry



# ##########################################################
# ## list all databases and tables
# ###########################################################


def index():
    return dict(databases=databases)


# ##########################################################
# ## insert a new record
# ###########################################################


def insert():
    (db, table) = get_table(request)
    form = SQLFORM(db[table], ignore_rw=ignore_rw)
    if form.accepts(request.vars, session):
        response.flash = T('new record inserted')
    return dict(form=form,table=db[table])


# ##########################################################
# ## list all records in table and insert new record
# ###########################################################


def download():
    import os
    db = get_database(request)
    return response.download(request,db)

def csv():
    import gluon.contenttype
    response.headers['Content-Type'] = \
        gluon.contenttype.contenttype('.csv')
    db = get_database(request)
    query = get_query(request)
    if not query:
        return None
    response.headers['Content-disposition'] = 'attachment; filename=%s_%s.csv'\
         % tuple(request.vars.query.split('.')[:2])
    return str(db(query).select())


def import_csv(table, file):
    table.import_from_csv_file(file)

def select():
    import re
    db = get_database(request)
    dbname = request.args[0]
    regex = re.compile('(?P<table>\w+)\.(?P<field>\w+)=(?P<value>\d+)')
    if len(request.args)>1 and hasattr(db[request.args[1]],'_primarykey'):
        regex = re.compile('(?P<table>\w+)\.(?P<field>\w+)=(?P<value>.+)')
    if request.vars.query:
        match = regex.match(request.vars.query)
        if match:
            request.vars.query = '%s.%s.%s==%s' % (request.args[0],
                    match.group('table'), match.group('field'),
                    match.group('value'))
    else:
        request.vars.query = session.last_query
    query = get_query(request)
    if request.vars.start:
        start = int(request.vars.start)
    else:
        start = 0
    nrows = 0
    stop = start + 100
    table = None
    rows = []
    orderby = request.vars.orderby
    if orderby:
        orderby = dbname + '.' + orderby
        if orderby == session.last_orderby:
            if orderby[0] == '~':
                orderby = orderby[1:]
            else:
                orderby = '~' + orderby
    session.last_orderby = orderby
    session.last_query = request.vars.query
    form = FORM(TABLE(TR(T('Query:'), '', INPUT(_style='width:400px',
                _name='query', _value=request.vars.query or '',
                requires=IS_NOT_EMPTY(error_message=T("Cannot be empty")))), TR(T('Update:'),
                INPUT(_name='update_check', _type='checkbox',
                value=False), INPUT(_style='width:400px',
                _name='update_fields', _value=request.vars.update_fields
                 or '')), TR(T('Delete:'), INPUT(_name='delete_check',
                _class='delete', _type='checkbox', value=False), ''),
                TR('', '', INPUT(_type='submit', _value='submit'))),
                _action=URL(r=request,args=request.args))
    if request.vars.csvfile != None:
        try:
            import_csv(db[request.vars.table],
                       request.vars.csvfile.file)
            response.flash = T('data uploaded')
        except:
            response.flash = T('unable to parse csv file')
    if form.accepts(request.vars, formname=None):
#         regex = re.compile(request.args[0] + '\.(?P<table>\w+)\.id\>0')
        regex = re.compile(request.args[0] + '\.(?P<table>\w+)\..+')
        
        match = regex.match(form.vars.query.strip())
        if match:
            table = match.group('table')
        try:
            nrows = db(query).count()
            if form.vars.update_check and form.vars.update_fields:
                db(query).update(**eval_in_global_env('dict(%s)'
                                  % form.vars.update_fields))
                response.flash = T('%s rows updated', nrows)
            elif form.vars.delete_check:
                db(query).delete()
                response.flash = T('%s rows deleted', nrows)
            nrows = db(query).count()
            if orderby:
                rows = db(query).select(limitby=(start, stop),
                        orderby=eval_in_global_env(orderby))
            else:
                rows = db(query).select(limitby=(start, stop))
        except:
            (rows, nrows) = ([], 0)
            response.flash = T('Invalid Query')
    return dict(
        form=form,
        table=table,
        start=start,
        stop=stop,
        nrows=nrows,
        rows=rows,
        query=request.vars.query,
        )


# ##########################################################
# ## edit delete one record
# ###########################################################


def update():
    (db, table) = get_table(request)
    keyed = hasattr(db[table],'_primarykey')
    norec = True
    if keyed:
        key = [f for f in request.vars if f in db[table]._primarykey]
        if key:
            try:
              records = db(db[table][key[0]] == request.vars[key[0]]).select()
              if records:
                  record = records[0]
                  norec = False
            except:
                pass
        else:
            qry = query_by_table_type(table)
    else:
        try:
            id = int(request.args[2])
            record = db(db[table].id == id).select()[0]
            norec = False
        except:
            qry = query_by_table_type(table)

    if norec:
        session.flash = T('record does not exist')
        redirect(URL(r=request, f='select', args=request.args[:1],
                     vars=dict(query=qry)))
    
    if keyed:
        for k in db[table]._primarykey: 
            db[table][k].writable=False
    
    form = SQLFORM(db[table], record, deletable=True, delete_label=T('Check to delete'), 
                   ignore_rw=ignore_rw and not keyed,
                   linkto=URL(r=request, f='select',
                   args=request.args[:1]), upload=URL(r=request,
                   f='download', args=request.args[:1]))

    if form.accepts(request.vars, session):
        session.flash = T('done!')
        qry = query_by_table_type(table)
        redirect(URL(r=request, f='select', args=request.args[:1],
                 vars=dict(query=qry)))
    return dict(form=form,table=db[table])


# ##########################################################
# ## get global variables
# ###########################################################


def state():
    return dict()


