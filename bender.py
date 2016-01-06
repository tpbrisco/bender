#!/usr/bin/python
#
"""Implement a simple database representing network policy
This allows the definition of "host groups" and "service templates"
which allow policy statements like "Allow Workstations to access
SMTP on Servers"

While this version uses a CSV file, it should be easily
extensible to use more conventional databases.
"""

import sys, io
import csv as _csv

class host_group:
    """host_group(table_name)

    A host_group as a name with a number of servers associated with it.
    Because this inspects the format of the database, it makes it easy to
    extend what is stored in the database, allowing many foreign key
    references for database reconciliation and meta-data.
    This requires only a "name" (of the host group) and "member" be defined.
    A server may belong to multiple groups. """

    _host_groups = []  # empty list of host_group dictionaries
    _host_fields = ()     # set of field names
    _host_dialect = ''    # dialect of CSV file

    def __init__(self, uri, table_name):
        """Define the host group based on the fields in the table_name.

       Peeking into the database to get all columns; use the field names
        to generate a list of dictionary objects that can be managed.
        """

        self.table_name = table_name
        engine, table_name = uri.split(':')
        # Open, Peek into the CSV, and create DictReader
        try:
            reader_fd = io.open(table_name, 'rb')
            dialect = _csv.Sniffer().sniff(reader_fd.read(1024))
            reader_fd.seek(0)
            dreader = _csv.DictReader(reader_fd, dialect=dialect)
        except:
            raise

        # check to make sure that "name","member" at least exist
        self._host_fields = dreader.fieldnames
        self._host_dialect = dreader.dialect
        for req_field in ['hg_name', 'hg_member']:
            if not req_field in self._host_fields:
                print >>sys.stderr, "hostdb needs \"name\" and \"member\" columns"
                sys.exit(1)

        # Load the CSV into the _host_groups list of dictionaries
        for row in dreader:
            # assemble the arguments in the right order
            self._host_groups.append(row)

    def save(self, table_name):
        """Persist (commit) changes to the database indicated"""
        fields = self._host_fields
        w_fd = io.open(table_name, 'wb')
        dw = _csv.DictWriter(w_fd, fields, dialect=self._host_dialect)
        dw.writeheader()
        for r in self._host_groups:
            try:
                dw.writerow(r)
            except:
                print "Writing row", r
                raise
        w_fd.close()

    def add(self, **kwargs):
        """Add a new member to the database, with the field values"""
        exists = self.select(**kwargs)    # will match partial
        for e in exists:
            self.delete(e)
        if not kwargs in self._host_groups:
            self._host_groups.append(kwargs)

    def delete(self, d):
        """Delete the member from the database"""
        return self._host_groups.remove(d)

    def len(self):
        """Return the number of overall members stored"""
        return len(self._host_groups)

    def select(self, **kwargs):
        """Select a subset of members, selected by the field/value criteria"""
        def f(x):
            for field in kwargs:
                if (x[field]) and (kwargs[field] != x[field]):
                    return None
            return x
        return filter(f, self._host_groups)

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
    _svc_dialect = ''    # dialect of CSV

    def __init__(self, uri, table_name):
        """Define the service_template based on the columns in the
        database.

        Peeking into the database to get all columns; use the
        field names to generate dictionary objects that can be managed."""

        self.table_name = table_name
        engine, table_name = uri.split(':')
        # Open, Peek into the CSV, and create DictReader
        try:
            reader_fd = io.open(table_name, 'rb')
            dialect = _csv.Sniffer().sniff(reader_fd.read(1024))
            reader_fd.seek(0)
            dreader = _csv.DictReader(reader_fd, dialect=dialect)
        except:
            raise

        # check to make sure that "name" and "port" at least exist
        self._svc_fields = dreader.fieldnames
        self._svc_dialect = dreader.dialect
        for req_field in ['st_name', 'st_port']:
            if not req_field in self._svc_fields:
                print >>sys.stderr, "Server templates need \"name\" and \"member\" columns"
                sys.exit(1)

        # Load the CSV into the _svc_groups list of dictionaries
        for row in dreader:
            # assemble the arguments in the right order
            self._svc_groups.append(row)

    def save(self, table_name):
        """Persist (commit) changes to the database indicated"""
        fields = self._svc_fields
        w_fd = io.open(table_name, 'wb')
        dw = _csv.DictWriter(w_fd, fields, dialect=self._svc_dialect)
        dw.writeheader()
        for r in self._svc_groups:
            dw.writerow(r)
        w_fd.close()

    def add(self, **kwargs):
        """Add a new service template to the database, with the field values"""
        exists = self.select(**kwargs)    # will match partial
        for e in exists:
            self.delete(e)
        if not kwargs in self._svc_groups:
            self._svc_groups.append(kwargs)

    def delete(self, d):
        """Delete the service template line from the database"""
        return self._svc_groups.remove(d)

    def len(self):
        """Return the number of service lines (not templates) in the database"""
        return len(self._svc_groups)

    def select(self, **kwargs):
        """Select a subset of services, indicated by the field/value criteria"""
        def f(x):
            for field in kwargs:
                if (x[field]) and (kwargs[field] != x[field]):
                    return None
            return x
        return filter(f, self._svc_groups)

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
    _policy_dialect = ''   # dialect of CSV

    def __init__(self, uri, table_name):
        """Define the policy group based on the fields in the table_name.

        Peeking into the database to get all columns; use the field names
        to generate a list of dictionary objects that can be managed."""

        self.table_name = table_name
        engine, table_name = uri.split(':')
        # Open, peek into the CSV and create DictReader
        try:
            reader_fd = io.open(table_name, 'rb')
            dialect = _csv.Sniffer().sniff(reader_fd.read(1024))
            reader_fd.seek(0)
            dreader = _csv.DictReader(reader_fd, dialect=dialect)
        except:
            raise

        # make sure that name, source, destination, template all exist
        self._policy_fields = dreader.fieldnames
        self._policy_dialect = dreader.dialect
        for req_field in ['p_name', 'p_source', 'p_destination', 'p_template']:
            if not req_field in self._policy_fields:
                print >>sys.stderr, "Policy groups need ", req_field, \
                    "not seen in", table_name
                sys.exit(1)

        # Load the CSV into the _policy_groups list of dictionaries
        for row in dreader:
            self._policy_groups.append(row)

    def save(self, table_name):
        """Persist (commit) changes to the database indicated"""
        fields = self._policy_fields
        w_fd = io.open(table_name, 'wb')
        dw = _csv.DictWriter(w_fd, fields, dialect=self._policy_dialect)
        dw.writeheader()
        for r in self._policy_groups:
            try:
                dw.writerow(r)
            except:
                print "Writing row", r
                raise
        w_fd.close()

    def add(self, **kwargs):
        """Add a new policy to the database, with the field values"""
        exists = self.select(**kwargs)    # will match partial
        for e in exists:
            self.delete(e)
        if not kwargs in self._policy_groups:
            self._policy_groups.append(kwargs)

    def delete(self, d):
        """Delete the policy from the database"""
        return self._policy_groups.remove(d)

    def len(self):
        """Return the number of overall members stored"""
        return len(self._policy_groups)

    def select(self, **kwargs):
        """Return an array of selected policy groups based on the
        arguments passed in"""
        def f(x):
            for field in kwargs:
                if (x[field] != '') and (kwargs[field] != x[field]):
                    return None
            return x
        return filter(f, self._policy_groups)

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
    _sdp_dialect = ''    # remember dialect type

    def __init__(self, uri,  table_name):
        """Define the rendered policies in the named database."""

        self.table_name = table_name
        engine, table_name = uri.split(':')

        try:
            sdp_fd = io.open(table_name, 'rb')
            dialect = _csv.Sniffer().sniff(sdp_fd.read(2048), delimiters=',')
            sdp_fd.seek(0)
            dreader = _csv.DictReader(sdp_fd, dialect=dialect)
        except:
            raise
        # check to make sure that 'source', 'destination' and 'port' at least exist
        self._sdp_fields = dreader.fieldnames
        self._sdp_dialect = dreader.dialect

        for req_field in ['sdp_group', 'sdp_source', 'sdp_destination', 'sdp_source_ip', \
                          'sdp_destination_ip', 'sdp_bidir', 'sdp_port', 'sdp_protocol']:
            if not req_field in self._sdp_fields:
                print >>sys.stderr, "SDP needs", req_field, "defined in the database"
                sys.exit(1)

        # load the CSV into the _sdp_groups list of dictionaries
        for row in dreader:
            self._sdp_groups.append(row)

    def len(self):
        """Return the number of rendered policy lines in the database"""
        # if '_sdp_groups' not in locals():
        #    return 0
        return len(self._sdp_groups)

    def __iter__(self):
        """Return an iterator structure for moving through the list of members"""
        return list.__iter__(self._sdp_groups)

    def fields(self):
        """Return the relevant member fields, in order"""
        return self._sdp_fields

    def zero(self):
        """Reset/clear the rendered policy data"""
        while len(self._sdp_groups):
            self._sdp_groups.pop()

    def save(self, table_name):
        """Persist (commit) rendered policy to the database indicated"""
        fields = self._sdp_fields
        w_fd = io.open(table_name, 'wb')
        dw = _csv.DictWriter(w_fd, fields, dialect=self._sdp_dialect)
        dw.writeheader()
        for r in self._sdp_groups:
            dw.writerow(r)
        w_fd.close()

    def add(self, **kwargs):
        """Add a new SDP member to the database, with the field values"""
        exists = self.select(**kwargs)      # will match on all fields
        for e in exists:
            self.delete(e)
        if not kwargs in self._sdp_groups:
            self._sdp_groups.append(kwargs)

    def delete(self, d):
        """Delete the SDP line from the database"""
        return self._sdp_groups.remove(d)

    def select(self, **kwargs):
        """Select the SDP sets, indicated by the field/value criteria"""
        def f(x):
            for field in kwargs:
                if (x[field]) and (kwargs[field] != x[field]):
                    return None
            return x
        return filter(f, self._sdp_groups)

