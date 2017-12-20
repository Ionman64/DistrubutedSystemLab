# coding=utf-8
#------------------------------------------------------------------------------------------------------
# TDA596 Labs - Server Skeleton
# server/server.py
# Input: Node_ID total_number_of_ID
# Student Group: 23
# Student names: Henrick Nume & Peter Pickerill
#------------------------------------------------------------------------------------------------------
# We import various libraries
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler # Socket specifically designed to handle HTTP requests
import sys # Retrieve arguments
from urlparse import parse_qs # Parse POST data
from httplib import HTTPConnection # Create a HTTP connection, as a client (for POST requests to the other vessels)
from urllib import urlencode # Encode POST content into the HTTP header
from codecs import open # Open a file
from threading import  Thread # Thread Management
import uuid
import json
import os
from collections import OrderedDict
from datetime import datetime

# Static variables definitions
IP_ADDRESS_PREFIX = "10.1.0."
PORT_NUMBER = 61001

# debug variables
DEBUG = False
LOCALHOST = "127.0.0.1"
PORT_PREFIX = "6100"
TIE_BREAKER = True
TRAITORS = 1

class BlackboardServer(HTTPServer):

    def __init__(self, server_address, handler, node_id, vessel_list):
    # We call the super init
        HTTPServer.__init__(self, server_address, handler)
        # our own ID (IP is 10.1.0.ID)
        self.vessel_id = node_id
        # The list of other vessels
        self.vessels = vessel_list

        self.byzantine_votes = {}
        self.vector_byzantine_votes = {}
        self.isByzantineNode = False
        self.round = 0
        self.result_vector = {}
        self.has_voted = False

    # Closes socket before shutdown so it can be reused in tests.
    def shutdown(self):
        self.socket.close()
        HTTPServer.shutdown(self)


    def get_ip_address(self):
        if DEBUG:
            # use port instead of ip when running all vessels locally
            return PORT_PREFIX + str(self.vessel_id)
        return IP_ADDRESS_PREFIX + str(self.vessel_id)


    # Contact a specific vessel with a set of variables to transmit to it
    def contact_vessel(self, vessel_ip, path, action_type, key, value):
        # the Boolean variable we will return
        success = False
        # The variables must be encoded in the URL format, through urllib.urlencode
        post_content = urlencode({'id': key, 'entry': value})
        # the HTTP header must contain the type of data we are transmitting, here URL encoded
        headers = {"Content-type": "application/x-www-form-urlencoded"}
        # We should try to catch errors when contacting the vessel
        try:
            # We contact vessel:PORT_NUMBER since we all use the same port
            # We can set a timeout, after which the connection fails if nothing happened
            if DEBUG:
                # vessel_ip is portnr here
                connection = HTTPConnection("%s:%s" % (LOCALHOST, vessel_ip), timeout = 30)
            else:
                connection = HTTPConnection("%s:%d" % (vessel_ip, PORT_NUMBER), timeout = 30)
            # We send the HTTP request
            connection.request(action_type, path, post_content, headers)
            # We retrieve the response
            response = connection.getresponse()
            # We want to check the status, the body should be empty
            status = response.status
            # If we receive a HTTP 200 - OK
            if status == 200:
                success = True
        # We catch every possible exceptions
        except Exception as e:
            print "Error while contacting %s" % vessel_ip
            # printing the error given by Python
            print(e)

        # we return if we succeeded or not
        return success


    # We send a received value to all the other vessels of the system
    def propagate_value_to_vessels(self, path, action_type, key, value):
        # We iterate through the vessel list
        for vessel in self.vessels:
            # We should not send it to our own IP, or we would create an infinite loop of updates
            if vessel != self.get_ip_address():
                # A good practice would be to try again if the request failed
                # Here, we do it only once
                print "---> propagating to %s" % vessel
                self.contact_vessel(vessel, path, action_type, key, value)


    def propagate_byz_votes(self, votes):
        # set args
        path = "/propagate/vote"
        action_type = "POST"
        key = self.get_ip_address()
        sorted_vessels = sorted(self.vessels)
        values = []
        # convert vote array
        for vote in votes:
            if isinstance(vote, list):
                # {1: True, 2: False, 3: False, 4: True}
                vector = {}
                for i in range(len(vote)):
                    v_id = sorted_vessels[i]
                    val = "True" if vote[i] else "False"
                    vector[v_id] = val
                values.append(json.dumps(vector))
            else:
                # True / False
                val = "True" if vote else "False"
                values.append(val)
        # propagate
        sorted_vessels.remove(key) #remove youself
        for i in range(len(sorted_vessels)):
            print "---> propagating to %s , key:%s  value: %s" % (sorted_vessels[i], key, values[i])
            self.contact_vessel(sorted_vessels[i], path, action_type, key, values[i])

