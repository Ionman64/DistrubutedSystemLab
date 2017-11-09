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
#------------------------------------------------------------------------------------------------------

# Global variables for HTML templates
board_frontpage_footer_template = ""
board_frontpage_header_template = ""
boardcontents_template = ""
entry_template = ""

#------------------------------------------------------------------------------------------------------
# Static variables definitions
PORT_NUMBER = 61001
#------------------------------------------------------------------------------------------------------

Entries = {}

#------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------
class BlackboardServer(HTTPServer):
#------------------------------------------------------------------------------------------------------
	def __init__(self, server_address, handler, node_id, vessel_list):
	# We call the super init
		HTTPServer.__init__(self,server_address, handler)
		# we create the dictionary of values
		self.store = {}
		# We keep a variable of the next id to insert
		self.current_key = -1
		# our own ID (IP is 10.1.0.ID)
		self.vessel_id = vessel_id
		# The list of other vessels
		self.vessels = vessel_list
#------------------------------------------------------------------------------------------------------
	# We add a value received to the store
	def add_value_to_store(self, value):
		# We add the value to the store
		id =str(uuid.uuid4())
		Entries[id] = value
		return id
#------------------------------------------------------------------------------------------------------
	# We modify a value received in the store
	def modify_value_in_store(self,key,value):
		# we modify a value in the store if it exists
		Entries[key] = value
#------------------------------------------------------------------------------------------------------
	# We delete a value received from the store
	def delete_value_in_store(self,key):
		# we delete a value in the store if it exists
		del Entries[key]
#------------------------------------------------------------------------------------------------------
# Contact a specific vessel with a set of variables to transmit to it
	def contact_vessel(self, vessel_ip, path, action, key, value):
		# the Boolean variable we will return
		success = False
		# The variables must be encoded in the URL format, through urllib.urlencode
		post_content = urlencode({'action': action, 'key': key, 'value': value})
		# the HTTP header must contain the type of data we are transmitting, here URL encoded
		headers = {"Content-type": "application/x-www-form-urlencoded"}
		# We should try to catch errors when contacting the vessel
		try:
			# We contact vessel:PORT_NUMBER since we all use the same port
			# We can set a timeout, after which the connection fails if nothing happened
			connection = HTTPConnection("%s:%d" % (vessel, PORT_NUMBER), timeout = 30)
			# We only use POST to send data (PUT and DELETE not supported)
			action_type = "POST"
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
			print "Error while contacting %s" % vessel
			# printing the error given by Python
			print(e)

		# we return if we succeeded or not
		return success
#------------------------------------------------------------------------------------------------------
	# We send a received value to all the other vessels of the system
	def propagate_value_to_vessels(self, path, action, key, value):
		# We iterate through the vessel list
		for vessel in self.vessels:
			# We should not send it to our own IP, or we would create an infinite loop of updates
			if vessel != ("10.1.0.%s" % self.vessel_id):
				# A good practice would be to try again if the request failed
				# Here, we do it only once
				self.contact_vessel(vessel, path, action, key, value)
#------------------------------------------------------------------------------------------------------







#------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------
# This class implements the logic when a server receives a GET or POST request
# It can access to the server data through self.server.*
# i.e. the store is accessible through self.server.store
# Attributes of the server are SHARED accross all request hqndling/ threads!
class BlackboardRequestHandler(BaseHTTPRequestHandler):
#------------------------------------------------------------------------------------------------------
	# We fill the HTTP headers
	def set_HTTP_headers(self, status_code = 200):
		 # We set the response status code (200 if OK, something else otherwise)
		self.send_response(status_code)
		# We set the content type to HTML
		#self.send_header("Content-type","text/html")
		# No more important headers, we can close them
		self.end_headers()
#------------------------------------------------------------------------------------------------------
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
#------------------------------------------------------------------------------------------------------
# Request handling - GET
#------------------------------------------------------------------------------------------------------
	# This function contains the logic executed when this server receives a GET request
	# This function is called AUTOMATICALLY upon reception and is executed as a thread!
	def do_GET(self):
		print("Receiving a GET on path %s" % self.path)

		# Here, we should check which path was requested and call the right logic based on it
		if self.path == "/board":
			self.do_GET_Board()

		elif self.path == "/entries":
			self.do_GET_Entries()

		# Default?
		else:
			self.do_GET_Index()

