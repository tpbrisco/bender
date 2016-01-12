#!/usr/bin/python
#
"""Implement a simple database representing network policy
This allows the definition of "host groups" and "service templates"
and other structures which allow policy statements like
"Allow <Workstations> to access <SMTP> on <Servers>"
"""

import sys, io
import sqlalchemy as _sa
import csv as _csv
import time
import ConfigParser

# read "bender.cf" file - which has a staggaringly simple format right now
# [database]
# URI=....
# and that's it ...
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
        except ConfigParser as parse_err:
            print >>sys.stderr, "Exception %s reading %s from %s" % \
                (parse_err, section, file_list)
            dict1[option] = None
    return dict1

# generic "bender" object - it implements the logic for (a) dealing with different
# database formats (right now, CSV and MySQL/MariaDB), (b) enforcing required
# column entries, and (c) basic service routines (comuting "now", and kwargs
# transforms

class bender_io(object):
    """'Implements the base class for host_group, service_template,
    policy_group, and policy_render objects."""

    # Note: the following items should be defined in the derived objects
    # _pfx - the prefix for the table
    # _object_groups - the array of objects that are represented (hostsgroups, templates, etc)
    # _object_fields - the fields that are defined for each object
    # _object_dialect - (csv relevant only) - the dialect for the CSV file

    def __init__(self, engine_uri, table_name, mode, req_fields):
        """
        Initialize the object - use the engine_uri to determine the
	database type, table of to be used, mode for open and
	minimum required fields.

        engine_uri - URI format of <engine://<path>.
    			CSV and MySQL are supported.
    			Examples: csv://relative/path/table.csv,
				mysql://user:pass@localhost/table
        table_name - name of the table to be used - unused for CSV files
        mode        - mode to io.open() the file - unused for MySQL
        req_fields  - array of column names required for the database"""

        if engine_uri.split(':')[0] == 'csv':
            self._bo_engine_type = 'csv'
            self._init_csv(engine_uri, table_name, mode)
        elif engine_uri.split(':')[0] == 'mysql':
            self._bo_engine_type = 'mysql'
            self._init_sql(engine_uri, table_name, mode)
        else:
            raise TypeError('unknown engine type')

        # _host_fields() and _host_groups[] are defined now
        for field in req_fields:
            if not field in self._object_fields:
                raise NameError('field %s required' % (field))

    def _init_csv(self, engine_uri, table_name, mode):
        """CSV specific initialization
        engine_uri is the csv://<path to the file> to be opened
        table_name is the name of the table inside of the URI
        mode is the mode of the file open (usually 'wb')"""
        try:
            reader_fd = io.open(engine_uri.split('://')[1], mode)
            dialect = _csv.Sniffer().sniff(reader_fd.read(2048))
            reader_fd.seek(0)
            dreader = _csv.DictReader(reader_fd, dialect=dialect)
            self.table_name = table_name
        except:
            raise
        self._object_fields = dreader.fieldnames   # goes into parent namespace
        self._object_dialect = dreader.dialect
        for row in dreader:
            # cache the entire csv in memory
            self._object_groups.append(row)

    def _init_sql(self, engine_uri, table_name, mode):
        """MySQL specific initialization
        engine_uri is the engine URI - typically mysql://...
        mode is irrelevant for SQL
        req_fields is an array of the required fields"""
        try:
            self.meta_data = _sa.MetaData()
            self.engine = _sa.create_engine(engine_uri)
            self.connection = self.engine.connect()
            self.hostgroups = _sa.Table(table_name, self.meta_data,
                                        autoload=True, autoload_with=self.engine)
            self.table_name = table_name
        except:
            raise
        # initialize the column names
        self._object_fields = [str(c).replace(self.table_name + '.', '') \
                             for c in self.hostgroups.columns]

    def _kwarg2sel(self, **kwargs):
        """Given a set of kwargs, convert to a select statement"""
        sel_stmt = ''
        andp = ''
        for k in kwargs:
            sel_stmt = sel_stmt + andp + "%s.%s = \'%s\'" % (self.table_name, k, kwargs[k])
            andp = " and "
        return sel_stmt

    def _nowt_(self):
        """Form time-related statement for bi-temporal milestoning of the database"""
        return "%s.%svalid_from <= utc_timestamp() and %s.%svalid_to > utc_timestamp()" % \
            (self.table_name, self._pfx, self.table_name, self._pfx)

    def len_csv(self):
        """Return the length of the database"""
        return len(self._object_groups)

    def len_sql(self):
        """Return the length of the database"""
        try:
            i = self.hostgroups.count().where(self._nowt_())
        except _sa.exc.SQLAlchemyError as err:
            print err
            raise
        conn_result = self.connection.execute(i)
        return conn_result.scalar()

    def save_csv(self, table_name):
        """Save/Persist the database"""
        fields = self._object_fields
        w_fd = io.open(table_name, 'wb')
        dictw = _csv.DictWriter(w_fd, fields, dialect=self._object_dialect)
        dictw.writeheader()
        for row in self._object_groups:
            try:
                dictw.writerow(row)
            except:
                print "Writing row", row
                raise
        w_fd.close()
        return True

    def save_sql(self, table_name):
        """Save/Persist the database"""
        return True

    def update_csv(self, k_selection, k_update):
        """Update rows matched in dictionary k_selection, with fields in
        dictionary k_update"""
        for row in self._object_groups:
            # if we match all in k_selection
            #   update fields in k_update
            #
            # skip this row if we don't match it
            not_matched = 0
            for k in list(k_selection):
                if not (row[k] == k_selection[k]):
                    not_matched = 1
                    continue   # continue next "r in self._object_groups"
            if not_matched:
                continue
            for k in list(k_update):
                row[k] = k_update[k]  # update row based on k_update

    def update_sql(self, k_selection, k_update):
        """Update rows matched in dictionary k_selection with fields in
	dictionary k_update"""
        a_sel = self._kwarg2sel(**k_selection)
        a_sel = a_sel + " and " + self._nowt_()
        i = self.hostgroups.update().where(a_sel).values(k_update)
        return self.connection.execute(i)

    def add_csv(self, **kwargs):
        """Add a new member to the database, with the field values"""
        exists = self.select_csv(**kwargs)
        for e in exists:
            self.delete_csv(e)
        if not kwargs in self._object_groups:
            self._object_groups.append(kwargs)

    def add_sql(self, **kwargs):
        """Add a new member to the database, with the field values"""
        exists = self.select_sql(**kwargs)  # will match if fields are a subset of all _host_fields
        for e in exists:
            self.delete_sql(e)
        start_t = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
        kwargs['%svalid_from' % (self._pfx)] = start_t
        kwargs['%svalid_to' % (self._pfx)] = '2038-01-01 00:00:00' # close to max TIMESTAMP
        i = self.hostgroups.insert(values=kwargs)
        return self.connection.execute(i)

    def zero_csv(self):
        """Reset/clear the table"""
        while len(self._object_groups):
            self._object_groups.pop()

    def zero_sql(self):
        """Reset/clear the table"""
        # note that a "self.sdp.delete() is different from "self.delete({})".  The
        # self.sdp.delete() is a SQL (alchemy) operator to delete all rows, whereas
        # self.delete({}) leaves the rows, but updates the timestamps
        sql_del = self.delete_sql({})
        return sql_del

    def delete_csv(self, dmem):
        """Delete the member from the database"""
        return self._object_groups.remove(dmem)

    def delete_sql(self, dmem):
        """Delete the member from the database"""
        end_t = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
        a = self._kwarg2sel(**dmem)
        dmem["%svalid_to" % (self._pfx)] = end_t
        #
        i = self.hostgroups.update().where(a).values(dmem)
        return self.connection.execute(i)

    def select_csv(self, **kwargs):
        """Select a subset of the hostgroup database, indicated by the
        field/values"""
        def filter_obj(x_obj):
            for field in kwargs:
                if (x_obj[field]) and (kwargs[field] != x_obj[field]):
                    return None
            return x_obj
        return filter(filter_obj, self._object_groups)

    def select_sql(self, **kwargs):
        """Select a subset of the hostgroup database, indicated by the
        field/values"""
        a = self._kwarg2sel(**kwargs)
        andp = ''
        if len(a):
            andp = " and "
        # limit selects to current records
        a = a + andp + self._nowt_()
        try:
            s = self.hostgroups.select().where(a)
            rows = self.connection.execute(s)
        except _sa.exc.SQLAlchemyError as e:
            print e
            raise e
        r = []
        for row in rows:
            r.append(dict(row).copy())
        self._object_groups = r
        return r

    def __iter__(self):
        """Returns an iterator structure for moving thorugh the list of members"""
        return list.__iter__(self._object_groups)

    def fields(self):
        """Returns a list of the member fields"""
        return self._object_fields

