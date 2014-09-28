#!/usr/bin/python
#
"""Implement a simple database representing network policy
This allows the definition of "host groups" and "service templates"
which allow policy statements like "Allow Workstations to access
SMTP on Servers"

While this version uses a CSV file, it should be easily
extensible to use more conventional databases.
"""

import sys
import csv as _csv
import sqlalchemy as _sa

class host_group:
    """host_group(table_name)

    A host_group as a name with a number of servers associated with it.
    Because this inspects the format of the database, it makes it easy to
    extend what is stored in the database, allowing many foreign key
    references for database reconciliation and meta-data.
    This requires only a "name" (of the host group) and "member" be defined.
    A server may belong to multiple groups. """

    _host_groups = []  # empty list of host_group dictionaries
    _host_fields = []     # empty list of field names in the dictionary

    def __init__(self,  engine_uri, table_name):
        """Define the host group based on the fields in the table_name.

       Peeking into the database specified by the engine_uri to get all
        columns; use the field names to generate a list of dictionary objects
        that can be managed.
        """

        # Open, reflect on the database to determine fields
        try:
            self.meta_data = _sa.MetaData()
            self.engine = _sa.create_engine(engine_uri)
            self.connection = self.engine.connect()
            self.hostgroups = _sa.Table(table_name, self.meta_data,
                                                       autoload=True, autoload_with=self.engine)
        except:
            raise

        # check to make sure that "name","member" at least exist
        self._host_fields = [str(c).replace('hostgroups.','') for c in self.hostgroups.columns]
        for req_field in ['hg_name', 'hg_member']:
            if not req_field in self._host_fields:
                print >>sys.stderr, "hostgroups: Need \"name\" and \"member\" columns"
                sys.exit(1)

        # don't need to load this into RAM - we can do a self.hostgroups.select() call
        ## Load the CSV into the _host_groups list of dictionaries
        ## for row in dreader:
            ## assemble the arguments in the right order
            ## self._host_groups.append(row)

    def save(self, table_name):
        """Persist (commit) changes to the database indicated"""
        # this is a no-op now - we use autocommit in sqlalchemy
        return

    def add(self, **kwargs):
        """Add a new member to the database, with the field values"""
        exists = self.select(**kwargs)    # will match partial
        for e in exists:
            self.delete(e)
        i = self.hostgroups.insert(values=kwargs)
        return self.connection.execute(i)
        # if not kwargs in self._host_groups:
         #   self._host_groups.append(kwargs)

    def delete(self, d):
        """Delete the member from the database"""
        a = self.__kwarg2sel(**d)
        i = self.hostgroups.delete(a)
        return self.connection.execute(i)

    def len(self):
        """Return the number of overall members stored"""
        try:
            i = self.hostgroups.count()
        except _sa.exc.SQLAlchemyError as e:
            print e
            raise
        c = self.connection.execute(i)
        return c.scalar()

    def __kwarg2sel(self, **kwargs):
        """Given a set of kwargs, convert to a select statement"""
        a=''
        andp=''
        for k in kwargs:
            a = a + andp + "hostgroups.%s = \'%s\'" % (k, kwargs[k])
            andp=" and "
        return a

    def select(self, **kwargs):
        """Select a subset of members, selected by the field/value criteria"""
        a = self.__kwarg2sel(**kwargs)
        s = self.hostgroups.select().where(a)            
        rows = self.connection.execute(s)
        r = []
        for row in rows:
            r.append(dict(row).copy())
        self._host_groups = r
        return r

    def __iter__(self):
        """Return an iterator structure for moving through the list
        of members"""
        return list.__iter__(self._host_groups)

    def fields(self):
        """Return the relevant member fields, in order"""
        return self._host_fields

