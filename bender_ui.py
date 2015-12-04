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
hg = bender.host_group('mockdata/mock-hostdb.csv')
sg = bender.service_template('mockdata/mock-svcdb.csv')
pg = bender.policy_group('mockdata/mock-poldb.csv')
sdp = bender.policy_render('mockdata/mock-sdpdb.csv')

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
        print "Web: *** delete_group - no group specified:", g
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
        print "Web: *** delete_member - no member specified:", m, "group:",g
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
        return redirect(url_for('index_hostgroups'))
    print "Web: add member", m, "to group", g
    hg.add(hg_name=g, hg_member=m, hg_type=t, hg_owner=o, hg_rp=r)
    return redirect(url_for('index_hostgroups')+"#groups")

@b_ui.route('/savegroup', methods=['POST'])
def save_group():
    hg.save("mockdata/mock-hostdb.csv")
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
    #    sl = sg.select(st_name=sname)
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
    sg.add(st_name=name, st_port=port, st_protocol=protocol, st_bidir=bidir,
           st_transport=transport, st_owner=owner, st_rp=rp)
    return redirect(url_for('index_hostgroups')+"#services")

@b_ui.route('/saveservice', methods=['POST'])
def save_service():
    sg.save("mockdata/mock-svcdb.csv")
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
    dpol = pg.select(p_name=name, p_source=source,
                     p_destination=destination, p_template=template)
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
    pg.save("mockdata/mock-poldb.csv")
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
        for src in hg.select(hg_name=p['p_source']):
            for dst in hg.select(hg_name=p['p_destination']):
                for svc in sg.select(st_name=p['p_template']):
                    name = "%s_%s_%s" % (src['hg_name'], dst['hg_name'], svc['st_name'])
                    try:
                        source_ip = gethostaddr(src['hg_member'])
                        destination_ip = gethostaddr(dst['hg_member'])
                    except:
                        print "Error looking up", src['hg_member'], "or", dst['hg_member']
                        continue  # just skip it?
                    if src['hg_member'] != dst['hg_member']:
                        # print "\tSDP Add:", src['hg_member'], "and", dst['hg_member'], "for", svc['st__name']
                        sdp.add(sdp_group=p['p_name'], sdp_name=name,
                                sdp_source=src['hg_member'], sdp_source_ip=source_ip,
                                sdp_destination=dst['hg_member'],
                                sdp_destination_ip=destination_ip,
                                sdp_bidir=svc['st_bidir'], sdp_port=svc['st_port'],
                                sdp_protocol=svc['st_protocol'])
    sdp.save('mockdata/mock-sdpdb.csv')
    return redirect(url_for('index_hostgroups')+"#renderedpolicies")

@b_ui.route('/resetsdp', methods=['POST'])
def reset_sdp():
    # just erase the whole thing - usually done prior to a full recompute
    sdp.zero()
    sdp.save('mockdata/mock-sdpdb.csv')
    return redirect(url_for('index_hostgroups')+"#renderedpolicies")

if __name__ == '__main__':
    b_ui.run(debug=True, use_reloader=False, host='0.0.0.0', port=5010)