#------------------------------------------------------------------------------------------------------
# GET logic - specific path
#------------------------------------------------------------------------------------------------------
	def do_GET_Entries(self):
		self.set_HTTP_headers(200)
		self.wfile.write(self.gen_entries_html)

	def gen_entries_html(self):
		html_response = ""
		for key, value in Entries.iteritems():
			html_response += entry_template % ("entries/", key, value )
		return html_response

	def do_GET_Board(self):
		self.set_HTTP_headers(200)

		entry1 = entry_template % ("entries/1", 1, "First message" )  # (action, id ,entry)
		entry2 = entry_template % ("entries/2", 2, "Second message" )
		entries = "%s%s" % (entry1, entry2)
		#print entries
		board = boardcontents_template % ("Banana Board", self.gen_entries_html()) # (boardtitle, entries)
		#self.wfile.write(board)
		print(json.dumps(Entries))
		self.wfile.write(json.dumps(Entries))


	def do_GET_Index(self):
		# We set the response status code to 200 (OK)
		self.set_HTTP_headers(200)
		# We should do some real HTML here
		#In practice, go over the entries list,
		#produce the boardcontents part,
		#then construct the full page by combining all the parts ...

		header = board_frontpage_header_template
		body = boardcontents_template % ("My Board", "good day")
		footer = board_frontpage_footer_template % ("The dude and the other dude") 	#(groupMembers)
		self.wfile.write(header + body + footer)


#------------------------------------------------------------------------------------------------------
	# we might want some other functions
#------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------
# Request handling - POST
#------------------------------------------------------------------------------------------------------
	def do_POST(self):
		print("Receiving a POST on %s" % self.path)
		# Here, we should check which path was requested and call the right logic based on it
		# We should also parse the data received
		# and set the headers for the client


		if self.path == "/board":
			self.do_POST_Board()

	 	elif self.path.startswith("/entries/"):
			id = self.path.replace("/entries/", "")
			self.do_UPDATE_entries(id)

		# If we want to retransmit what we received to the other vessels
		pass
		retransmit = False # Like this, we will just create infinite loops!
		if retransmit:
			# do_POST send the message only when the function finishes
			# We must then create threads if we want to do some heavy computation
			#
			# Random content
			thread = Thread(target=self.server.propagate_value_to_vessels,args=("action", "key", "value") )
			# We kill the process if we kill the server
			thread.daemon = True
			# We start the thread
			thread.start()
#------------------------------------------------------------------------------------------------------
# POST Logic
#------------------------------------------------------------------------------------------------------
	# We might want some functions here as well
#------------------------------------------------------------------------------------------------------
	def do_UPDATE_entries(self,id):
		self.set_HTTP_headers(200)
		res = self.parse_POST_request()
		print res
		server.modify_value_in_store(id, res['entry'][0])
		self.wfile.write(json.dumps({"status": "OK"}))

	def do_POST_Board(self):
		self.set_HTTP_headers(200)
		res = self.parse_POST_request()
		server.add_value_to_store(res['entry'][0])
		self.wfile.write(json.dumps({"status": "OK"}))

# Request handling - DELETE
#------------------------------------------------------------------------------------------------------
	def do_DELETE(self):
		print("Receiving a DELETE on %s" % self.path)

		if self.path.startswith("/entries/"):
			id = self.path.replace("/entries/", "")
			self.do_DELETE_entries(id)

#---------------------------------------------------------------------------------
# DELETE Logic
	def do_DELETE_entries(self, id):
		self.set_HTTP_headers(200)
		if len(id) == 0:
			self.set_HTTP_headers(204)
			self.wfile.write(json.dumps({"status": "Not Found"}))
		else:
			server.delete_value_in_store(id)
			self.wfile.write(json.dumps({"status": "OK"}))

#-------------------------------------
# file i/o
def read_file(filename):
    opened_file = open(filename, 'r')
    all_content = ''
    for line in opened_file:
        all_content += line
    opened_file.close()
    return all_content
#------------------------------------------------------------------------------------------------------


# Execute the code
if __name__ == '__main__':

	## read the templates from the corresponding html files
	board_frontpage_header_template = index = read_file("index.html");
	#board_frontpage_header_template = read_file('board_frontpage_header_template.html')
	board_frontpage_footer_template = read_file('board_frontpage_footer_template.html')
	boardcontents_template = read_file('boardcontents_template.html')
	entry_template = read_file('entry_template.html')

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
			vessel_list.append("10.1.0.%d" % i) # We can add ourselves, we have a test in the propagation

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
#------------------------------------------------------------------------------------------------------
