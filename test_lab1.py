import unittest
import requests
import json

class SimpleTestCase(unittest.TestCase):

    def setUp(self):
        """Call before every test case."""

    def tearDown(self):
        """Call after every test case."""

    def testA(self):
        # Posting an entry to board check if it exists:
        r = requests.get("http://10.1.0.1:61001/board")
        assert r.status_code == 200

        ENTRY_1 = "banana"
        r = requests.post("http://10.1.0.1:61001/board", data={'entry': ENTRY_1})
        assert r.status_code == 200

        r = requests.get("http://10.1.0.1:61001/board")
        data = json.loads(r.content)
        print "r: %s" % data

if __name__ == "__main__":
    unittest.main() # run all tests
