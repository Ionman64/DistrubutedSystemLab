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
import sqlite3
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
TIE_BREAKER = False
TRAITORS = 1

class BlackboardServer(HTTPServer):

    def __init__(self, server_address, handler, node_id, vessel_list):
    # We call the super init
        HTTPServer.__init__(self,server_address, handler)
        # our own ID (IP is 10.1.0.ID)
        self.vessel_id = node_id
        # The list of other vessels
        self.vessels = vessel_list

        self.byzantine_votes = {}
        self.vector_byzantine_votes = {}
        self.isByzantineNode = False
        self.round = 0
        self.result_vector = {}

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
    def propagate_value_to_vessels(self, path, action_type, key, value, ):
        # We iterate through the vessel list
        for vessel in self.vessels:
            # We should not send it to our own IP, or we would create an infinite loop of updates
            if vessel != self.get_ip_address():
                # A good practice would be to try again if the request failed
                # Here, we do it only once
                print "---> propagating to %s" % vessel
                self.contact_vessel(vessel, path, action_type, key, value)


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
            self.wfile.write(json.dumps(self.server.result_vector))
            self.finish()
            #self.success_out()
        else:
            self.do_GET_Index()

#------------------------------------------------------------------------------------------------------
# GET logic - specific path
#----------------------------------------------------------------------------------------------------

    def do_GET_Index(self):
        #output index.html
        self.set_HTTP_headers(200)
        self.wfile.write(index)

    def compute_byzantine_vote_round1(self, no_loyal, on_tie):
        result_vote = []
        for i in range(0,no_loyal):
            if i%2==0:
                result_vote.append(not on_tie)
            else:
                result_vote.append(on_tie)
        return result_vote

    def compute_byzantine_vote_round2(self, no_loyal,no_total,on_tie):
        result_vectors=[]
        for i in range(0,no_loyal):
            if i%2==0:
                result_vectors.append([on_tie]*no_total)
            else:
                result_vectors.append([not on_tie]*no_total)
        return result_vectors

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
        print "parameters: %s" % parameters
        self.set_HTTP_headers(200)

        if request_path == "/vote/attack":
            print "I am voting to attack"
            self.server.byzantine_votes[self.server.get_ip_address()] = True
            self.success_out()
            self.retransmit("/vote", "POST", self.server.get_ip_address(), "True")
            

        if request_path == "/vote/retreat":
            print "I am voting to retreat"
            self.server.byzantine_votes[self.server.get_ip_address()] = False
            self.success_out()
            self.retransmit("/vote", "POST", self.server.get_ip_address(), "False")
            

        if request_path == "/vote/byzantine":
            print "I am voting to byzantine"
            self.server.isByzantineNode = True
            self.server.byzantine_votes[self.server.get_ip_address()] = False 
            self.success_out()
            vote = self.compute_byzantine_vote_round1(len(self.server.vessels)-TRAITORS, TIE_BREAKER)
            i = 0
            for vessel in self.server.vessels:
                self.server.contact_vessel(vessel, "/propagate/vote", "POST", self.server.get_ip_address(), vote[i])
                i = i + 1
            

        if request_path == "/propagate/vote":
            id_sender = parameters['id'][0]
            value = parameters['entry'][0]
            if value == 'True' or value == 'False':
                # its a vote
                print "Receiving vote"
                if value == 'True':
                    self.server.byzantine_votes[id_sender] = True
                if value == 'False':
                    self.server.byzantine_votes[id_sender] = False
            else:
                # its a dict
                "Receiving vote array"
                self.server.vector_byzantine_votes[id_sender] = json.loads(value)

        if self.isRoundOne() and self.server.round == 0:
            print "It's Round One"
            print "byz_votes: %s" % self.server.byzantine_votes
            self.server.vector_byzantine_votes[self.server.get_ip_address()] = self.server.byzantine_votes
            self.retransmit("/vote", "POST", self.server.get_ip_address(), json.dumps(self.server.byzantine_votes))
            self.server.round = 1

        if self.isRoundTwo() and self.server.round == 1:
            print "It's Round Two"
            print "byz_votes: %s" % self.server.vector_byzantine_votes
            self.server.round = 2
            if self.server.isByzantineNode:
                self.server.result_vector = self.compute_byzantine_vote_round2(len(self.server.vessels)-TRAITORS,len(self.server.vessels)+1,TIE_BREAKER)
            else:
                self.server.result_vector = evaluate_votes(self.server.vessels, self.server.vector_byzantine_votes)

    def has_all_votes(self):
         return len(self.server.byzantine_votes) == len(self.server.vessels)

    def has_all_vector_votes(self):
         return len(self.server.vector_byzantine_votes) == len(self.server.vessels)

    def isRoundOne(self):
        if not self.has_all_votes():
           return False
        success = True
        for key in self.server.byzantine_votes:
            if type(self.server.byzantine_votes[key]) != type(True):
                success = False
        return success

    def isRoundTwo(self):
        if not self.has_all_vector_votes():
               return False
        success = True
        for key in self.server.vector_byzantine_votes:
            if type(self.server.vector_byzantine_votes[key]) != type({}):
                success = False
        return success


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
            thread = Thread(target=self.server.propagate_value_to_vessels,args=(action, action_type, key, value))
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

