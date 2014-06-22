#!/usr/bin/python
#
# Simple version
# Generate IOS syntax for the policy named on the command line
# An advanced version might notice adjacent IP addresses and adjust the mask accordingly
#                              or might notice adjacent port numbers, and adjust accordingly

import os, sys
import csv, getopt
import bender

policy = sys.argv[1]

p_groups =  bender.policy_group('testdata/mock-poldb.csv')
sdp_groups = bender.policy_render('testdata/mock-sdpdb.csv')

# we check the policy groups to make sure it exists at all.
policy_lines = p_groups.select(name=policy)
if len(policy_lines) == 0:
    print "No policy",sys.argv[1]
    sys.exit(1)
# then loop through all the S/D/P data for that group
# we use "last_name" to determine when to do a "no ip accress list" statement
last_name = ''
for sdp in sdp_groups.select(group=policy):
    if sdp['name'] != last_name:
        print "no ip access-list %s" % (sdp['name'])
        print "ip access-list extended %s remark policy %s" % (sdp['name'], sdp['group'])
        last_name = sdp['name']
    print "ip access-list extended %s permit %s host %s host %s eq %s" % (
        last_name, sdp['protocol'], sdp['source_ip'], sdp['destination_ip'], sdp['port'])