#------------------------------------------------------------------------------------------------------
# This class implements the logic when a server receives a GET or POST request
# It can access to the server data through self.server.*
# i.e. the store is accessible through self.server.store
# Attributes of the server are SHARED accross all request hqndling/ threads!
class BlackboardRequestHandler(BaseHTTPRequestHandler):
#------------------------------------------------------------------------------------------------------

    # Disable logging
    def log_message(self, format, *args):
        return

    # We fill the HTTP headers
    def set_HTTP_headers(self, status_code = 200):
         # We set the response status code (200 if OK, something else otherwise)
        self.send_response(status_code)
        # We set the content type to HTML
        #self.send_header("Content-type","text/html")
        # No more important headers, we can close them
        self.end_headers()


    # a POST request must be parsed through urlparse.parse_QS, since the content is URL encoded
    def parse_POST_request(self):
        post_data = ""
        # We need to parse the response, so we must know the length of the content
        length = int(self.headers['Content-Length'])
        # we can now parse the content using parse_qs
        post_data = parse_qs(self.rfile.read(length), keep_blank_values=1)
        # we return the data
        return post_data

#------------------------------------------------------------------------------------------------------
# Request handling - GET
#------------------------------------------------------------------------------------------------------
    # This function contains the logic executed when this server receives a GET request
    # This function is called AUTOMATICALLY upon reception and is executed as a thread!
    def do_GET(self):
        #print("Receiving a GET on path %s" % self.path)

        # Here, we should check which path was requested and call the right logic based on it
        if self.path == "/vote/result":
            self.set_HTTP_headers(200)
            final_result = "undecided"
            if len(self.server.result_vector) > 0:
                final_result = calc_final_result(self.server.result_vector)

            sorted_result_vector = OrderedDict(sorted(self.server.result_vector.items()))
            response = {'result': final_result, 'result_vector': sorted_result_vector}
            self.wfile.write(json.dumps(response))
            print "VotesR1: %d" % len(self.server.byzantine_votes)
            print "VotesR2: %d" % len(self.server.vector_byzantine_votes)

        else:
            self.do_GET_Index()

#------------------------------------------------------------------------------------------------------
# GET logic - specific path
#----------------------------------------------------------------------------------------------------

    def do_GET_Index(self):
        #output index.html
        self.set_HTTP_headers(200)
        self.wfile.write(index)