#####
class service_template:
    """service_template(table_name)

    A service_template is a pattern representing the communications
    protocols needed by an application.  Only 'name', 'port' and 'protocol'
    are required, though additional fields can help increase security."""

    _svc_groups = []  # empty list of host_group dictionaries
    _svc_fields = ()     # set of field names

    def __init__(self, engine_uri, table_name):
        """Define the service_template based on the columns in the
        database.

        Peeking into the database to get all columns; use the
        field names to generate dictionary objects that can be managed."""

        # Open, Peek into the CSV, and create DictReader
        try:
            self.meta_data = _sa.MetaData()
            self.engine = _sa.create_engine(engine_uri)
            self.connection = self.engine.connect()
            self.services = _sa.Table(table_name, self.meta_data,
                                      autoload=True, autoload_with=self.engine)
        except:
            raise

        # check to make sure that "name" and "port" at least exist
        self._svc_fields = [str(c).replace('service_templates.','') for c in self.services.columns]
        for req_field in ['st_name', 'st_port']:
            if not req_field in self._svc_fields:
                print >>sys.stderr, "service_templates needs \"st_name\" and \"st_member\" columns in service template"
                sys.exit(1)

    def save(self, table_name):
        """Persist (commit) changes to the database indicated"""
        return

    def add(self, **kwargs):
        """Add a new service template to the database, with the field values"""
        exists = self.select(**kwargs)    # will match partial
        for e in exists:
            self.delete(e)
        i = self.services.insert(values=kwargs)
        return self.connection.execute(i)

    def delete(self, d):
        """Delete the service template line from the database"""
        a = self.__kwarg2sel(**d)
        i = self.services.delete(a)
        return self.connection.execute(i)

    def len(self):
        """Return the number of service lines (not templates) in the database"""
        try:
            i = self.services.count()
        except _sa.exc.SQLAlchemyError as e:
            print e
            raise
        c = self.connection.execute(i)
        return c.scalar()

    def __kwarg2sel(self, **kwargs):
        """Given a set of kwargs, convert to a select statement"""
        a=''
        andp=''
        for k in kwargs:
            a = a + andp + "service_templates.%s = \'%s\'" % (k, kwargs[k])
            andp=" and "
        return a

    def select(self, **kwargs):
        """Select a subset of services, indicated by the field/value criteria"""
        a = self.__kwarg2sel(**kwargs)
        try:
            s = self.services.select().where(a)
            rows = self.connection.execute(s)
        except OperationalError as o:
            print o
            raise
        r = []
        for row in rows:
            r.append(dict(row).copy())
        self._svc_groups = r
        return r

    def __iter__(self):
        """Return an iterator structure for moving through the
        list of services"""
        return list.__iter__(self._svc_groups)

    def fields(self):
        """Return the relevant member fields, in order"""
        return self._svc_fields

#####
class policy_group:
    """policy_group(table_name)

    A policy group is a simple database of policy statements that use host
    groups and service templates defined in other bender calls.

    A policy group expresses
        "Source Group accesses Destination Group for Service"
    and gives a name to that statement."""

    _policy_groups = [] # empty list of policy statements
    _policy_fields = ()    # set of field names

    def __init__(self, engine_uri,table_name):
        """Define the policy group based on the fields in the table_name.

        Peeking into the database to get all columns; use the field names
        to generate a list of dictionary objects that can be managed."""

        # Open, reflect on the database to get the columns
        try:
            self.meta_data = _sa.MetaData()
            self.engine = _sa.create_engine(engine_uri)
            self.connection = self.engine.connect()
            self.policies = _sa.Table(table_name, self.meta_data,
                                      autoload=True, autoload_with=self.engine)
        except:
            raise
        # make sure that name, source, destination, template all exist
        self._policy_fields = [str(c).replace('policy.','') for c in self.policies.columns]
        for req_field in ['p_name', 'p_source', 'p_destination', 'p_template']:
            if not req_field in self._policy_fields:
                print >>sys.stderr, "policy_groups: Required field", req_field, \
                    "not seen in", table_name
                sys.exit(1)

    def save(self, table_name):
        """Persist (commit) changes to the database indicated"""
        return

    def add(self, **kwargs):
        """Add a new policy to the database, with the field values"""
        exists = self.select(**kwargs)    # will match partial
        for e in exists:
            self.delete(e)
        i = self.policies.insert(values=kwargs)
        return self.connection.execute(i)

    def delete(self, d):
        """Delete the policy from the database"""
        a = self.__kwarg2sel(**d)
        i = self.policies.delete(a)
        return self.connection.execute(i)

    def len(self):
        """Return the number of overall members stored"""
        try:
            i = self.policies.count()
        except _sa.exc.SQLAlchemyError as e:
            print e
            raise
        c = self.connection.execute(i)
        return c.scalar()

    def __kwarg2sel(self, **kwargs):
        """Given a set of kwargs, convert to a select statement"""
        a=''
        andp=''
        for k in kwargs:
            a = a + andp + "policy.%s = \'%s\'" % (k, kwargs[k])
            andp=" and "
        return a        

    def select(self, **kwargs):
        """Return an array of selected policy groups based on the
        arguments passed in"""
        a = self.__kwarg2sel(**kwargs)
        try:
            s = self.policies.select().where(a)
            rows = self.connection.execute(s)
        except:
            raise
        r = []
        for row in rows:
            r.append(dict(row).copy())
        self._policy_groups = r
        return r

    def __iter__(self):
        """Return an iterator structure for moving through the
        list of members"""
        return list.__iter__(self._policy_groups)

    def fields(self):
        """Return the relevant member fields, in order"""
        return self._policy_fields

