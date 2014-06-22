
Bender

A better way to manage firewall rules - by managing policy instead

Say
   "TheseHosts" want to communicate to "ThoseHosts" for "ThisService"

Groups Of Hosts leverage a Service Template to gain access to Groups Of
Hosts.
A Policy groups define the current and allowable sets of rules

A simple policy might include
  Host Groups
       Group		Member	Type	Owner	Risk Person
       workstation	huey	user		walt		walt
       workstation	louie	user		walt		walt
       server		pluto	genpop	scrooge	walt
       server		goofy	genpop	scrooge	walt

  Service Template
	Name	Port	Protocol	Transport	Owner	Risk Person
	domain	53	tcp		dns		daffy	walt
	domain	53	udp		dns		daffy	walt
	time		123	udp		ntp		scrooge	walt

  Policy Groups
  	Name		Source		Destination	Template
	basic_service	workstation	server		domain
	basic_service	workstation	server		time

The above say that "workstations can access basic_service on server".  From 
this, by looking up domain names and services, the basic data for various
firewalls is available (see "Policy Rendering"), and correct syntax can be 
easily generated.

Day to Day Policy Management:
    Manage and maintain the host groups
    Manage and maintain the service template
    Manage and maintain policy statements

    This is the basis of it all.  These group/group/template approaches allow
    management of policy at a higher level - enabling tracking of all
    relationships back to the original policy statement.

    The policy statement (the "allow TheseHosts to access ThoseHosts for
    ThatService") is managed in the policy database.

    By "resolving" the policy (using the host and service templates), a set of
    end-to-end permissions can be determined - this looks a lot more like the
    traditional <source,destination,protocol> tuples that people who manage
    firewalls are used to seeing.  However, these only describe the end-to-end
    state, and don't describe all devices in the path.

    The rendered policy (or "SDP" - source/destination/protocol) rules can
    then be mapped to the network topology to determine the actual
    configuration statements that are necessary to enable the original policy
    statement.

But I also need to ...

    There is a lot of meta-data that needs tracking to understand the
    provenance (the history and control) of policy, rules and services and
    host groups.  This tends to vary widely across different organizations,
    and may include date/age of the policy or rule, who made the change, who
    the various owners are (service, server, risk), and so forth.

    The approach to resolve this is to make the system data-driven, rather
    than control driven.  WHATEVER fields you define in the databases will be
    tracked and managed.  Need to add a new field? Stop the system, and update
    the database with a new column that you need.  It will then be available
    in all matching/searching operations.

    Some recommended fields:

    	start/stop dates - this allows tracking of history of rules by never
    	 	    actually deleting data from the system.  If a rule needs
    	 	    to be "deleted", simply set the end date to the current
    	 	    date.  If a rule needs to be updated, then set the end
    	 	    date on the old record, and start a new record.  In this
    	 	    approach, policy statements can be set to "reconfirm" at
    	 	    some date, and the entire history of the policy is
    	 	    available by looking at records without regards to the
    	 	    dates.

	owners and risk party - track the owner of the server or service
    	       	   seperately from the party that signs off on the risk.  This
    	       	   is the bases for the control gates in workflows to allow
    	       	   sign-offs and cross-checking and audit functionality.

     Some required fields:

     	  To work generically, a minimum set of fields are required (though
     	  matching/searching operations can occur across all available
     	  fields).

	  Note that the required fields are _not_ enough to generate valid
	  configuration in a running network - just enough to tell different
	  things apart.  For example; the SDP database doesn't require
	  protocol (tcp or udp), but those would be necessary to generate
	  valid ACLs.

	  Requred fields for databases (the column names are capitalized)-
	  * Host Groups: NAME of the group, and MEMBER of the group
	  * Service Templates: NAME of the service, and PORT that it uses, PROTOCOL
          * Policy Database: NAME, SOURCE, DESTINATION, TEMPLATE 
	  * SDP Database: GROUP, NAME, SOURCE, DESTINATION,
				PORT, PROTOCOL, SOURCE_IP, DESTINATION_IP
	
What does it work on?

     Since only the data is stored and manipulated, the last steps of
     generating valid configuration involve (a) determining the topology and
     devices, (b) translating the SDP sets into configuration language.

     From a <source, destination, port, protocol> tuple, it is pretty trivial
     to generate valid configuration for IOS ACLs, IP Tables, or what have
     you.  An example "ios-genpol.py" is included as an example of reading the
     SDP tuples, and wrapping platform syntax around it.

Getting Started

 Bender is written as a python class library - but includes some example code
 at the bottom.  There is also a "bender_ui.py" written using Flask that can
 help to understand the interworkings a bit better.
	 

;; Local Variables:
;; mode: text
;; fill-column: 78
;; End:
