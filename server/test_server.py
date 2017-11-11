import threading
import time
import unittest
import requests

# import SUT
from server import BlackboardServer, BlackboardRequestHandler

PORT = 61001
BASE_URL = 'http://127.0.0.1:%d' % PORT

# run tests: python test_server.py -v
class TestApiEndpoints(unittest.TestCase):
    bbserver = None
    server_thread = None

    def setUp(self):
        # Call before every test case.
        vessel_list = ['10.1.0.1']
        self.bbserver = BlackboardServer(('', PORT), BlackboardRequestHandler, 1, vessel_list)
        self.server_thread = threading.Thread(target=self.bbserver.serve_forever)
        self.server_thread.setDaemon(True)
        self.server_thread.start()
        # Wait a bit for the server to come up
        time.sleep(0.2)

    def tearDown(self):
        # Call after every test case
        self.bbserver.shutdown()
        # Wait for the server to shut down.
        self.server_thread.join()

    def test_board_should_be_empty(self):
        r = requests.get(BASE_URL + '/board')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {})

    def test_posted_entry_should_exist(self):
        r1 = requests.post(BASE_URL + '/board', data={'entry': 'banana'})
        self.assertEqual(r1.status_code, 200)
        posted_id = r1.json()['id']
        self.assertNotEqual(posted_id, None)

        r2 = requests.get(BASE_URL + '/board')
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.json()[posted_id], 'banana')

    def test_delete_entry(self):
        # Post two entries
        r1 = requests.post(BASE_URL + '/board', data={'entry': 'apple'})
        r2 = requests.post(BASE_URL + '/board', data={'entry': 'banana'})
        apple_id = r1.json()['id']
        # first delete should be successful
        r3 = requests.delete(BASE_URL + '/entries/' + apple_id)
        self.assertEqual(r3.status_code, 200)
        # deleting it again should not be.
        r4 = requests.delete(BASE_URL + '/entries/' + apple_id)
        self.assertEqual(r4.status_code, 404)

if __name__ == '__main__':
    unittest.main()  # run all tests
