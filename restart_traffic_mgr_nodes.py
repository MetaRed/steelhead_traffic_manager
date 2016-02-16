#!/usr/local/bin/python
# Richard Lopez
#
# Steel App Traffic Manager Nodes Pool
# Drain/Enable Logic
#################################################
import json
from collections import defaultdict
import sys
import re
import requests
import argparse
import logging

parser = argparse.ArgumentParser(argument_default='', description='Steelhead Traffic Manager API')
parser.add_argument('--pool', metavar='<POOL NAME>', help='Display all nodes in this Pool')
parser.add_argument('--port', metavar='<PORT NUMBER>', help='Port Number to connect Default is 9070', default='9070')
parser.add_argument('--hostname', metavar='<https://HOSTNAME URL>', help='Name or IP address of Traffic Manager', required=True)
parser.add_argument('--user', metavar='<USER NAME>', help='User for Authentication', required=True)
parser.add_argument('--password', metavar='<USER NAME PASSWORD>', help='User Password for Authentication', required=True)

user_args = vars(parser.parse_args())
user_pool_name = str(user_args['pool'])
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
logging.basicConfig(filename='palo.log', filemode='w')
logging.captureWarnings(True)

pool_list = []
user_nodes = defaultdict(list)
veritas_nodes = defaultdict(list)
action_nodes = defaultdict(list)

# Sliding Window Function for Pools containing 3 or more nodes
def rolling_restart(node_list,user_node_list_size,step=1):
    # Pre-compute number of hosts to process
    hosts_num = (len(node_list)/step)
    for i in range(0,hosts_num*step,step):
        yield node_list[i:i+user_node_list_size]

# Collect all nodes in an active state from all existing Pools
def lb_connector():

    response = client.get(url + '/' + user_pool_name)

    user_pool_config = json.loads(response.content)

    # Since we are getting the properties for a pool we expect the first element to be 'properties'

    if user_pool_config.has_key('properties'):
    # The value of the key 'properties' will be a dictionary containing property sections
    # All the properties that this program cares about are in the 'nodes_table' below the 'basic'section
    # The nodes_table section contains the list of all nodes in this pool and the node's state

            node = user_pool_config['properties']['basic']['nodes_table']
            # Each node is grouped into a dictionary by the node's state

            for s in node:
            # Add all 'active' nodes by name and corresponding pool

             if s['state'] == 'active':
             # Add node name and state to 'active_nodes' dictionary

                user_nodes[user_pool_name].append(s['node'])

             else:
                print s['node'] + ' has unknown status :' + s['state']
                continue

    else:
        print 'Error: No properties found for pool ' + user_pool_name

# Drain and Enable user nodes
# Drain and Enable any nodes that are members of other pools
# with the same base host name as the user nodes
# Assumes the same hostname convention is used for all nodes
# and node distinction is determined by the port that node's
# service is listening on

