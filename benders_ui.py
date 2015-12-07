#!/usr/bin/python
"""Interface to a simple policy database representing network policy
This allows owners to update the own "host groups" and "service templates"
which allow policy statements.

While this version uses a CSV files, it should be easily
extensible to use more conventional databases.
"""

import bender_sql as bender
import socket, sys

from flask import Flask, request, url_for, render_template, redirect

# gethostaddr - similar to socket.gethostbyname() - but use getaddrinfo() to deal
# with IPv6 addresses
def gethostaddr(name):
    # a _very_ bad way to if name is an IP address or IP network (v4 or v6)
    s = name
    if s.strip('0123456789/.:abcdefABCDEF') == '':
        return name  # _probably_ an IPv4 or IPv6 address or network
    # raises gaierror for invalid names
    h_infos = socket.getaddrinfo(name,None,0,0,socket.SOL_TCP)
    # go for the first item returned in the array
    # print "Name",name,"address",h_infos[0][4][0]
    return h_infos[0][4][0]

# set up initial Flask and SQLAlchemy stuff
b_ui = Flask(__name__, static_url_path='/static')

db_cfg = bender.read_config("database",['/etc/bender.cf','bender.cf'])

if len(sys.argv) < 2 and db_cfg['uri'] == '':
    print "benders_ui <sqlalchemy URI>"
    print "\tmysql:///user:pass@hostname:3306/bender"
    sys.exit(1)

if db_cfg['uri'] == '':
    db_uri = sys.argv[1]
else:
    db_uri = db_cfg['uri']

# Load the databases
hg = bender.host_group(db_uri,'hostgroups')
sg = bender.service_template(db_uri,'service_templates')
pg = bender.policy_group(db_uri,'policy')
sdp = bender.policy_render(db_uri,'sdp')

# 
# Set up Flask main page, which has links to everything else
#
@b_ui.route('/index')
@b_ui.route('/')
def index_hostgroups():
    r_info = []
    q_info = []
    p_info = []
    sdp_info = []

    # check for messages from other parts redirecting here
    hostgroup_err = request.args.get('hg_msg')
    service_err = request.args.get('svc_msg')
    policy_err = request.args.get('pol_msg')
    sdp_err = request.args.get('sdp_msg')

    # sort when displaying, so members of the same group appear next to each other
    for h in sorted(hg.select(), key=lambda k: k['hg_name']):
        r_info.append(h.copy())
    for s in sorted(sg.select(), key=lambda k: k['st_name']):
        q_info.append(s.copy())
    for p in sorted(pg.select(), key=lambda k: k['p_name']):
        p_info.append(p.copy())
    for sd in sorted(sdp.select(), key=lambda k: k['sdp_group']):
        sdp_info.append(sd.copy())
    print "Render:",service_err
    return render_template('benders_index.html',
                           groupinfo=r_info, hg_error=hostgroup_err,
                           svcinfo=q_info, svc_error=service_err,
                           polinfo=p_info, pol_error=policy_err,
                           sdpinfo=sdp_info, sdp_error=sdp_err)


#####################################################
# Group management
#####################################################
@b_ui.route('/delgroup', methods=['POST'])
def delete_group():
    g = request.form['group']
    if not g:
        print "Web: *** delete_group - no group specified:", s
        return redirect(url_for('index_hostgroups'))
    print "Web: delete group ", g
    dg = hg.select(hg_name=g)
    for d in dg:
        hg.delete(d)
    return redirect(url_for('index_hostgroups'))

@b_ui.route('/delmember', methods=['POST'])
def delete_member():
    m = request.form['member']
    g = request.form['group']
    if not m or not g:
        print "Web: *** delete_member - no member specified:", m
        return redirect(url_for('index_hostgroups'))
    dm = hg.select(hg_name=g, hg_member=m)
    print "Web: delete member ", m, "returned", dm
    for m in dm:
        hg.delete(m)
    return redirect(url_for('index_hostgroups'))

@b_ui.route('/addgroup', methods=['POST'])
def add_group():
    m = request.form['groupmember']
    g = request.form['groupname']
    t = request.form['grouptype']
    o = request.form['groupowner']
    r = request.form['grouprp']
    if not m or not g:
        print "Web: *** add_group - no member or group specified:", g
        return redirect(url_for('index_hostgroups', hg_msg="no member specified"))
    print "Web: add member", m, "to group", g
    hg.add(hg_name=g, hg_member=m, hg_type=t, hg_owner=o, hg_rp=r)
    return redirect(url_for('index_hostgroups')+"#groups")

@b_ui.route('/savegroup', methods=['POST'])
def save_group():
    hg.save("testdata/mock-hostdb.csv")
    return redirect(url_for('index_hostgroups')+"#groups")

#####################################################
# service management
#####################################################
@b_ui.route('/deletesvc', methods=['POST'])
def delete_service():
    sname = request.form['name']
    print "Web: *** delete_service", sname
    sl = sg.select(st_name=sname)
    for s in sl:
        sg.delete(s)
    return redirect(url_for('index_hostgroups')+"#services")