class host_group(bender_io):
    """host_group(table_name)

    A host_group is a name with a number of (member) servers
    associated with it. Fieldnames for the host_groups are determined
    by inspecting the database, and making mimum assumptions.  That is;
    if you add a key to a database, it shouldn't require other code changes.
    Calling objects indicate which are required fields.  This object only
    requires hg_name, hg_member and hg_valid_from/hg_valid_to fields.
    An individual host may belong to multiple groups."""

    # _object_groups = []  # list of host_group dictionaries for cacheing
    # _object_fields = []     # list of field names in the dictionary
    # _object_dialect = ''    # if we're using CSV, this is the CSV "dialect"
    # _pfx = 'hg_'  	    # table column prefix - e.g. 'hg_name', etc

    # methods for each database type.
    _methods = {
        'len': {'mysql': 'len_sql', 'csv': 'len_csv'},
        'update': {'mysql': 'update_sql', 'csv': 'update_csv'},
        'add': {'mysql': 'add_sql', 'csv': 'add_csv'},
        'save': {'mysql': 'save_sql', 'csv': 'save_csv'},
        'delete': {'mysql': 'delete_sql', 'csv': 'delete_csv'},
        'select': {'mysql': 'select_sql', 'csv': 'select_csv'},
        'zero': {'mysql': 'zero_sql', 'csv': 'zero_csv'}
    }

    def __init__(self, engine_uri, table_name):
        """Define the host group based on the fields in the table_name.

        This peeks into the database specified by the engine_uri to get
        all column names.
        """

        # initialize instance information
        self._object_groups = []  # list of host_group dictionaries for cacheing
        self._object_fields = []     # list of field names in the dictionary
        self._object_dialect = ''    # if we're using CSV, this is the CSV "dialect"
        self._pfx = 'hg_'  	    # table column prefix - e.g. 'hg_name', etc

        # initialize object
        req_fields = ['hg_name', 'hg_member', 'hg_valid_from', 'hg_valid_to']
        super(host_group, self).__init__(engine_uri, table_name, 'rb', req_fields)

    @property
    def len(self):
        """Return length of the group database"""
        return getattr(super(host_group, self),
                       self._methods['len'][self._bo_engine_type])

    @property
    def zero(self):
        """Reset/clear the group data"""
        return getattr(super(host_group, self),
                       self._methods['zero'][self._bo_engine_type])

    @property
    def save(self):
        """Persist the group database"""
        return getattr(super(host_group, self),
                       self._methods['save'][self._bo_engine_type])

    @property
    def update(self):
        """Update rows matched in dictionary k_selection, with fields in
        dictionary k_update"""
        return getattr(super(host_group, self),
                       self._methods['update'][self._bo_engine_type])

    @property
    def add(self):
        """Add a new entry to the group database"""
        return getattr(super(host_group, self),
                       self._methods['add'][self._bo_engine_type])

    @property
    def delete(self):
        """Delete the indicated member from the group database"""
        return getattr(super(host_group, self),
                       self._methods['delete'][self._bo_engine_type])

    @property
    def select(self, **kwargs):
        """Select a subset of the hostgroup database, indicated by the
        field/values"""
        return getattr(super(host_group, self),
                       self._methods['select'][self._bo_engine_type])

    def __iter__(self):
        """Return an iterator structure for moving through the list
        of members"""
        return list.__iter__(self._object_groups)

    def fields(self):
        """Returns a list of the member fields"""
        return self._host_fields