#------------------------------------------------------------------------------------------------------
# Request handling - POST
#------------------------------------------------------------------------------------------------------
    def do_POST(self):
        # Here, we should check which path was requested and call the right logic based on it
        # We should also parse the data received
        # and set the headers for the client
        request_path = self.path
        parameters = self.parse_POST_request()
        print("Receiving a POST on %s" % self.path)
        #print "parameters: %s" % parameters
        self.success_out()

        if request_path == "/vote/attack":
            print "I am voting to attack"
            self.server.byzantine_votes[self.server.get_ip_address()] = True
            self.server.voted = True
            self.retransmit("/vote", "POST", self.server.get_ip_address(), "True")
            

        if request_path == "/vote/retreat":
            print "I am voting to retreat"
            self.server.byzantine_votes[self.server.get_ip_address()] = False
            self.server.voted = True
            self.retransmit("/vote", "POST", self.server.get_ip_address(), "False")
            

        if request_path == "/vote/byzantine":
            print "I am voting to byzantine"
            self.server.isByzantineNode = True
            self.server.byzantine_votes[self.server.get_ip_address()] = False
            self.server.voted = True
            fake_votes = compute_byzantine_vote_round1(len(self.server.vessels)-TRAITORS, TIE_BREAKER)
            print "Fake votes: %s" % fake_votes
            self.retransmit_byz_votes(fake_votes)
        
        # call this from all nodes and refresh page to vote again.
        if request_path == "/reset":
            print "Resetting..."
            self.server.byzantine_votes = {}
            self.server.vector_byzantine_votes = {}
            self.server.isByzantineNode = False
            self.server.round = 0
            self.server.result_vector = {}
            self.server.has_voted = False

        if request_path == "/propagate/vote":
            # removE?
            id_sender = parameters['id'][0]
            value = parameters['entry'][0]
            if value == 'True' or value == 'False':
                # its a vote
                print "Receiving R1 vote"
                if value == 'True':
                    self.server.byzantine_votes[id_sender] = True
                if value == 'False':
                    self.server.byzantine_votes[id_sender] = False
            else:
                # its a dict
                print "Receiving R2 vote array"
                self.server.vector_byzantine_votes[id_sender] = json.loads(value)

        if self.server.isByzantineNode:
            if self.has_all_votes() and self.server.round == 0:
                self.server.round = 1
                print "Byz have all votes and sending fakes"
                #fake_votes = compute_byzantine_vote_round1(len(self.server.vessels)-TRAITORS, TIE_BREAKER)
                #self.retransmit_byz_votes(fake_votes)

            elif  self.server.round == 1:
                self.server.round = 2
                print "It's Round Two"
                print "# propagating false vectors"
                votes = compute_byzantine_vote_round2(len(self.server.vessels)-TRAITORS, len(self.server.vessels),  TIE_BREAKER)
                self.retransmit_byz_votes(votes)

        if not self.server.isByzantineNode:            
            if self.has_all_votes() and self.server.round == 0:
                print "It's Round Two"
                self.server.round = 2
                print "# propagateing own vector"
                self.server.vector_byzantine_votes[self.server.get_ip_address()] = self.server.byzantine_votes
                self.retransmit("/vote", "POST", self.server.get_ip_address(), json.dumps(self.server.byzantine_votes))
        
        print "VotesR1: %d" % len(self.server.byzantine_votes)
        print "VotesR2: %d" % len(self.server.vector_byzantine_votes)
        # Calc result
        if self.has_all_vector_votes() and len(self.server.result_vector) == 0:
            print "Calculating results..."
            #print "input:"
            #print_vector(self.server.vector_byzantine_votes)
            self.server.result_vector = evaluate_votes(self.server.vector_byzantine_votes, self.server.get_ip_address())
            #print "result:"
            #print_vector(self.server.result_vector)


    def has_all_votes(self):
        return len(self.server.byzantine_votes) == len(self.server.vessels)
    
    def has_all_vector_votes(self):
        return len(self.server.vector_byzantine_votes) == len(self.server.vessels)

    def success_out(self):
        self.set_HTTP_headers(200)
        self.wfile.write(json.dumps({"status": "OK"}))
        self.wfile.close()

    def error_out(self, reason=None, header=200):
        self.set_HTTP_headers(header)
        self.wfile.write(json.dumps({"status": "FAIL", "reason":reason}))
        self.wfile.close()

    def retransmit(self, action, action_type, key = None, value = None):
        action = ''.join(["/propagate", action])
        print "retransmitting to vessels on" + action
        thread = Thread(target=self.server.propagate_value_to_vessels, args=(action, action_type, key, value))
        # We kill the process if we kill the server
        thread.daemon = True
        # We start the thread
        thread.start()

    def retransmit_byz_votes(self, votes):
        #retransmitting bool arr or  2d bool arr
        print "retransmitting byz votes for round %d:" % self.server.round
        thread = Thread(target=self.server.propagate_byz_votes, args=(votes,)) # wrap in tuple to force single argument
        # We kill the process if we kill the server
        thread.daemon = True
        # We start the thread
        thread.start()


# file i/o
def read_file(filename):
    curr_path = sys.path[0]
    f = open('%s/%s' % (curr_path, filename))
    content = f.read()
    f.close()
    return content


def return_entry_timestamp(entry):
    if 'timestamp' not in entry:
        return 0
    return entry['timestamp']


def evaluate_votes(vector, this_node):
    result_vector = {}
    sorted_nodes = sorted(vector)
    for node in sorted_nodes:
        count_true = count_by_index(vector, node, this_node, True)
        count_false = count_by_index(vector, node, this_node, False)
        #print "node:%s T: %d  F:%d" % (str(node) ,count_true, count_false)
        if (count_true > count_false):
            result_vector[node] = True
        elif (count_true < count_false):
            result_vector[node] = False
        else:
            result_vector[node] = TIE_BREAKER
            #result_vector[node] = 'UNKNOWN'
    return result_vector


def count(dictionary, filter):
    if type(dictionary) != type({}):
        raise Exception("Tried to count something other than a dict")
    count = 0
    for key in dictionary:
        if dictionary[key] == filter:
            count = count + 1
    return count

def count_by_index(vector, index, ignore_self, filter):
    if type(vector) != type({}):
        raise Exception("Tried to count something other than a dict")
    count = 0
    for key in vector:
        #if key == ignore_self: remove your own vector row
        if key == index:
            continue # dont count your own value
        if vector[key][index] == filter or vector[key][index] == str(filter):
            count = count + 1
    return count

#------------------ Byzantine Behaviour -------------------------
def compute_byzantine_vote_round1(no_loyal, on_tie):
    result_vote = []
    for i in range(0, no_loyal):
        if i%2 == 0:
            result_vote.append(not on_tie)
        else:
            result_vote.append(on_tie)
    return result_vote

