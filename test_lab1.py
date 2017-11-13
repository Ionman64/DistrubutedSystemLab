import os
import requests
from lab1 import Lab1
from lab1 import Lab1Topology



if __name__ == '__main__':
    print "---starting test---"
    # we set the log level to info, in order to display the server outputs as well
    #setLogLevel( 'info' )
    lab = Lab1()
    lab.run()
    r = requests.get("10.1.0.1:61001/board")
    print r
    print "---ending test---"