@b_ui.route('/deletesvcline', methods=['POST'])
def delete_service_line():
    lname = request.form['name']
    print "Web: *** delete_service line", lname
    #    sl = sg.select(name=sname)
    sl = sg.select(st_name=request.form['name'],
                   st_port=request.form['port'],
                   st_protocol=request.form['protocol'],
                   st_transport=request.form['transport'],
                   st_bidir=request.form['bidir'],
                   st_owner=request.form['owner'],
                   st_rp=request.form['rp'])
    for s in sl:
        sg.delete(s)
    return redirect(url_for('index_hostgroups')+"#services")

@b_ui.route('/addservice', methods=['POST'])
def add_service():
    name = request.form['name']
    port = request.form['port']
    protocol = request.form['protocol']
    transport = request.form['transport']
    bidir = request.form['bidir']
    owner = request.form['owner']
    rp = request.form['rp']
    if not port.isdigit():
        # pop up message here
        return redirect(url_for('index_hostgroups',svc_msg='port must be a number')+"#services")
    else:
        sg.add(st_name=name,
               st_port=port,
               st_protocol=protocol,
               st_bidir=bidir,
               st_transport=transport,
               st_owner=owner,
               st_rp=rp)
    return redirect(url_for('index_hostgroups')+"#services")

@b_ui.route('/saveservice', methods=['POST'])
def save_service():
    sg.save("testdata/mock-svcdb.csv")
    return redirect(url_for('index_hostgroups')+"#services")

#####################################################
# Policy management
#####################################################
@b_ui.route('/delpolicyline', methods=['POST'])
def delete_policy_line():
    name = request.form['name']
    source = request.form['source']
    destination = request.form['destination']
    template = request.form['template']
    dpol = pg.select(p_name=name,
                     p_source=source,
                     p_destination=destination,
                     p_template=template)
    for d in dpol:
        pg.delete(d)
    return redirect(url_for('index_hostgroups')+"#policies")

@b_ui.route('/delpolicy', methods=['POST'])
def delete_policy():
    name = request.form['name']
    dpol = pg.select(p_name=name)
    for d in dpol:
        pg.delete(d)
    return redirect(url_for('index_hostgroups')+"#policies")

@b_ui.route('/addpolicy', methods=['POST'])
def add_policy():
    name = request.form['name']
    source = request.form['source']
    destination = request.form['destination']
    template = request.form['template']
    pg.add(p_name=name,
           p_source=source,
           p_destination=destination,
           p_template=template)
    return redirect(url_for('index_hostgroups')+"#policies")

@b_ui.route('/savepolicy', methods=['POST'])
def save_policy():
    pg.save("testdata/mock-poldb.csv")
    return redirect(url_for('index_hostgroups')+"#policies")

#####################################################
# Rendering functions
#####################################################
@b_ui.route('/rendersdp', methods=['POST'])
def render_sdp():
    # Generate all policies
    #   for all policies
    #           for all hosts in the policy source host group
    #             for all hosts in the policy destination host group
    #                 for all services in the service template
    #                   save the source,destination,port information
    errors = ''
    errors_nl = ''
    # first, clear all policies
    sdp.delete({})
    # regenerate what we need
    for p in pg:
        for src in hg.select(hg_name=p['p_source']):
            for dst in hg.select(hg_name=p['p_destination']):
                for svc in sg.select(st_name=p['p_template']):
                    name = "%s_%s_%s" % (src['hg_name'], dst['hg_name'], svc['st_name'])
                    try:
                        source_ip = gethostaddr(src['hg_member'])
                        destination_ip = gethostaddr(dst['hg_member'])
                    except:
                        e_msg = "Error looking up %s or %s" % (src['hg_member'],dst['hg_member'])
                        print e_msg
                        errors = errors + errors_nl + e_msg
                        errors_nl = '\r\n'
                        continue  # just skip it?
                    if src['hg_member'] != dst['hg_member']:
                        # print "\tSDP Add:", src['member'], "and", dst['member'], "for", svc['name']
                        sdp.add(sdp_group=p['p_name'],
                                sdp_name=name,
                                sdp_source=src['hg_member'],
                                sdp_source_ip=source_ip,
                                sdp_destination=dst['hg_member'],
                                sdp_destination_ip=destination_ip,
                                sdp_bidir=svc['st_bidir'],
                                sdp_port=svc['st_port'],
                                sdp_protocol=svc['st_protocol'])
    sdp.save('testdata/mock-sdpdb.csv')
    return redirect(url_for('index_hostgroups', sdp_msg=errors)+"#renderedpolicies")

@b_ui.route('/resetsdp', methods=['POST'])
def reset_sdp():
    # just erase the whole thing - usually done prior to a full recompute
    sdp.zero()
    sdp.save('testdata/mock-sdpdb.csv')
    return redirect(url_for('index_hostgroups')+"#renderedpolicies")

if __name__ == '__main__':
    b_ui.run(debug=True, use_reloader=False, host='0.0.0.0', port=5010)
