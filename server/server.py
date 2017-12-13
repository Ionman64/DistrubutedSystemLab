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
import sqlite3
import os
from collections import OrderedDict

#------------------------------------------------------------------------------------------------------
# Static variables definitions
IP_ADDRESS_PREFIX = "10.1.0."
PORT_NUMBER = 61001

#For the database
DATABASE_CREATE = 0
DATABASE_MODIFY = 1
DATABASE_DELETE = 2
DATABASE_BUFFERED = 1

# debug variables
DEBUG = False
LOCALHOST = "127.0.0.1"
PORT_PREFIX = "6100"
DEBUG_MODE = True

#------------------------------------------------------------------------------------------------------
class DatabaseHandler:
    def __init__(self, name):
        self.database = (str(name) + ".sqlite")
        if DEBUG_MODE:
            print ("*************WARNING: DEBUG MODE ACTIVE**************")
            if (os.path.exists(self.database)):
                os.remove(self.database)
                print ("DATABASE DELETED")
        if not os.path.exists(self.database):
            conn = self.get_connection()
            cur = conn.cursor()
            print ("CREATED DATABASE")
            cur.execute("CREATE TABLE posts (id VARCHAR(36), entry VARCHAR(1000), action INT, logical_timestamp INT, sequence_number INT, unique(id, logical_timestamp))")
            print ("CREATED TABLES")

    def get_connection(self):
        try:
            return sqlite3.connect(self.database)
        except Exception as ex:
            raise Exception(ex)

    def get_posts(self):
        conn = self.get_connection()
        cur = conn.cursor()

        get_all_query = "SELECT id, entry, sequence_number FROM posts GROUP BY id HAVING action != 2 ORDER BY sequence_number, logical_timestamp"
        cur = cur.execute(get_all_query)
        entries = OrderedDict()
        for row in cur.fetchall():
            entries[row[0]] = {"id":row[0], "text":row[1], "seq":row[2]}
        return entries

    def post_deleted(self, id):
        conn = self.get_connection()
        cur = conn.cursor()
        try:
            cur.execute("SELECT 1 FROM posts WHERE id = ? AND action = ?", (id, DATABASE_DELETE))
            if cur.rowcount > 0:
                return True
            return False
        except Exception as ex:
            print(ex)
            return False
        finally:
            conn.close()

    def get_logical_clock(self, id):
        conn = self.get_connection()
        cur = conn.cursor()
        try:
            cur = conn.execute("SELECT IFNULL(MAX(logical_timestamp), -1) FROM posts WHERE id = ?", [id])
            if (cur.rowcount > 0):
                return -1
            for row in cur.fetchone():
                return int(row)
        except Exception as ex:
            raise ex
            print(ex)
            return None
        finally:
            conn.close()

    def save_post(self, id, entry, action, logical_timestamp=-1, sequence_number=0):
        if self.post_deleted(id):
            return False
        if (logical_timestamp == -1):
            logical_timestamp = self.get_logical_clock(id)
        if (logical_timestamp == None):
            raise Exception("Could not get logical timestamp")
            return
        logical_timestamp += 1
        if (action < 0 or action > 2):
            print ("Illegal action")
            return
        conn = self.get_connection()
        cur = conn.cursor()
        try:

            if action == DATABASE_MODIFY:
                # keep the same seq_number
                cur.execute('SELECT sequence_number FROM posts WHERE id=?', (id,))
                sequence_number = cur.fetchone()[0]

            cur.execute("INSERT INTO posts (id, entry, action, logical_timestamp, sequence_number) VALUES (?, ?, ?, ?, ?)",(id, entry, action, logical_timestamp, sequence_number))
            conn.commit()
            if cur.rowcount > 0:
                #self.fix_buffer_for_entry(id)
                return True
            return False
        except Exception as ex:
            print (ex)
            return False
        finally:
            conn.close()

    def delete_post(self, id, logical_timestamp=-1, sequence_number=0):
        self.save_post(id, "", DATABASE_DELETE, logical_timestamp, )

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
        self.database = DatabaseHandler(node_id)
        # Create vector clock and initalize all to 0
        self.vclock = dict.fromkeys(self.vessels, 0)

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
        self.database.delete_post(key, self.database.get_logical_clock(key), self.vclock[self.get_ip_address()])


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
        self.wfile.write(json.dumps(self.server.database.get_posts()))

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
        print "parameters: %s" % parameters
        self.set_HTTP_headers(200)
        if request_path == "/board":
            keys = parameters.keys()
            entry_id = None
            entry = None
            if 'entry' not in keys:
                self.error_out("No entry parameter")
                return
            self.success_out()
            entry = parameters['entry'][0]
            action = None
            tick = self.server.tick()
            print ("TICK : %i" % tick)
            if 'id' not in keys:
                # generate id if not provided (new entry)
                entry_id = str(uuid.uuid4())
                self.server.database.save_post(entry_id, entry, DATABASE_CREATE, -1, tick)
                action = DATABASE_CREATE
            else:
                # get from parameters (modified entry)
                entry_id = parameters['id'][0]
                self.server.database.save_post(entry_id, entry, DATABASE_MODIFY, self.server.database.get_logical_clock(entry_id), tick)
                action = DATABASE_MODIFY
            entry_response = {'id':entry_id, 'action':action, 'logical_clock': self.server.vclock[self.server.get_ip_address()], "logical_timestamp": self.server.database.get_logical_clock(entry_id), 'text':entry, 'pid': self.server.get_ip_address(), 'vc': self.server.vclock}
            self.retransmit(request_path, "POST", entry_id, json.dumps(entry_response))

        elif request_path == "/propagate/board":
            content = json.loads(parameters['entry'][0])
            id = content["id"]
            entry = content["text"]
            #pid = content['pid']
            logical_timestamp = content["logical_timestamp"]
            action = content["action"]
            incoming_vclock = content['vc']
            self.success_out()
            self.server.update_clock(incoming_vclock)
            self.server.print_vclock()
            self.server.database.save_post(id, entry, action, logical_timestamp, self.server.vclock[self.server.get_ip_address()])



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
            entry_id = parameters['id'][0]
            if self.server.database.get_logical_clock(entry_id) > -1:
                self.success_out()
                self.server.delete_value_in_store(entry_id)
                self.retransmit(request_path, "DELETE", entry_id, None)
            else:
                #return not found
                self.error_out("Not found", 404)

        elif request_path.startswith("/propagate/board"):
            if 'id' not in keys:
                self.error_out("missing id")
                print ("Propagate!:NOKEY")
                return
            entry_id = parameters['id'][0]
            print ("Propagate!: ID %s" % entry_id)
            if self.server.database.get_logical_clock(entry_id) > -1:
                # Delete
                print ("ID FOUND")
                self.server.delete_value_in_store(entry_id)
                self.success_out()
            else:
                #return not found
                print ("Propagate!: ID NOT FOUND")
                self.error_out("Not found", 404)


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

# Execute the code
if __name__ == '__main__':
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
