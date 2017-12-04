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
import time
import random

#------------------------------------------------------------------------------------------------------
# Static variables definitions
IP_ADDRESS_PREFIX = "10.1.0."
PORT_NUMBER = 61001
#------------------------------------------------------------------------------------------------------

class BlackboardServer(HTTPServer):

    def __init__(self, server_address, handler, node_id, vessel_list):
    # We call the super init
        HTTPServer.__init__(self,server_address, handler)
        # we create the dictionary of values
        self.Entries = {}
        # our own ID (IP is 10.1.0.ID)
        self.vessel_id = node_id
        # The list of other vessels
        self.vessels = vessel_list
        # Create vector clock and initalize all to 0
        self.vclock = dict.fromkeys(self.vessels, 0)

        self.print_vclock()
        self.update_clock({"10.1.0.1": 3, "10.1.0.2": 4})
        self.print_vclock()

    def tick(self):
        this_vessel = self.get_ip_address()
        self.vclock[this_vessel] = self.vclock[this_vessel] + 1
        return self.vclock[this_vessel]


    def update_clock(self, other_clock):
        for k, v in other_clock.items():
            self.vclock[k] = max(self.vclock[k], v) # choose highest value
        self.tick()

    def print_vclock(self):
        for k, v in self.vclock.items():
            print (k, v)

    # Closes socket before shutdown so it can be reused in tests.
    def shutdown(self):
        self.socket.close()
        HTTPServer.shutdown(self)


    # We delete a value received from the store
    def delete_value_in_store(self,key):
        # we delete a value in the store if it exists
        del self.Entries[key]


    def get_ip_address(self):
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
        if self.path == "/board":
            self.do_GET_Board()

        # Default?
        else:
            self.do_GET_Index()

#------------------------------------------------------------------------------------------------------
# GET logic - specific path
#------------------------------------------------------------------------------------------------------

    def do_GET_Board(self):
        self.set_HTTP_headers(200)
        temp_entries = []
        for item in sorted(self.server.Entries.values(), key=return_entry_timestamp, reverse=True):
            temp_entries.append(item)
        self.wfile.write(json.dumps(temp_entries))

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
        self.server.print_vclock()
        request_path = self.path
        parameters = self.parse_POST_request()
        print("Receiving a POST on %s" % self.path)
        print "parameters: %s" % parameters
        self.set_HTTP_headers(200)
        if request_path == "/board":
            keys = parameters.keys()
            id = None
            entry = None
            if 'entry' not in keys:
                self.error_out("No entry parameter")
                return
            entry = parameters['entry'][0]
            if 'id' not in keys:
                # generate id if not provided (new entry)
                id = str(uuid.uuid4())
            else:
                # get from parameters (modified entry)
                id = parameters['id'][0]
            self.success_out()

            entry_response = {}
            if id in self.server.Entries:
                #post is old, just update the text
                self.server.Entries[id]["text"] = entry
                entry_response = self.server.Entries[id]
            else:
                #post is new, apply a timestamp to order the entry.
                entry_response = {'id':id, 'timestamp': self.server.tick(), 'text':entry, 'vc': self.server.vclock}
                self.server.Entries[id] = entry_response
            self.retransmit(request_path, "POST", id, json.dumps(entry_response))

        elif request_path == "/propagate/board":
            id = parameters['id'][0]
            self.server.Entries[id] = json.loads(parameters['entry'][0])

            self.success_out()

        elif request_path.startswith("/propagate/entries/"):
            id = self.path.replace("/propagate/entries/", "")
            self.server.Entries[id] = parameters['entry'][0]
            self.success_out()


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


#------------------------------------------------------------------------------------------------------
# Request handling - DELETE
#------------------------------------------------------------------------------------------------------
    def do_DELETE(self):
        print("Receiving a DELETE on %s" % self.path)
        parameters = self.parse_POST_request()
        request_path = self.path
        keys = parameters.keys()
        if request_path.startswith("/board"):
            if 'id' not in keys:
                self.error_out("missing id")
                return
            id = parameters['id'][0]
            if id in self.server.Entries:
                self.success_out()
                self.server.delete_value_in_store(id)
                self.retransmit(request_path, "DELETE", id, None)
            else:
                #return not found
                self.error_out("Not found", 404)

        elif request_path.startswith("/propagate/board"):
            print ("Propagate!")
            if 'id' not in keys:
                self.error_out("missing id")
                print ("Propagate!:NOKEY")
                return
            id = parameters['id'][0]
            print ("Propagate!: ID %s" % id)
            if id in self.server.Entries:
                # Delete
                print ("Propagate!: ID FOUND %s")
                self.server.delete_value_in_store(id)
                self.success_out()
            else:
                #return not found
                print ("Propagate!: ID NOT FOUND")
                self.error_out("Not found", 404)


# file i/o
def read_file(filename):
    curr_path = sys.path[0]
    opened_file = open('%s/%s' % (curr_path, filename), 'r')
    all_content = ''
    for line in opened_file:
        all_content += line
    opened_file.close()
    return all_content


def return_entry_timestamp(entry):
    if 'timestamp' not in entry:
        return 0
    return entry['timestamp']

# Execute the code
if __name__ == '__main__':
    index = read_file("index.html");
    vessel_list = []
    vessel_id = 0
    # Checking the arguments
    if len(sys.argv) != 3: # 2 args, the script and the vessel name
        print("Arguments: vessel_ID number_of_vessels")
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
    print "All vessels:"
    for vessel in vessel_list:
        if vessel.endswith(str(vessel_id)):
            print "%s:%s <-- this server" % (vessel, PORT_NUMBER)
        else:
            print "%s:%s" % (vessel, PORT_NUMBER)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
        print("Stopping Server")
#-------------------------------------------------------------------------------------
