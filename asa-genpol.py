#!/usr/bin/python
#
# Simple version
# Generate ASA 'service' and 
#
# Instead of using the pre-generated 'SDP' database, this reads directly from
# the policy database -- since the ASA allows us to define service groups and
# host groups, this will be much cleaner to read.

import os, sys
import getopt
import bender

if len(sys.argv) < 2:
    print "Usage: asa-genpol <policy name>"
    sys.exit(1)

policy = sys.argv[1]

p_groups = bender.policy_group('testdata/mock-poldb.csv')
h_groups = bender.host_group('testdata/mock-hostdb.csv')
s_groups = bender.service_template('testdata/mock-svcdb.csv')

policy_lines = p_groups.select(name=policy)
if len(policy_lines) == 0:
    print "No policy",sys.argv[1]
    sys.exit(1)

def uniq_values(list, key):
    seen = set()
    for x in list:
        if x[key] not in seen:
            seen.add(x[key])
    return seen

# For all of the service/protocol combinations, build up the ASA namespace, and
# print out all of the service object definitions
service_names = uniq_values(policy_lines, 'template')
asa_service_names = []
for service_name in service_names:
    svc_list = s_groups.select(name=service_name)
    for svc_prot_name in uniq_values(svc_list, 'protocol'):
        obj_name = service_name+"-"+svc_prot_name
        if obj_name not in asa_service_names:
            asa_service_names.append(obj_name)
            print "object-group service %s %s" % (obj_name, svc_prot_name)
            svc = s_groups.select(name=service_name, protocol=svc_prot_name)
            for s in svc:
                print "\tport-object",s['port']

# For all of the hosts in groups, build up the ASA namespace, and
# print out all of the host object definitions
host_group_names_src = uniq_values(policy_lines, 'source')
host_group_names_dst = uniq_values(policy_lines, 'destination')
asa_host_names = []
for host_group_name in host_group_names_src.union(host_group_names_dst):
    if host_group_name not in asa_host_names:
        print "object-group network %s" % (host_group_name)
        host_groups = h_groups.select(name=host_group_name)
        for h in host_groups:
            print "\tnetwork-object host", h['member']

# now the "easy" part - rip through the policy line by line, printing it out
for policy_line in policy_lines:
#    print "line:",policy_line
    template_name = policy_line['template']
    if template_name+"-tcp" in asa_service_names:
        print "access-list %s permit tcp object-group %s object-group %s object-group %s" % (\
                    policy_line['name'],policy_line['source'], \
                    template_name+"-tcp", policy_line['destination'])
    if template_name+"-udp" in asa_service_names:
        print "access-list %s  permit udp object-group %s object-group %s object-group %s" % (\
                    policy_line['name'],policy_line['source'],
                     template_name+"-udp", policy_line['destination'])
