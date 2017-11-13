import unittest
import requests
import json

POST_ID = None

class SimpleTestCase(unittest.TestCase):

    def setUp(self):
        """Call before every test case."""

    def tearDown(self):
        """Call after every test case."""

    def testBoard(self):
        r = requests.get("http://10.1.0.1:61001/board")
        assert r.status_code == 200
    def testEntryAndModify(self):
        ENTRY_1 = "banana"
        r = requests.post("http://10.1.0.1:61001/board", data={'entry': ENTRY_1})
        data = json.loads(r.text)
        print data
        POST_ID = data["id"]
        assert r.status_code == 200
        #modify
        ENTRY_1 = "apple"
        r = requests.post("http://10.1.0.1:61001/board" + "/" + POST_ID, data={'entry': ENTRY_1})
        data = json.loads(r.text)
        assert r.status_code == 200
    def testEntry(self):
        # Posting an entry to board check if it exists:
        ENTRY_1 = "banana"
        r = requests.post("http://10.1.0.1:61001/board", data={'entry': ENTRY_1})
        assert r.status_code == 200
    def testDelete(self):
        ENTRY_1 = "banana"
        r = requests.post("http://10.1.0.1:61001/board", data={'entry': ENTRY_1})
        data = json.loads(r.text)
        print data
        POST_ID = data["id"]
        assert r.status_code == 200
        #modify
        ENTRY_1 = "apple"
        r = requests.delete("http://10.1.0.1:61001/board" + "/" + POST_ID)
        assert r.status_code == 200
        
if __name__ == "__main__":
    unittest.main() # run all tests