#####
class service_template(bender_io):
    """service_template(table_name)

    A service_template is a pattern representing the communications
    protocols needed by an application.  Only 'name', 'port' and 'protocol'
    are required, though additional fields can help increase security."""

    _object_groups = []  # empty list of host_group dictionaries
    _object_fields = ()     # set of field names
    _object_dialect = ''    # dialect of CSV
    _pfx = 'st_'		# table name prefix - e.g. 'st_name', etc

    _methods = {
        'len': {'mysql': 'len_sql', 'csv': 'len_csv'},
        'update': {'mysql': 'update_sql', 'csv': 'update_csv'},
        'add': {'mysql': 'add_sql', 'csv': 'add_csv'},
        'save': {'mysql': 'save_sql', 'csv': 'save_csv'},
        'delete': {'mysql': 'delete_sql', 'csv': 'delete_csv'},
        'select': {'mysql': 'select_sql', 'csv': 'select_csv'},
        'zero': {'mysql': 'zero_sql', 'csv': 'zero_csv'}
    }

    def __init__(self, engine_uri, table_name):
        """
        Initialize the object - use the engine_uri to determine the
	database type, table of to be used, mode for open and
	minimum required fields.

        engine_uri - URI format of <engine://<path>.
    			CSV and MySQL are supported.
    			Examples: csv://relative/path/table.csv,
				mysql://user:pass@localhost/table
        table_name - name of the table to be used - unused for CSV files
        mode        - mode to io.open() the file - unused for MySQL
        req_fields  - array of column names required for the database"""

        # initialize object
        req_fields = ['st_name', 'st_port', 'st_valid_from', 'st_valid_to']
        super(service_template, self).__init__(engine_uri, table_name, 'rb', req_fields)

    @property
    def len(self):
        """Return length of the group database"""
        return getattr(super(service_template, self),
                       self._methods['len'][self._bo_engine_type])

    @property
    def zero(self):
        """Reset/clear the group data"""
        return getattr(super(service_template, self),
                       self._methods['zero'][self._bo_engine_type])

    @property
    def save(self):
        """Persist the group database"""
        return getattr(super(service_template, self),
                       self._methods['save'][self._bo_engine_type])

    @property
    def update(self):
        """Update rows matched in dictionary k_selection, with fields in
        dictionary k_update"""
        return getattr(super(service_template, self),
                       self._methods['update'][self._bo_engine_type])

    @property
    def add(self):
        """Add a new entry to the group database"""
        return getattr(super(service_template, self),
                       self._methods['add'][self._bo_engine_type])

    @property
    def delete(self):
        """Delete the indicated member from the group database"""
        return getattr(super(service_template, self),
                       self._methods['delete'][self._bo_engine_type])

    @property
    def select(self):
        """Select a subset of the hostgroup database, indicated by the
        field/values"""
        return getattr(super(service_template, self),
                       self._methods['select'][self._bo_engine_type])

    def __iter__(self):
        """Return an iterator structure for moving through the
        list of services"""
        return list.__iter__(self._object_groups)

    def fields(self):
        """Returns a list of the member fields"""
        return self._svc_fields