####################
if __name__ == '__main__':
    import socket

    # basic test of host_group objects
    ho = host_group('testdata/mock-hostdb.csv')
    print "Number of host groups", ho.len()
    #
    sel = ho.select(member='ghidora')
    print "Groups referencing ghidora:", len(sel)
    for h in sel:
        print "\tPolicy:", h['name']
        h['owner'] = 'brisco'
    #
    print "Adding host group item, current len", ho.len()
    ho.add(name='workstation', member='ghidora', type='none', \
           owner='tomoso', rp='tomoso')
    print "Added item to host groups, now len", ho.len()
    #
    ho.save('testdata/mock-hostdb.csv')

    #
    # basic test of service template object
    so = service_template('testdata/mock-svcdb.csv')
    print "Number of service templates", so.len()

    # Now read a default policy statement - "forward_mail"
    po = policy_group('testdata/mock-poldb.csv')
    email_list = po.select(name='forward_email')
    email = email_list[0]
    print "Policy forward_email: %s can access %s on %s" % (email['source'],\
                                                            email['template'], email['destination'])

    # Now add a policy statement
    print "Adding policy for time service, policy length is", po.len()
    po.add(name='sync_time', source='workstation', destination='server', template='time')
    print "Added time policy, len now", po.len()
    po.save('testdata/mock-poldb.csv')

    # now, generate a SDP group for policy "forward_email" -
    #     "workstations access email on servers"
    wkstn = ho.select(name=email['source'])
    email_srvrs = ho.select(name=email['destination'])
    smtp = so.select(name=email['template'])

    sr = policy_render('testdata/mock-sdpdb.csv')
    print "Rendered policies", sr.len()

    src_dst_list = sr.select(source='ghidora', destination='dracula')
    print "Select SDP for source=ghidora, destination=dracula"
    for s in src_dst_list:
        print "\t%s to %s on port %s/%s (%s)" % (s['source'], s['destination'],\
                                                 s['port'], s['protocol'], s['name'])

    for w in wkstn:
        for e in email_srvrs:
            if w['member'] == e['member']:
                continue
            for s in smtp:
                sr_name = w['name']+"_"+e['name']+"_"+s['name']
                print "%s,%s,%s,%s/%s" % (sr_name, w['member'], e['member'], \
                                          s['protocol'], s['port'])
                # get source/dest IP address
                try:
                    source_ip = socket.gethostbyname(w['member'])
                    destination_ip = socket.gethostbyname(e['member'])
                except:
                    print "Not valid hostname", w['member'], "or", e['member']
                    raise
                sr.add(group="fake", name=sr_name, source=w['member'],
                       source_ip=source_ip, destination=e['member'],
                       destination_ip=destination_ip, port=s['port'], protocol=s['protocol'])

    print "Total of", sr.len(), "SDP lines added"
    sr.save('testdata/mock-sdpdb.csv')
