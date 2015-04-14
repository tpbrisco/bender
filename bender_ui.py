#!/usr/bin/python
"""Interface to a simple policy database representing network policy
This allows owners to update the own "host groups" and "service templates"
which allow policy statements.

While this version uses a CSV files, it should be easily
extensible to use more conventional databases.
"""

import bender
import socket

from flask import Flask, request, url_for, render_template, redirect

b_ui = Flask(__name__, static_url_path='/static')

# Load the demo databases from mock data
hg = bender.host_group('testdata/mock-hostdb.csv')
sg = bender.service_template('testdata/mock-svcdb.csv')
pg = bender.policy_group('testdata/mock-poldb.csv')
sdp = bender.policy_render('testdata/mock-sdpdb.csv')

# gethostaddr - similar to socket.gethostbyname() - but use getaddrinfo() to deal
# with IPv6 addresses
def gethostaddr(name):
    h_infos = socket.getaddrinfo(name,None,0,0,socket.SOL_TCP)
    if len(h_infos) < 0:
        raise
    # go for the first item returned in the array
    print "Name",name,"address",h_infos[0][4][0]
    return h_infos[0][4][0]

@b_ui.route('/index')
@b_ui.route('/')
def index_hostgroups():
    r_info = []
    q_info = []
    p_info = []
    sdp_info = []

    # sort when displaying, so members of the same group appear next to each other
    for h in sorted(hg, key=lambda k: k['hg_name']):
        r_info.append(h.copy())
    for s in sorted(sg, key=lambda k: k['st_name']):
        q_info.append(s.copy())
    for p in sorted(pg, key=lambda k: k['p_name']):
        p_info.append(p.copy())
    for sd in sorted(sdp, key=lambda k: k['sdp_group']):
        sdp_info.append(sd.copy())
    return render_template('bender_index.html',
                           groupinfo=r_info, svcinfo=q_info,
                           polinfo=p_info, sdpinfo=sdp_info)


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
    dg = hg.select(name=g)
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
    dm = hg.select(name=g, member=m)
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
        return redirect(url_for('index_hostgroups'))
    print "Web: add member", m, "to group", g
    hg.add(name=g, member=m, type=t, owner=o, rp=r)
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
    sl = sg.select(name=sname)
    for s in sl:
        sg.delete(s)
    return redirect(url_for('index_hostgroups')+"#services")

@b_ui.route('/deletesvcline', methods=['POST'])
def delete_service_line():
    lname = request.form['name']
    print "Web: *** delete_service line", lname
    #    sl = sg.select(name=sname)
    sl = sg.select(name=request.form['name'],
                   port=request.form['port'],
                   protocol=request.form['protocol'],
                   transport=request.form['transport'],
                   bidir=request.form['bidir'],
                   owner=request.form['owner'],
                   rp=request.form['rp'])
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
    sg.add(name=name, port=port, protocol=protocol, bidir=bidir,
           transport=transport, owner=owner, rp=rp)
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
    dpol = pg.select(name=name, source=source,
                     destination=destination, template=template)
    for d in dpol:
        pg.delete(d)
    return redirect(url_for('index_hostgroups')+"#policies")

@b_ui.route('/delpolicy', methods=['POST'])
def delete_policy():
    name = request.form['name']
    dpol = pg.select(name=name)
    for d in dpol:
        pg.delete(d)
    return redirect(url_for('index_hostgroups')+"#policies")

@b_ui.route('/addpolicy', methods=['POST'])
def add_policy():
    name = request.form['name']
    source = request.form['source']
    destination = request.form['destination']
    template = request.form['template']
    pg.add(name=name, source=source, destination=destination, template=template)
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
    for p in pg:
        for src in hg.select(name=p['source']):
            for dst in hg.select(name=p['destination']):
                for svc in sg.select(name=p['template']):
                    name = "%s_%s_%s" % (src['name'], dst['name'], svc['name'])
                    try:
                        source_ip = gethostaddr(src['member'])
                        destination_ip = gethostaddr(dst['member'])
                    except:
                        print "Error looking up", src['member'], "or", dst['member']
                        continue  # just skip it?
                    if src['member'] != dst['member']:
                        # print "\tSDP Add:", src['member'], "and", dst['member'], "for", svc['name']
                        sdp.add(group=p['name'], name=name,
                                source=src['member'], source_ip=source_ip,
                                destination=dst['member'], destination_ip=destination_ip,
                                bidir=svc['bidir'],
                                port=svc['port'], protocol=svc['protocol'])
    sdp.save('testdata/mock-sdpdb.csv')
    return redirect(url_for('index_hostgroups')+"#renderedpolicies")

@b_ui.route('/resetsdp', methods=['POST'])
def reset_sdp():
    # just erase the whole thing - usually done prior to a full recompute
    sdp.zero()
    sdp.save('testdata/mock-sdpdb.csv')
    return redirect(url_for('index_hostgroups')+"#renderedpolicies")

if __name__ == '__main__':
    b_ui.run(debug=True, use_reloader=False, host='0.0.0.0', port=5010)
