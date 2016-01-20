#!/usr/bin/python
#
# Simple version
# Generate IPTables access list - suitable for hooking onto INPUT and OUTPUT policies
#
# This uses the pre-generated "SDP" tables to generate

import sys
import bender_obj as bender

if len(sys.argv) < 2:
    print "Usage: iptable-genpol <policy name>"
    sys.exit(1)

sdp_group = sys.argv[1]

pol_db_cfg = bender.read_config("database", ['/etc/bender.cf', 'bender.cf'])

sdp_entries = bender.policy_render(pol_db_cfg['uri'], 'sdp')

sdp_lines = sdp_entries.select(sdp_group=sdp_group)
if len(sdp_lines) == 0:
    print "Nothing in group", sys.argv[1]
    sys.exit(1)

def uniq_values(listv, key):
    seen = set()
    for x in listv:
        if x[key] not in seen:
            seen.add(x[key])
    return seen

# Set up iptables --
#  1) make sure the "default_drop" chain is in place
#  2) clear the INPUT chain of references to this rule we're generating
#  3) update/create the chain we want
#  4) make sure that chain INPUT calls the rule we're generating
#

# print a preamble to the script that normalizes the INPUT chain.
print """
CHAIN=%s
# make sure default_drop - default INPUT policy - exists
if $(iptables --list default_drop 2>/dev/null 1>&2)  ;
then
	# chain exists, do nothing
	true
else
	# create it
	iptables -N default_drop 
	# should be more here ...
fi
# remove CHAIN from INPUT, and flush it (if it exists), and re-create it
(iptables -D INPUT -j ${CHAIN}
 iptables -X ${CHAIN}
 iptables -N ${CHAIN}) 2>/dev/null 1>&2
# remove "drop default" as last rule, append this chain, re-append default_drop to end
if $(iptables --check INPUT -j ${CHAIN} 2>/dev/null 1>&2) ; 
then 
	# already call chain from INPUT, so just empty this chain
	iptables -F ${CHAIN}
else 
	# add this ruleto the chain
	iptables -A INPUT -j ${CHAIN}
fi
if $(iptables --check INPUT -j default_drop 2>/dev/null 1>&2) ;
then
	# remove default action from INPUT chain
	iptables -D INPUT -j default_drop  # default "drop" action
else
	# not there, that's ok
	true
fi	
""" % (sdp_group)

for line in sdp_lines:
    print "iptables -A %s --source %s --protocol %s --sport %d --destination %s --jump ACCEPT"\
        % (sdp_group, line['sdp_source_ip'], line['sdp_protocol'], line['sdp_port'],  \
         line['sdp_destination_ip'])

# print iptables "end rules" - default drop
print "iptables -A INPUT -j default_drop"

