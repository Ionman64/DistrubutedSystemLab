import unittest
import requests
import json

POST_ID = None

class SimpleTestCase(unittest.TestCase):

    def setUp(self):
        """Call before every test case."""

    def tearDown(self):
        """Call after every test case."""

    ''' def testBoard(self):
        r = requests.get("http://10.1.0.1:61001/board")
        assert r.status_code == 200
    def testEntryAndModify(self):
        ENTRY_1 = "banana"
        r = requests.post("http://10.1.0.1:61001/board", data={'entry': ENTRY_1})
        data = json.loads(r.text)
        POST_ID = data["id"]
        assert r.status_code == 200
        #modify
        ENTRY_1 = "apple"
        r = requests.post("http://10.1.0.1:61001/board" + "/" + POST_ID, data={'entry': ENTRY_1})
        assert r.status_code == 200
    def testEntry(self):
        # Posting an entry to board check if it exists:
        ENTRY_1 = "banana"
        r = requests.post("http://10.1.0.1:61001/board", data={'entry': ENTRY_1})
        assert r.status_code == 200
    def testDelete(self):
        r = requests.post("http://10.1.0.1:61001/board", data={'entry': "banana"})
        data = json.loads(r.text)
        POST_ID = data["id"]
        assert r.status_code == 200 '''
    def testStressTest(self):
        NUMBER_OF_NODES = 4
        NUMBER_OF_MESSAGES = 50
        success = True
        for k in range(NUMBER_OF_MESSAGES):
            ip_address = "http://10.1.0.%s:61001/board" % str(i+1)
            for i in range(NUMBER_OF_NODES):
                r = requests.post(ip_address, data={'entry': "I am %s sending %i" % (ip_address, i)})
            if success:
                success = (r.status_code == 200)
        assert success
         

        #r = requests.delete("http://10.1.0.1:61001/board/%s" % POST_ID)
        #assert r.status_code == 200
        
if __name__ == "__main__":
    unittest.main() # run all tests
