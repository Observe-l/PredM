import sys
import optparse
import sumolib
import traci.constants as tc

import os
import time
import ray
import math
import pymysql
import sqlite3
import multiprocessing
import threading
import pandas as pd
from time import sleep

# we need to import python modules from the $SUMO_HOME/tools directory
if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("please declare environment variable 'SUMO_HOME'")

from sumolib import checkBinary  # noqa
import traci  # noqa
# import libsumo as traci




def run():
    """execute the TraCI control loop"""
    step = 0
    times = 0
    # we start with phase 2 where EW has green
    # traci.trafficlight.setPhase("0", 2)

    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        # Check Parking area
        
        
        # if traci.trafficlight.getPhase("0") == 2:
        #     # we are not already switching
        #     if traci.inductionloop.getLastStepVehicleNumber("0") > 0:
        #         # there is a vehicle from the north, switch
        #         traci.trafficlight.setPhase("0", 3)
        #     else:
        #         # otherwise try to keep green for EW
        #         traci.trafficlight.setPhase("0", 2)
    traci.close()
    sys.stdout.flush()

def get_options():
    optParser = optparse.OptionParser()
    optParser.add_option("--nogui", action="store_true",
                         default=False, help="run the commandline version of sumo")
    options, args = optParser.parse_args()
    return options

# task_csv()

if __name__ == "__main__":
    options = get_options()
    
    # this script has been called from the command line. It will start sumo as a
    # server, then connect and run
    if options.nogui:
        sumoBinary = checkBinary('sumo')
    else:
        sumoBinary = checkBinary('sumo-gui')

    # net = sumolib.net.readNet("traci_tls/data/cross.net.xml")
    # print(net.getNode('51').getCoord())
    # nextNodeID = net.getEdge('51i').getToNode().getID()
    # print(nextNodeID)
    # first, generate the route file for this simulation
    # generate_routefile()

    # this is the normal way of using traci. sumo is started as a
    # subprocess and then the python script connects and runs
    traci.start([sumoBinary, "-c", "SUMO_data/cross.sumocfg",
                             "--tripinfo-output", "SUMO_data/tripinfo.xml"])
    
    run()


