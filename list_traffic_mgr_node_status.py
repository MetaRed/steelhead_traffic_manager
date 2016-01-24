#!/usr/local/bin/python

import simplejson as json
import sys
import requests
import argparse
import logging

parser = argparse.ArgumentParser(argument_default="", description='Steelhead Traffic Manager API')
parser.add_argument('--pool', metavar='<POOL NAME>', help='Display all nodes in this Pool')
parser.add_argument('--port', metavar='<PORT NUMBER>', help='Port Number to connect Default is 9070', default='9070')
parser.add_argument('--hostname', metavar='<https://HOSTNAME URL>', help='Name or IP address of Traffic Manager', required=True)
parser.add_argument('--user', metavar='<USER NAME>', help='User for Authentication', required=True)
parser.add_argument('--password', metavar='<USER NAME PASSWORD>', help='User Password for Authentication', required=True)

user_args = vars(parser.parse_args())
poolName = str(user_args['pool'])
host_name = str(user_args['hostname'])
port_num = str(user_args['port'])
user_name = str(user_args['user'])
user_pass_word = str(user_args['password'])

url = host_name + ':' + port_num + '/api/tm/3.0/config/active/pools'
jsontype = {'content-type': 'application/json'}
client = requests.Session()
client.auth = (user_name, user_pass_word)
# To allow interaction with self sighned SSL certificates
client.verify = False
# Redirect messages to your log file
logging.basicConfig(filename='python.log', filemode='w')
logging.captureWarnings(True)
# Dictionary group declarations
active_nodes = {}
draining_nodes = {}
disabled_nodes = {}

###
### Function
###
def lb_connector():

    response = client.get(url + "/" + poolName)

    poolConfig = json.loads(response.content)

    if response.status_code == 200:
        print "\n" + poolName + " pool:"
                # Since we are getting the properties for a pool we expect the first element to be 'properties'

        if poolConfig.has_key('properties'):

                    # The value of the key 'properties' will be a dictionary containing property sections
                    # All the properties that this program cares about are in the 'nodes_table' below the 'basic'section
                    # The nodes_table section contains the
                    # the list of all nodes in this pool and the node's state

            node = poolConfig['properties']['basic']['nodes_table']

                # Each node is grouped into a dictionary by the node's state

            for s in node:
                        # Add node name and state to corresponding dictionaries
                        # 'active_node' 'drain_nodes' 'disabled_nodes'

             if s['state'] == "active":
                                # Add node name and state to 'active_nodes' dictionary

                active_nodes.update({'node': s['node'],'state': s['state']})
                print active_nodes["node"] + " " + active_nodes["state"]
             elif s['state'] == "draining":
                            # Add node name and state to 'draining_nodes' dictionary

                draining_nodes.update({'node': s['node'],'state': s['state']})
                print draining_nodes["node"] + " " + draining_nodes["state"]

             elif s['state'] == "disabled":
                            # Add node name and state to disabled dictionary

                disabled_nodes.update({'node': s['node'],'state': s['state']})
                print disabled_nodes["node"] + " " + disabled_nodes["state"]

             else:
                print s['node'] + " has unknown status :" + s['state']
                continue

        else:
                print "Error: No properties found for pool " + poolName

    else:
                print "Error getting pool config: URL=%s Status=%d Id=%s: %s" %(url + "/" + poolName, response.status_code, poolConfig['error_id'], poolConfig['error_text'])

#
# End Function
#

if poolName:
    # Get the properties of a single pool name
    lb_connector()
else:
    # Otherwise get the properties of all the pools
    try:

    # Do the HTTP GET to get the lists of pools.  We are only putting this client.get within a try
    # because if there is no error connecting on this one there shouldn't be an error connnecting
    # on later client.get so that would be an unexpected exception.

        response = client.get(url)

    except requests.exceptions.ConnectionError:

        print "Error: Unable to connect to " + url
        sys.exit(1)

    data = json.loads(response.content)


    if response.status_code == 200:

        if data.has_key('children'):
            pools = data['children']

            for i, pool in enumerate(pools):
                poolName = pool['name']

                # Do the HTTP GET to get the properties of a pool
                lb_connector()
        else:
            print 'Error: No chidren found'

    else:
        print "Error getting pool list: URL=%s Status=%d Id=%s: %s" %(url, response.status_code, data['error_id'], data['error_text'])