def compute_byzantine_vote_round2(no_loyal, no_total, on_tie):
    result_vectors = []
    for i in range(0, no_loyal):
        if i%2 == 0:
            result_vectors.append([on_tie]*no_total)
        else:
            result_vectors.append([not on_tie]*no_total)
    return result_vectors

#-----------------------------------------------------------------

def calc_final_result(res_vector):
    final_result = "undecided"
    count_true = count(res_vector, True)
    count_false = count(res_vector, False)
    if count_true > count_false:
        final_result = "Attack"
    elif count_true < count_false:
        final_result = "Retreat"
    else:
        final_result = "Attack on tiebreaker" if TIE_BREAKER else "Retreat on tiebreaker" 
    return final_result

def print_vector(vector):
    for key in sorted(vector):
        print "Node:%s: %s" % (key, vector[key])
       
if __name__ == '__main__':
    
    #TEST
    """
    # test evaluate_votes
    testvector1 = {
        1: {1: True, 2: True, 3: True},
        2: {1: False, 2: True, 3: False},
        3: {1: True, 2: True, 3: False}
    }
    res = evaluate_votes(testvector1, 1)
    print "p1 test: %s" % (res == {1: True, 2: True, 3: True})
    print calc_final_result(res)
    
    testvector2 = {
        1: {1: False, 2: False, 3: False},
        2: {1: False, 2: True, 3: False},
        3: {1: True, 2: True, 3: False}
    }
    res = evaluate_votes(testvector2, 2)
    print "p2 test: %s" % (res == {1: True, 2: True, 3: False})
    print calc_final_result(res)
    
    testvector = {
        1: {1: True, 2: False, 3: False, 4: True},
        2: {1: True, 2: False, 3: False, 4: True},
        3: {1: True, 2: False, 3: False, 4: False},
        4: {1: False, 2: False, 3: False, 4: False}  
    }
    res = evaluate_votes(testvector, 1)
    print "p1 res: %s" % res
    print calc_final_result(res)

    testvector = {
        1: {1: True, 2: False, 3: False, 4: True},
        2: {1: True, 2: False, 3: False, 4: True},
        3: {1: True, 2: False, 3: False, 4: False},
        4: {1: True, 2: True, 3: True, 4: True}  
    }
    res = evaluate_votes(testvector, 2)
    print "p2 res: %s" % res
    print calc_final_result(res)

    testvector = {
        1: {1: True, 2: False, 3: False, 4: True},
        2: {1: True, 2: False, 3: False, 4: True},
        3: {1: True, 2: False, 3: False, 4: False},
        4: {1: False, 2: True, 3: False, 4: True}  
    }
    res = evaluate_votes(testvector, 3)
    print "p3 res: %s" % res
    print calc_final_result(res)

    quit()
    #"""
    index = read_file("index.html")
    vessel_list = []
    vessel_id = 0
    # Checking the arguments
    nr_args = len(sys.argv)
    if nr_args < 3 or nr_args > 4: # 2 args, the script and the vessel name
        print "Arguments: vessel_ID number_of_vessels [--debug]"

    elif len(sys.argv) == 4 and sys.argv[3] == "--debug":
        # Set port as id instead of ip for running on localhost:
        DEBUG = True
        vessel_id = int(sys.argv[1])
        for i in range(1, int(sys.argv[2])+1):
            vessel_list.append(PORT_PREFIX + str(i))
        # We launch a server
        port_nr = int(PORT_PREFIX + str(vessel_id))
        server = BlackboardServer((LOCALHOST, port_nr), BlackboardRequestHandler, vessel_id, vessel_list)
        print "Starting DEBUG server on port: %s:%d" % (LOCALHOST, port_nr)
    else:
        # We need to know the vessel IP
        vessel_id = int(sys.argv[1])
        # We need to write the other vessels IP, based on the knowledge of their number
        for i in range(1, int(sys.argv[2])+1):
            vessel_list.append(IP_ADDRESS_PREFIX + ("%d" % i)) # We can add ourselves, we have a test in the propagation

        # We launch a server
        server = BlackboardServer(('', PORT_NUMBER), BlackboardRequestHandler, vessel_id, vessel_list)
        print "Starting the server on port: %d" % PORT_NUMBER


    # Printing all vessels
    print "This Server: %s" % vessel_id
    print "All vessels:"
    for vessel in vessel_list:
        if DEBUG:
            print "    %s:%s" % (LOCALHOST, vessel)
        else:
            print "    %s:%s" % (vessel, PORT_NUMBER)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
        print "Stopping Server"