#####
class policy_render:
    """Render policy statements into source/destination/protocol tuples.  This
    the output of policy statements at a point in time.  Comparisons can
    then be made to determine if updates to the environment are necessary"""

    _sdp_groups = []  # empty list of sdp dictionaries
    _sdp_fields = ()     # set of field names

    def __init__(self, engine_uri, table_name):
        """Define the rendered policies in the named database."""

        try:
            self.meta_data = _sa.MetaData()
            self.engine = _sa.create_engine(engine_uri)
            self.connection = self.engine.connect()
            self.sdp = _sa.Table(table_name, self.meta_data,
                                        autoload=True, autoload_with=self.engine)
        except:
            raise
        # check to make sure that 'source', 'destination' and 'port' at least exist
        self._sdp_fields = [str(c).replace('sdp.','') for c in self.sdp.columns]
        for req_field in ['sdp_group', 'sdp_source', 'sdp_destination', 'sdp_source_ip', \
                          'sdp_destination_ip', 'sdp_bidir', 'sdp_port', 'sdp_protocol']:
            if not req_field in self._sdp_fields:
                print >>sys.stderr, "policy_render needs: ", req_field, "defined in the database"
                sys.exit(1)

    def len(self):
        """Return the number of rendered policy lines in the database"""
        try:
            i = self.sdp.count()
        except _sa_exc.SQLAlchemyError as e:
            print e
            raise
        c = self.connection.execute(i)
        return c.scalar()

    def __kwarg2sel(self, **kwargs):
        """Given a set of kwargs, convert to a select statement"""
        a=''
        andp=''
        for k in kwargs:
            a = a + andp + "sdp.%s = \'%s\'" % (k, kwargs[k])
            andp=" and "
        return a

    def __iter__(self):
        """Return an iterator structure for moving through the list of members"""
        return list.__iter__(self._sdp_groups)

    def fields(self):
        """Return the relevant member fields, in order"""
        return self._sdp_fields

    def zero(self):
        """Reset/clear the rendered policy data"""
        s = self.sdp.delete()
        i = self.connection.execute(s)

    def save(self, table_name):
        """Persist (commit) rendered policy to the database indicated"""
        return

    def add(self, **kwargs):
        """Add a new SDP member to the database, with the field values"""
        exists = self.select(**kwargs)  # matching partials
        for e in exists:
            self.delete(e)
        i = self.sdp.insert(values=kwargs)
        return self.connection.execute(i)

    def delete(self, d):
        """Delete the SDP line from the database"""
        a = self.__kwarg2sel(**d)
        i = self.sdp.delete(a)
        return self.connection.execute(i)

    def select(self, **kwargs):
        """Select the SDP sets, indicated by the field/value criteria"""
        a = self.__kwarg2sel(**kwargs)
        s = self.sdp.select().where(a)
        rows = self.connection.execute(s)
        r = []
        for row in rows:
            r.append(dict(row).copy())
        self._host_groups = r
        return r