def evaluate_votes(vessels, vector):
    result_vector = {}
    #list_of_nodes = vector.keys()TIE_BREAKER = False
    #nodes = [1,2,3,4] 
    #this should be the vessel list
    for node in vessels:
        #if node == server.get_ip_address():
        #continue
        for index in range(len(vessels)):
            count_true = count_by_index(vector, node, True)
            count_false = count_by_index(vector, node, False)
            if (count_true > count_false):
                result_vector[node] = True
            elif (count_true < count_false):
                result_vector[node] = False
            else:
                result_vector[node] = TIE_BREAKER
    return result_vector

def count(dictionary, filter):
    if type(dictionary) != type({}):
        raise Exception("Tried to count something other than a dict")
    count = 0
    for key in dictionary:
        if dictionary[key] == filter:
            count = count + 1
    return count

def count_by_index(vector, index, filter):
    if type(vector) != type({}):
        raise Exception("Tried to count something other than a dict")
    count = 0
    for key in vector:
        if vector[key][index] == filter:
            count = count + 1
    return count

if __name__ == '__main__':
    #TEST

    #testvector = {1: {1: False, 2: False, 3: True, 4: True},
    #   2: {1: False, 2: False, 3: True, 4: True},
    #   3: {1: False, 2: False, 3: True, 4: True},
    #   4: {1: False, 2: False, 3: True, 4: False}}
    #print "result: %s" % evaluate_votes(testvector)

    index = read_file("index.html");
    vessel_list = []
    vessel_id = 0
    # Checking the arguments
    nr_args = len(sys.argv)
    if nr_args < 3 or nr_args > 4: # 2 args, the script and the vessel name
        print("Arguments: vessel_ID number_of_vessels [--debug]" )

    elif len(sys.argv) == 4 and sys.argv[3] == "--debug":
        # Set port as id instead of ip for running on localhost:
        DEBUG = True
        vessel_id = int(sys.argv[1])
        for i in range(1, int(sys.argv[2])+1):
            vessel_list.append(PORT_PREFIX + str(i))
        # We launch a server
        port_nr = int(PORT_PREFIX + str(vessel_id))
        server = BlackboardServer((LOCALHOST, port_nr), BlackboardRequestHandler, vessel_id, vessel_list)
        print("Starting DEBUG server on port: %s:%d" % (LOCALHOST, port_nr))
    else:
        # We need to know the vessel IP
        vessel_id = int(sys.argv[1])
        # We need to write the other vessels IP, based on the knowledge of their number
        for i in range(1, int(sys.argv[2])+1):
            vessel_list.append(IP_ADDRESS_PREFIX + ("%d" % i)) # We can add ourselves, we have a test in the propagation

        # We launch a server
        server = BlackboardServer(('', PORT_NUMBER), BlackboardRequestHandler, vessel_id, vessel_list)
        print("Starting the server on port: %d" % PORT_NUMBER)


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
        print("Stopping Server")
#-------------------------------------------------------------------------------------
