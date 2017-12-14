import unittest
import requests
import json

POST_ID = None

class SimpleTestCase(unittest.TestCase):

    def setUp(self):
        """Call before every test case."""

    def tearDown(self):
        """Call after every test case."""

    def testStressTest(self):
        NUMBER_OF_NODES = 8
        NUMBER_OF_MESSAGES = 50
        success = True
        for k in range(NUMBER_OF_MESSAGES):
            for i in range(NUMBER_OF_NODES):
                ip_address = "http://10.1.0.%s:61001/board" % str(i+1)
                r = requests.post(ip_address, data={'entry': "I am %s sending %i" % (ip_address, i)})
            if success:
                success = (r.status_code == 200)
        assert success


        #r = requests.delete("http://10.1.0.1:61001/board/%s" % POST_ID)
        #assert r.status_code == 200

if __name__ == "__main__":
    unittest.main() # run all tests
