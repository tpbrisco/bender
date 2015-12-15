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
import sqlalchemy as _sa
import time
import ConfigParser

def read_config(section, file_list):
    """read_config(section, file_list)

    Read the bender configuration file list to initialize variables"""
    config = ConfigParser.ConfigParser()
    config.read(file_list)
    dict1 = {}
    options = config.options(section)
    for option in options:
        try:
            dict1[option] = config.get(section, option)
        except:
            print >>sys.stderr, "Exception reading %s from %s" % (section, file_list)
            dict1[option] = None
    return dict1

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

    def __init__(self, engine_uri, table_name):
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
            self.table_name = table_name
        except:
            raise

        # check to make sure that "name","member" at least exist
        self._host_fields = [str(c).replace(self.table_name + '.', '') \
                             for c in self.hostgroups.columns]
        for req_field in ['hg_name', 'hg_member', 'hg_valid_from', 'hg_valid_to']:
            if not req_field in self._host_fields:
                print >>sys.stderr, "host_group needs", req_field, \
                    "defined in table", self.table_name
                sys.exit(1)

    def save(self, table_name):
        """Persist (commit) changes to the database indicated"""
        # this is a no-op now - we use autocommit in sqlalchemy
        return

    def update(self, **kwargs):
        """Update fields to values indicated in kwargs"""
        a = self.__kwarg2sel(hg_name=self._host_groups[0]['hg_name'],
                             hg_member=self._host_groups[0]['hg_member'])
        a = a + " and hg_valid_from<=now() and hg_valid_to>=now()"
        print "hostgroup/update",a,"kwargs=",kwargs
        i = self.hostgroups.update().where(a).values(kwargs)
        return self.connection.execute(i)

    def add(self, **kwargs):
        """Add a new member to the database, with the field values"""
        exists = self.select(**kwargs)    # will match partial
        for e in exists:
            self.delete(e)
        start_t = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
        kwargs['hg_valid_from'] = start_t
        kwargs['hg_valid_to'] = '2038-01-01 00:00:00'  # close to maximum TIMESTAMP value
        i = self.hostgroups.insert(values=kwargs)
        return self.connection.execute(i)

    def delete(self, d):
        """Delete the member from the database"""
        end_t = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
        a = self.__kwarg2sel(**d)
        i = self.hostgroups.update().where(a).values(hg_valid_to=end_t)
        return self.connection.execute(i)

    def len(self):
        """Return the number of overall members stored"""
        now_t = "%s.hg_valid_from <= now() and %s.hg_valid_to >= now()" % \
                (self.table_name, self.table_name)
        try:
            i = self.hostgroups.count().where(now_t)
        except _sa.exc.SQLAlchemyError as e:
            print e
            raise
        c = self.connection.execute(i)
        return c.scalar()

    def __kwarg2sel(self, **kwargs):
        """Given a set of kwargs, convert to a select statement"""
        a = ''
        andp = ''
        for k in kwargs:
            if not kwargs[k]:
                continue
            a = a + andp + "%s.%s = \'%s\'" % (self.table_name, k, kwargs[k])
            andp = " and "
        # use the time fields hg_valid_from and hg_valid_to
        # a = a + " and hg_valid_from<=now() and hg_valid_to>=now()"
        return a

    def select(self, **kwargs):
        """Select a subset of members, selected by the field/value criteria"""
        now_t = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
        a = self.__kwarg2sel(**kwargs)
        andp = ''
        if len(a):
            andp = " and "
        # limit selects to current records
        a = a + andp + "%s.hg_valid_from <= \'%s\' and %s.hg_valid_to > \'%s\'" % \
            (self.table_name, now_t, self.table_name, now_t)
        try:
            s = self.hostgroups.select().where(a)
            rows = self.connection.execute(s)
        except _sa.exc.SQLAlchemyError as e:
            print e
            raise e
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
            self.table_name = table_name
        except _sa.exc.SQLAlchemyError as e:
            print e
            raise e

        # check to make sure that "name" and "port" at least exist
        self._svc_fields = [str(c).replace(self.table_name + '.', '') \
                            for c in self.services.columns]
        for req_field in ['st_name', 'st_port', 'st_valid_from', 'st_valid_to']:
            if not req_field in self._svc_fields:
                print >>sys.stderr, "service_template needs", req_field, \
                    "defined in table", self.table_name
                sys.exit(1)

    def save(self, table_name):
        """Persist (commit) changes to the database indicated"""
        return

    def update(self, **kwargs):
        """Update fields to values indicated in kwargs"""
        a = self.__kwargs2sel(st_name=self._svc_groups[0]['st_name'],
                              st_port=self._svc_groups[0]['st_port'],
                              st_protocol=self._svc_groups[0]['st_protocol']);
        a = a + "and st_valid_from<=now() and st_valid_to>=now()"
        i = self.services.update().where(a).values(kwargs)
        return self.connection.execute(i)

    def add(self, **kwargs):
        """Add a new service template to the database, with the field values"""
        exists = self.select(**kwargs)    # will match partial
        for e in exists:
            self.delete(e)
        start_t = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
        kwargs['st_valid_from'] = start_t
        kwargs['st_valid_to'] = '2038-01-01 00:00:00'
        i = self.services.insert(values=kwargs)
        return self.connection.execute(i)

    def delete(self, d):
        """Delete the service template line from the database"""
        end_t = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
        a = self.__kwarg2sel(**d)
        i = self.services.update().where(a).values(st_valid_to=end_t)
        return self.connection.execute(i)

    def len(self):
        """Return the number of service lines (not templates) in the database"""
        now_t = "%s.st_valid_from <= now() and %s.st_valid_to >= now()" % \
                (self.table_name, self.table_name)
        try:
            i = self.services.count().where(now_t)
        except _sa.exc.SQLAlchemyError as e:
            print e
            raise
        c = self.connection.execute(i)
        return c.scalar()

    def __kwarg2sel(self, **kwargs):
        """Given a set of kwargs, convert to a select statement"""
        a = ''
        andp = ''
        for k in kwargs:
            if not kwargs[k]:
                continue
            a = a + andp + "%s.%s = \'%s\'" % (self.table_name, k, kwargs[k])
            andp = " and "
        # a = a + " and st_valid_from<=now() and st_valid_to>=now()"
        return a

    def select(self, **kwargs):
        """Select a subset of services, indicated by the field/value criteria"""
        now_t = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
        a = self.__kwarg2sel(**kwargs)
        andp = ''
        if len(a):
            andp = " and "
        # limit searches to current records
        a = a + andp + "%s.st_valid_from <= \'%s\' and %s.st_valid_to > \'%s\'" % \
            (self.table_name, now_t, self.table_name, now_t)
        try:
            s = self.services.select().where(a)
            rows = self.connection.execute(s)
        except _sa.exc.SQLAlchemyError as e:
            print e
            raise e
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

    def __init__(self, engine_uri, table_name):
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
            self.table_name = table_name
        except _sa.exc.SQLAlchemyError as e:
            print e
            raise e
        # make sure that name, source, destination, template all exist
        self._policy_fields = [str(c).replace(self.table_name + '.', '') \
                               for c in self.policies.columns]
        for req_field in ['p_name', 'p_source', 'p_destination', \
                          'p_template', 'p_valid_from', 'p_valid_to']:
            if not req_field in self._policy_fields:
                print >>sys.stderr, "policy_group needs", req_field, \
                    "defined in table", self.table_name
                sys.exit(1)

    def save(self, table_name):
        """Persist (commit) changes to the database indicated"""
        return

    def update(self, **kwargs):
        """Update fields to values indicated in kwargs"""
        a = self.__kwargs2sel(p_name=self._policy_groups[0]['p_name'],
                              p_port=self._policy_groups[0]['p_template'])
        a = a + "and p_valid_from<=now() and p_valid_to>=now()"
        i = self.policies.update().where(a).values(kwargs)
        return self.connection.execute(i)

    def add(self, **kwargs):
        """Add a new policy to the database, with the field values"""
        exists = self.select(**kwargs)    # will match partial
        for e in exists:
            self.delete(e)
        start_t = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
        kwargs['p_valid_from'] = start_t
        kwargs['p_valid_to'] = '2038-01-01 00:00:00'
        i = self.policies.insert(values=kwargs)
        return self.connection.execute(i)

    def delete(self, d):
        """Delete the policy from the database"""
        end_t = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
        a = self.__kwarg2sel(**d)
        i = self.policies.update().where(a).values(p_valid_to=end_t)
        return self.connection.execute(i)

    def len(self):
        """Return the number of overall members stored"""
        now_t = "%s.p_valid_from <= now() and %s.p_valid_to >= now()" % \
                (self.table_name, self.table_name)
        try:
            i = self.policies.count().where(now_t)
        except _sa.exc.SQLAlchemyError as e:
            print e
            raise
        c = self.connection.execute(i)
        return c.scalar()

    def __kwarg2sel(self, **kwargs):
        """Given a set of kwargs, convert to a select statement"""
        a = ''
        andp = ''
        for k in kwargs:
            if not kwargs[k]:
                continue
            a = a + andp + "%s.%s = \'%s\'" % (self.table_name, k, kwargs[k])
            andp = " and "
        # a = a + " and p_valid_from<=now() and p_valid_to>=now()"
        return a

    def select(self, **kwargs):
        """Return an array of selected policy groups based on the
        arguments passed in"""
        now_t = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
        a = self.__kwarg2sel(**kwargs)
        andp = ''
        if len(a):
            andp = " and "
        # limit select to current records
        a = a + andp + "%s.p_valid_from <= \'%s\' and %s.p_valid_to > \'%s\'" % \
            (self.table_name, now_t, self.table_name, now_t)
        try:
            s = self.policies.select().where(a)
            rows = self.connection.execute(s)
        except _sa.exc.SQLAlchemyError as e:
            print e
            raise e
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
            self.table_name = table_name
        except _sa.exc.SQLAlchemyError as e:
            print e
            raise e
        # check to make sure that 'source', 'destination' and 'port' at least exist
        self._sdp_fields = [str(c).replace(self.table_name + '.', '') \
                            for c in self.sdp.columns]
        for req_field in ['sdp_group', 'sdp_source', 'sdp_destination', 'sdp_source_ip', \
                          'sdp_destination_ip', 'sdp_bidir', 'sdp_port', 'sdp_protocol', 'sdp_valid_from',\
                          'sdp_valid_to']:
            if not req_field in self._sdp_fields:
                print >>sys.stderr, "policy_render needs", req_field, \
                    "defined in table", self.table_name
                sys.exit(1)

    def len(self):
        """Return the number of rendered policy lines in the database"""
        now_t = "%s.sdp_valid_from <= now() and %s.sdp_valid_to >= now()" % \
                (self.table_name, self.table_name)
        try:
            i = self.sdp.count()
        except _sa_exc.SQLAlchemyError as e:
            print e
            raise e
        c = self.connection.execute(i)
        return c.scalar()

    def __kwarg2sel(self, **kwargs):
        """Given a set of kwargs, convert to a select statement"""
        a = ''
        andp = ''
        for k in kwargs:
            if not kwargs[k]:
                continue
            a = a + andp + "%s.%s = \'%s\'" % (self.table_name, k, kwargs[k])
            andp = " and "
        # a = a + " and sdp_valid_from<=utc_timestamp() and sdp_valid_to>=utc_timestamp()"
        return a

    def __iter__(self):
        """Return an iterator structure for moving through the list of members"""
        return list.__iter__(self._sdp_groups)

    def fields(self):
        """Return the relevant member fields, in order"""
        return self._sdp_fields

    def zero(self):
        """Reset/clear the rendered policy data"""
        # note that a "self.sdp.delete()" is different from "self.delete({})".  The
        # self.sdp.delete() is a SQL (alchemy) operator to delete all rows, whereas
        # self.delete({}) leaves the rows but updates the timestamps
        s = self.delete({})   # delete method tombstones it all
        return s

    def save(self, table_name):
        """Persist (commit) rendered policy to the database indicated"""
        return

    def update(self, **kwargs):
        """Update fields to values indicated in kwargs"""
        a = self.__kwargs2sel(sdp_group=self._sdp_groups[0]['sdp_group'],
                              sdp_name=self._sdp_groups[0]['sdp_name'])
        a = a + "and sdp_valid_from<=now() and sdp_valid_to>=now()"
        i = self.sdp.update().where(a).values(kwargs)
        return self.connection.execute(i)

    def add(self, **kwargs):
        """Add a new SDP member to the database, with the field values"""
        exists = self.select(**kwargs)  # matching partials
        for e in exists:
            self.delete(e)
        start_t = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
        kwargs['sdp_valid_from'] = start_t
        kwargs['sdp_valid_to'] = '2038-01-01 00:00:00'
        i = self.sdp.insert(values=kwargs)
        return self.connection.execute(i)

    def delete(self, d):
        """Delete the SDP line from the database"""
        end_t = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
        a = self.__kwarg2sel(**d)
        i = self.sdp.update().where(a).values(sdp_valid_to=end_t)
        return self.connection.execute(i)

    def select(self, **kwargs):
        """Select the SDP sets, indicated by the field/value criteria"""
        now_t = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
        a = self.__kwarg2sel(**kwargs)
        andp = ''
        if len(a):
            andp = " and "
        # limit selects to current records
        a = a + andp + "%s.sdp_valid_from <= \'%s\' and %s.sdp_valid_to > \'%s\'" % \
            (self.table_name, now_t, self.table_name, now_t)
        try:
            s = self.sdp.select().where(a)
            rows = self.connection.execute(s)
        except _sa.exc.SQLAlchemyError as e:
            print e
            raise e
        r = []
        for row in rows:
            r.append(dict(row).copy())
        self._sdp_groups = r
        return r

####################
if __name__ == '__main__':
    import socket, sys

    if sys.argv[1] == '':
        # we need a "mysql://user:pass@localhost:3306/bender" for sqlalchemy
        print sys.argv[0], "<sqlalchemy URI>"
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
    so = service_template(db_uri, 'service_templates')
    print "Number of service templates", so.len()

    # Now read a default policy statement - "forward_mail"
    po = policy_group(db_uri, 'policy')
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