#####
class policy_group(bender_io):
    """policy_group(table_name)

    A policy group is a simple database of policy statements that use host
    groups and service templates defined in other bender calls.

    A policy group expresses
        "Source Group accesses Destination Group for Service"
    and gives a name to that statement."""

    _object_groups = [] # empty list of policy statements
    _object_fields = ()    # set of field names
    _object_dialect = ''   # dialect of the CSV file; if we're using one
    _pfx = 'p_'		   # table column prefix - e.g. "p_name", etc

    _methods = {
        'len': {'mysql': 'len_sql', 'csv': 'len_csv'},
        'update': {'mysql': 'update_sql', 'csv': 'update_csv'},
        'add': {'mysql': 'add_sql', 'csv': 'add_csv'},
        'save': {'mysql': 'save_sql', 'csv': 'save_csv'},
        'delete': {'mysql': 'delete_sql', 'csv': 'delete_csv'},
        'select': {'mysql': 'select_sql', 'csv': 'select_csv'},
        'zero': {'mysql': 'zero_sql', 'csv': 'zero_csv'}
    }

    def __init__(self, engine_uri, table_name):
        """
        Initialize the object - use the engine_uri to determine the
	database type, table of to be used, mode for open and
	minimum required fields.

        engine_uri - URI format of <engine://<path>.
    			CSV and MySQL are supported.
    			Examples: csv://relative/path/table.csv,
				mysql://user:pass@localhost/table
        table_name - name of the table to be used - unused for CSV files
        mode        - mode to io.open() the file - unused for MySQL
        req_fields  - array of column names required for the database"""

        # initialize object
        req_fields = ['p_name', 'p_source', 'p_destination', \
                          'p_template', 'p_valid_from', 'p_valid_to']
        super(policy_group, self).__init__(engine_uri, table_name, 'rb', req_fields)

    @property
    def len(self):
        """Return length of the group database"""
        return getattr(super(policy_group, self),
                       self._methods['len'][self._bo_engine_type])

    @property
    def zero(self):
        """Reset/clear the group data"""
        return getattr(super(policy_group, self),
                       self._methods['zero'][self._bo_engine_type])

    @property
    def save(self):
        """Persist the group database"""
        return getattr(super(policy_group, self),
                       self._methods['save'][self._bo_engine_type])

    @property
    def update(self):
        """Update rows matched in dictionary k_selection, with fields in
        dictionary k_update"""
        return getattr(super(policy_group, self),
                       self._methods['update'][self._bo_engine_type])

    @property
    def add(self):
        """Add a new entry to the group database"""
        return getattr(super(policy_group, self),
                       self._methods['add'][self._bo_engine_type])

    @property
    def delete(self):
        """Delete the indicated member from the group database"""
        return getattr(super(policy_group, self),
                       self._methods['delete'][self._bo_engine_type])

    @property
    def select(self):
        """Select a subset of the hostgroup database, indicated by the
        field/values"""
        return getattr(super(policy_group, self),
                       self._methods['select'][self._bo_engine_type])

    def __iter__(self):
        """Return an iterator structure for moving through the
        list of members"""
        return list.__iter__(self._object_groups)

    def fields(self):
        """Returns a list of the member fields"""
        return self._policy_fields