def lb_lazarus():
    # Populate Restart List
    user_node_list = []
    for user_value in user_nodes.values():
        for user_node in user_value:
            user_node_list.append(user_node)

    if action_nodes:
        print 'User nodes that are active members of other pools:'
        for k, v in action_nodes.items():
            print k + ' Pool:'
            qnode = str(v).strip('[]\"\'')
            print qnode

        user_input = None

        while not user_input:
            print 'Do you wish to continue?'
            user_input = str(raw_input("Enter (Y)es or (N)o: ")).lower().strip()
            user_input.lower()

            if user_input == 'yes' or user_input == 'y':
                print 'DRAINING DUPLICATE NODES FROM ALL AUXILIARY POOLS'

                # Drain all duplicate nodes first
                for action_key, action_value in action_nodes.items():
                    for action_node_list in action_value:

                        print 'Compare Node Pool: ' + action_key
                        data_node = str(action_node_list).strip('[]\"\'')

                        data = {"properties": {"basic": {"nodes_table": [{"state": "draining", "node": data_node}]}}}
                        #client.put(url, data=json.dumps(data), headers={'content-type': 'application/json'})
                        print 'DRAINING NODE DATA IN LIST'
                        print data


                first_rolling_node = user_node_list[0]
                last_rolling_node = user_node_list[-1]
                print first_rolling_node
                print last_rolling_node

                # Sliding Window List to Restart Nodes if 3 or more in Pool
                rolling_user_nodes = rolling_restart(user_node_list,2,1)
                for rolling_node in rolling_user_nodes:

                    if len(user_node_list) == 2:
                        print 'READY TO DRAIN: ' + rolling_node[0] + '?'

                        user_say = None
                        while not user_say:
                            user_say = str(raw_input("Enter (Y)es or (N)o: ")).lower().strip()
                            user_say.lower()
                            if user_say == 'yes' or user_say == 'y':

                                print 'DRAIN LOGIC HERE'

                                data_node = str(rolling_node[0]).strip('[]\"\'')
                                data = {"properties": {"basic": {"nodes_table": [{"state": "draining", "node": data_node}]}}}
                                #client.put(url, data=json.dumps(data), headers={'content-type': 'application/json'})
                                print data
                                print rolling_node[0]

                            elif user_say == 'no' or user_say == 'n':
                                return False

                            else:
                                print 'Invalid User Input: Exiting Program.'

                        print 'READY TO ENABLE: ' + rolling_node[0] + ' AND DRAIN ' + rolling_node[1] + '?'

                        user_say = None
                        while not user_say:
                            user_say = str(raw_input("Enter (Y)es or (N)o: ")).lower().strip()
                            user_say.lower()
                            if user_say == 'yes' or user_say == 'y':

                                print 'ENABLE LOGIC HERE'
                                data_node = str(rolling_node[0]).strip('[]\"\'')
                                data = {"properties": {"basic": {"nodes_table": [{"state": "active", "node": data_node}]}}}
                                #client.put(url, data=json.dumps(data), headers={'content-type': 'application/json'})
                                print data
                                print rolling_node[0]

                                print 'DRAIN LOGIC HERE'
                                data_node = str(rolling_node[1]).strip('[]\"\'')
                                data = {"properties": {"basic": {"nodes_table": [{"state": "drain", "node": data_node}]}}}
                                #client.put(url, data=json.dumps(data), headers={'content-type': 'application/json'})
                                print data

                            elif user_say == 'no' or user_say == 'n':
                                return False

                            else:
                                print 'Invalid User Input: Exiting Program.'

                        print 'READY TO ENABLE: ' + rolling_node[1] + '?'

                        user_say = None
                        while not user_say:
                            user_say = str(raw_input("Enter (Y)es or (N)o: ")).lower().strip()
                            user_say.lower()
                            if user_say == 'yes' or user_say == 'y':

                                print 'ENABLE LOGIC HERE'

                                data_node = str(rolling_node[1]).strip('[]\"\'')
                                data = {"properties": {"basic": {"nodes_table": [{"state": "active", "node": data_node}]}}}
                                #client.put(url, data=json.dumps(data), headers={'content-type': 'application/json'})
                                print data
                                print rolling_node[1]
                                exit()

                            elif user_say == 'no' or user_say == 'n':
                                return False

                            else:
                                print 'Invalid User Input: Exiting Program.'

                    elif rolling_node[0] == first_rolling_node:
                        print 'READY TO DRAIN: ' + rolling_node[0] + '?'

                        user_say = None
                        while not user_say:
                            user_say = str(raw_input("Enter (Y)es or (N)o: ")).lower().strip()
                            user_say.lower()
                            if user_say == 'yes' or user_say == 'y':

                                print 'DRAIN LOGIC HERE'

                                data_node = str(rolling_node[0]).strip('[]\"\'')
                                data = {"properties": {"basic": {"nodes_table": [{"state": "draining", "node": data_node}]}}}
                                #client.put(url, data=json.dumps(data), headers={'content-type': 'application/json'})
                                print data
                                print rolling_node[0]

                            elif user_say == 'no' or user_say == 'n':
                                return False

                            else:
                                print 'Invalid User Input: Exiting Program.'

                    elif rolling_node[0] == last_rolling_node:
                        print 'READY TO ENABLE: ' + rolling_node[0] + '?'

                        user_say = None
                        while not user_say:
                            user_say = str(raw_input("Enter (Y)es or (N)o: ")).lower().strip()
                            user_say.lower()
                            if user_say == 'yes' or user_say == 'y':

                                print 'ENABLE LOGIC HERE'

                                data_node = str(rolling_node[0]).strip('[]\"\'')
                                data = {"properties": {"basic": {"nodes_table": [{"state": "active", "node": data_node}]}}}
                                #client.put(url, data=json.dumps(data), headers={'content-type': 'application/json'})
                                print data

                                # Re-enable all duplicate nodes
                                for action_key, action_value in action_nodes.items():
                                    for action_node_list in action_value:

                                        print 'Compare Node Pool: ' + action_key
                                        data_node = str(action_node_list).strip('[]\"\'')
                                        data = {"properties": {"basic": {"nodes_table": [{"state": "active", "node": data_node}]}}}
                                        #client.put(url, data=json.dumps(data), headers={'content-type': 'application/json'})
                                        print 'ENABLING DUPLICATE NODES IN LIST'
                                        print data


                            elif user_say == 'no' or user_say == 'n':
                                return False

                            else:
                                print 'Invalid User Input: Exiting Program.'

                    else:
                        print 'READY TO DRAIN: ' + str(rolling_node[1]) + ' AND ENABLE: ' + str(rolling_node[0]) + ' ?'
                        user_say = None

                        while not user_say:
                            user_say = str(raw_input("Enter (Y)es or (N)o: ")).lower().strip()
                            user_say.lower()
                            if user_say == 'yes' or user_say == 'y':

                                print ('ENABLING ' + track + ':')
                                print 'ENABLE LOGIC HERE'

                                data = {"properties": {"basic": {"nodes_table": [{"state": "active", "node": rolling_node[0]}]}}}
                                #client.put(url, data=json.dumps(data), headers={'content-type': 'application/json'})
                                print data

                                print 'DRAIN LOGIC HERE'
                                data = {"properties": {"basic": {"nodes_table": [{"state": "draining", "node": rolling_node[1]}]}}}
                                #client.put(url, data=json.dumps(data), headers={'content-type': 'application/json'})
                                print data

                            elif user_say == 'no' or user_say == 'n':
                                return False

                            else:
                                print 'Invalid User Input: Exiting Program.'



            elif user_input == 'no' or user_input == 'n':
                return False

            else:
                print 'Invalid User Input: Exiting Program.'

    else:
        first_rolling_node = user_node_list[0]
        last_rolling_node = user_node_list[-1]
        print first_rolling_node
        print last_rolling_node

        # Sliding Window List to Restart Nodes if 3 or more in Pool
        rolling_user_nodes = rolling_restart(user_node_list,2,1)
        for rolling_node in rolling_user_nodes:

            if len(user_node_list) == 2:
                print 'READY TO DRAIN: ' + rolling_node[0] + '?'

                user_say = None
                while not user_say:
                    user_say = str(raw_input("Enter (Y)es or (N)o: ")).lower().strip()
                    user_say.lower()

                    if user_say == 'yes' or user_say == 'y':
                        print 'DRAIN LOGIC HERE'
                        data_node = str(rolling_node[0]).strip('[]\"\'')
                        data = {"properties": {"basic": {"nodes_table": [{"state": "draining", "node": data_node}]}}}
                        #client.put(url, data=json.dumps(data), headers={'content-type': 'application/json'})
                        print data
                        print rolling_node[0]

                    elif user_say == 'no' or user_say == 'n':
                        return False

                    else:
                        print 'Invalid User Input: Exiting Program.'

                print 'READY TO ENABLE: ' + rolling_node[0] + ' AND DRAIN ' + rolling_node[1] + '?'

                user_say = None
                while not user_say:
                    user_say = str(raw_input("Enter (Y)es or (N)o: ")).lower().strip()
                    user_say.lower()

                    if user_say == 'yes' or user_say == 'y':

                        print 'ENABLE LOGIC HERE'
                        data_node = str(rolling_node[0]).strip('[]\"\'')
                        data = {"properties": {"basic": {"nodes_table": [{"state": "active", "node": data_node}]}}}
                        #client.put(url, data=json.dumps(data), headers={'content-type': 'application/json'})
                        print data
                        print rolling_node[0]

                        print 'DRAIN LOGIC HERE'
                        data_node = str(rolling_node[1]).strip('[]\"\'')
                        data = {"properties": {"basic": {"nodes_table": [{"state": "drain", "node": data_node}]}}}
                        #client.put(url, data=json.dumps(data), headers={'content-type': 'application/json'})
                        print data

                    elif user_say == 'no' or user_say == 'n':
                        return False

                    else:
                        print 'Invalid User Input: Exiting Program.'


                    print 'READY TO ENABLE: ' + rolling_node[1] + '?'
                    user_say = None
                    while not user_say:
                        user_say = str(raw_input("Enter (Y)es or (N)o: ")).lower().strip()
                        user_say.lower()

                        if user_say == 'yes' or user_say == 'y':
                            print 'ENABLE LOGIC HERE'
                            data_node = str(rolling_node[1]).strip('[]\"\'')
                            data = {"properties": {"basic": {"nodes_table": [{"state": "active", "node": data_node}]}}}
                            #client.put(url, data=json.dumps(data), headers={'content-type': 'application/json'})
                            print data
                            print rolling_node[1]
                            exit()

                        elif user_say == 'no' or user_say == 'n':
                            return False

                        else:
                            print 'Invalid User Input: Exiting Program.'

            elif rolling_node[0] == first_rolling_node:
                print 'READY TO DRAIN: ' + rolling_node[0] + '?'
                user_say = None

                while not user_say:
                    user_say = str(raw_input("Enter (Y)es or (N)o: ")).lower().strip()
                    user_say.lower()

                    if user_say == 'yes' or user_say == 'y':
                        print 'DRAIN LOGIC HERE'
                        data_node = str(rolling_node[0]).strip('[]\"\'')
                        data = {"properties": {"basic": {"nodes_table": [{"state": "draining", "node": data_node}]}}}
                        #client.put(url, data=json.dumps(data), headers={'content-type': 'application/json'})
                        print data
                        print rolling_node[0]

                    elif user_say == 'no' or user_say == 'n':
                        return False

                    else:
                        print 'Invalid User Input: Exiting Program.'

            elif rolling_node[0] == last_rolling_node:
                print 'READY TO ENABLE: ' + rolling_node[0] + '?'

                user_say = None
                while not user_say:
                    user_say = str(raw_input("Enter (Y)es or (N)o: ")).lower().strip()
                    user_say.lower()
                    if user_say == 'yes' or user_say == 'y':
                        print 'ENABLE LOGIC HERE'
                        data_node = str(rolling_node[0]).strip('[]\"\'')
                        data = {"properties": {"basic": {"nodes_table": [{"state": "active", "node": data_node}]}}}
                        #client.put(url, data=json.dumps(data), headers={'content-type': 'application/json'})
                        print data

                    elif user_say == 'no' or user_say == 'n':
                        return False

                    else:
                        print 'Invalid User Input: Exiting Program.'

            else:
                print 'READY TO DRAIN: ' + str(rolling_node[1]) + ' AND ENABLE: ' + str(rolling_node[0]) + ' ?'
                user_say = None

                while not user_say:
                    user_say = str(raw_input("Enter (Y)es or (N)o: ")).lower().strip()
                    user_say.lower()
                    if user_say == 'yes' or user_say == 'y':
                        print 'ENABLE LOGIC HERE'

                        data = {"properties": {"basic": {"nodes_table": [{"state": "active", "node": rolling_node[0]}]}}}
                        #client.put(url, data=json.dumps(data), headers={'content-type': 'application/json'})
                        print data

                        print 'DRAIN LOGIC HERE'
                        data = {"properties": {"basic": {"nodes_table": [{"state": "draining", "node": rolling_node[1]}]}}}
                        #client.put(url, data=json.dumps(data), headers={'content-type': 'application/json'})
                        print data

                    elif user_say == 'no' or user_say == 'n':
                        return False

                    else:
                        print 'Invalid User Input: Exiting Program.'