####################
if __name__ == '__main__':
    import socket, sys

    if sys.argv[1] == '':
        # we need a "mysql://user:pass@localhost:3306/bender" for sqlalchemy
        print sys.argv[0],"<sqlalchemy URI>"
        sys.exit(1)
    db_uri = sys.argv[1]

    def gethostaddr(name):
        h_infos = socket.getaddrinfo(name, None, 0, 0, socket.SOL_TCP)
        if len(h_infos) < 0:
            raise
        return h_infos[0][4][0]

    # basic test of host_group objects
    ho = host_group(db_uri, 'hostgroups')
    print "Number of host groups", ho.len()
    #
    sel = ho.select(hg_member='ghidora')
    print "Groups referencing ghidora:", len(sel)
    for h in sel:
        print "\tPolicy:", h['hg_name']
        h['hg_owner'] = 'brisco'
    #
    print "Adding host group item, current len", ho.len()
    ho.add(hg_name='workstation', hg_member='ghidora', hg_type='none', \
           hg_owner='tomoso', hg_rp='tomoso')
    print "Added item to host groups, now len", ho.len()
    #
    ho.save('testdata/mock-hostdb.csv')

    #
    # basic test of service template object
    so = service_template(db_uri,'service_templates')
    print "Number of service templates", so.len()

    # Now read a default policy statement - "forward_mail"
    po = policy_group(db_uri,'policy')
    email_list = po.select(p_name='forward_email')
    email = email_list[0]
    print "Policy forward_email: %s can access %s on %s" % (email['p_source'],\
                                                            email['p_template'], email['p_destination'])

    # Now add a policy statement
    print "Adding policy for time service, policy length is", po.len()
    po.add(p_name='sync_time', p_source='workstation', p_destination='server',
           p_template='time', p_bidir='1')
    print "Added time policy, len now", po.len()
    po.save('testdata/mock-poldb.csv')

    # now, generate a SDP group for policy "forward_email" -
    #     "workstations access email on servers"
    wkstn = ho.select(hg_name=email['p_source'])
    email_srvrs = ho.select(hg_name=email['p_destination'])
    smtp = so.select(st_name=email['p_template'])

    sr = policy_render(db_uri, 'sdp')
    print "Rendered policies", sr.len()

    src_dst_list = sr.select(sdp_source='ghidora', sdp_destination='dracula')
    print "Select SDP for source=ghidora, destination=dracula"
    for s in src_dst_list:
        print "\t%s to %s on port %s/%s (%s)" % (s['sdp_source'], s['sdp_destination'],\
                                                 s['sdp_port'], s['sdp_protocol'], s['sdp_name'])

    for w in wkstn:
        for e in email_srvrs:
            if w['hg_member'] == e['hg_member']:
                continue
            for s in smtp:
                sr_name = w['hg_name']+"_"+e['hg_name']+"_"+s['st_name']
                print "%s,%s,%s,%s/%s" % (sr_name, w['hg_member'], e['hg_member'], \
                                          s['st_protocol'], s['st_port'])
                # get source/dest IP address
                try:
                    source_ip = gethostaddr(w['hg_member'])
                    destination_ip = gethostaddr(e['hg_member'])
                except:
                    print "Not valid hostname", w['hg_member'], "or", e['hg_member']
                    raise
                sr.add(sdp_group="fake", sdp_name=sr_name, sdp_source=w['hg_member'],
                       sdp_source_ip=source_ip, sdp_destination=e['hg_member'],
                       sdp_destination_ip=destination_ip, sdp_port=s['st_port'],
                       sdp_protocol=s['st_protocol'])

    print "Total of", sr.len(), "SDP lines added"
    sr.save('testdata/mock-sdpdb.csv')
