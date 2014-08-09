#!/usr/bin/python
#
# Simple version
# Generate IOS syntax for the policy named on the command line
# An advanced version might notice adjacent IP addresses and adjust the mask accordingly
#                              or might notice adjacent port numbers, and adjust accordingly

import os, sys
import getopt
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
# we use "last_name" to determine when to do a "no ip accress list" statement.
# This simply accrues output in an output buffer, and when "last_name" changes,
# we print it all out (since we're potentially dealing with "in" and "out" polices).
last_name = ''
output_in = ""     # buffered output for "in" policy
output_out = ""   # buffered output for "out" policy
for sdp in sdp_groups.select(group=policy):
    if sdp['name'] != last_name:
        # print out buffered policy
        if not output_out == "":
            print output_out
            output_out = ""
        if not output_in == "":
            print output_in
            output_in = ""
        # start forming new policy
        output_out = "no ip access-list %s\n" % (sdp['name'])
        output_out = output_out + "ip access-list extended %s remark policy %s\n" % (sdp['name'], sdp['group'])
        # start forming the reverse policy, if we need it
        if sdp['direction'] == 'b':  # bidirectional connection - we need to reverse it
            output_in = "no ip access-list %s_in\n" % (sdp['name'])
            output_in = output_in + "ip access-list extended %s_in remark policy %s\n" % (sdp['name'], sdp['group'])
        last_name = sdp['name']
    output_out = output_out + "ip access-list extended %s permit %s host %s host %s eq %s\n" % (
        last_name, sdp['protocol'], sdp['source_ip'], sdp['destination_ip'], sdp['port'])
    # if we need a "bidirectional" (direction=b) entry, form the reverse
    if sdp['direction'] == 'b':
        # note we just reverse the source/destination for this
        output_in = output_in + "ip access-list extended %s permit %s host %s host %s eq %s\n" % (
            last_name,sdp['protocol'],sdp['destination_ip'],sdp['source_ip'], sdp['port'])