try:

    # Do the HTTP GET to get the lists of pools.  We are only putting this client.get within a try
    # because if there is no error connecting on this one there shouldn't be an error connecting
    # on later client.get so that would be an unexpected exception.

    response = client.get(url)

    data = json.loads(response.content)

    if response.status_code == 200:

        if data.has_key('children'):
            pools = data['children']

            for p, pool in enumerate(pools):

                if pool['name'] == user_pool_name:
                    continue

                else:
                    pool_list.append(pool['name'])

            for pool in pool_list:
                response = client.get(url + "/" + pool)

                veritas_pool = json.loads(response.content)

                match_nodes = veritas_pool['properties']['basic']['nodes_table']

                for n in match_nodes:
                    if n['state'] == "active":
                        veritas_nodes[pool].append(n['node'])

            lb_connector()

            for true_key, true_value in veritas_nodes.items():
                for user_value in user_nodes.values():
                    for user_node_list in user_value:

                        for veritas_node_list in true_value:
                            u = re.sub(":.*", '', user_node_list)
                            v = re.sub(":.*", '', veritas_node_list)
                            if u == v:
                                action_nodes[true_key].append(veritas_node_list)

            lb_lazarus()


        else:
            print 'Error: No children found'

    else:
        print 'Error getting pool list: URL=%s Status=%d Id=%s: %s'\
              %(url, response.status_code, data['error_id'], data['error_text'])

except requests.exceptions.ConnectionError:
    print 'Error: Unable to connect to ' + url
    sys.exit(1)