#####
class policy_render(bender_io):
    """Render policy statements into source/destination/protocol tuples.  This
    the output of policy statements at a point in time.  Comparisons can
    then be made to determine if updates to the environment are necessary"""

    _object_groups = []  # empty list of sdp dictionaries
    _object_fields = ()     # set of field names
    _object_dialect = ''    # dialect of the CSV file, if we're using one
    _pfx = 'sdp_'	 # table column prefix - e.g. 'sdp_name', etc

    _methods = {
        'len': {'mysql': 'len_sql', 'csv': 'len_csv'},
        'update': {'mysql': 'update_sql', 'csv': 'update_csv'},
        'add': {'mysql': 'add_sql', 'csv': 'add_csv'},
        'save': {'mysql': 'save_sql', 'csv': 'save_csv'},
        'delete': {'mysql': 'delete_sql', 'csv': 'delete_csv'},
        'select': {'mysql': 'select_sql', 'csv': 'select_csv'},
        'zero': {'mysql': 'zero_sql', 'csv': 'zero_csv'}
    }

    def __init__(self, engine_uri, table_name):
        """
        Initialize the object - use the engine_uri to determine the
	database type, table of to be used, mode for open and
	minimum required fields.

        engine_uri - URI format of <engine://<path>.
    			CSV and MySQL are supported.
    			Examples: csv://relative/path/table.csv,
				mysql://user:pass@localhost/table
        table_name - name of the table to be used - unused for CSV files
        mode        - mode to io.open() the file - unused for MySQL
        req_fields  - array of column names required for the database"""

        req_fields = ['sdp_group', 'sdp_source', 'sdp_destination', 'sdp_source_ip', \
                          'sdp_destination_ip', 'sdp_bidir', 'sdp_port', 'sdp_protocol', \
                          'sdp_valid_from', 'sdp_valid_to']
        super(policy_render, self).__init__(engine_uri, table_name, 'rb', req_fields)

    @property
    def len(self):
        """Return length of the group database"""
        return getattr(super(policy_render, self),
                       self._methods['len'][self._bo_engine_type])

    @property
    def zero(self):
        """Reset/clear the group data"""
        return getattr(super(policy_render, self),
                       self._methods['zero'][self._bo_engine_type])

    @property
    def save(self):
        """Persist the group database"""
        return getattr(super(policy_render, self),
                       self._methods['save'][self._bo_engine_type])

    @property
    def update(self):
        """Update rows matched in dictionary k_selection, with fields in
        dictionary k_update"""
        return getattr(super(policy_render, self),
                       self._methods['update'][self._bo_engine_type])

    @property
    def add(self):
        """Add a new entry to the group database"""
        return getattr(super(policy_render, self),
                       self._methods['add'][self._bo_engine_type])

    @property
    def delete(self):
        """Delete the policy from the database"""
        return getattr(super(policy_render, self),
                       self._methods['delete'][self._bo_engine_type])

    @property
    def select(self):
        """Select a subset of the hostgroup database, indicated by the
        field/values"""
        return getattr(super(policy_render, self),
                       self._methods['select'][self._bo_engine_type])

    def __iter__(self):
        """Return an iterator structure for moving through the list
        of members"""
        return list.__iter__(self._object_groups)

    def fields(self):
        """Returns a list of the member fields"""
        return self._sdp_fields

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
        for ems in email_srvrs:
            if w['hg_member'] == ems['hg_member']:
                continue
            for s in smtp:
                sr_name = w['hg_name']+"_"+ems['hg_name']+"_"+s['st_name']
                print "%s,%s,%s,%s/%s" % (sr_name, w['hg_member'], ems['hg_member'], \
                                          s['st_protocol'], s['st_port'])
                # get source/dest IP address
                try:
                    source_ip = gethostaddr(w['hg_member'])
                    destination_ip = gethostaddr(ems['hg_member'])
                except:
                    print "Not valid hostname", w['hg_member'], "or", ems['hg_member']
                    raise
                sr.add(sdp_group="fake", sdp_name=sr_name, sdp_source=w['hg_member'],
                       sdp_source_ip=source_ip, sdp_destination=ems['hg_member'],
                       sdp_destination_ip=destination_ip, sdp_port=s['st_port'],
                       sdp_protocol=s['st_protocol'])

    print "Total of", sr.len(), "SDP lines added"
    sr.save('testdata/mock-sdpdb.csv')
