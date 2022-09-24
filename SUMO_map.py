import sys
import optparse
import sumolib
import traci.constants as tc

import os
import numpy as np
import pandas as pd
import time
import ray
import math
import pymysql
import sqlite3
import multiprocessing
import threading
import pandas as pd
from util.lorry_manage import Lorry
from util.factory_manage import Factory

PARK_CAPACITY = 4

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
    prk_count = {'Factory1_0': 0,'Factory1_1': 0,
                 'Factory2_0': 0,'Factory2_1': 0,
                 'Factory3_0': 0,'Factory3_1': 0,
                 'Factory4_0': 0,'Factory4_1': 0}
    # Generate 8 lorries
    lorry = [Lorry(lorry_id=f'lorry_{i}') for i in range(8)]
    # Gendrate 4 Factories
    factory = [Factory(factory_id=f'Factory{i+1}', next_factory=f'Factory{i+2}') for i in range(4)]

    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        # Check Parking area. Current count save in prk_count.
        for prk_factory in range(4):
            prk_count[f'Factory{prk_factory+1}_0'] = traci.parkingarea.getVehicleCount(f'Factory{prk_factory+1}_0')
            prk_count[f'Factory{prk_factory+1}_1'] = traci.parkingarea.getVehicleCount(f'Factory{prk_factory+1}_1')
        tmp_state = [lorry[i].refresh_state() for i in range(8)]
        if lorry[0].state == 'free':
            lorry[0].delivery(parking_available=prk_count,desitination='Factory1', current_position=lorry[0].position)
        for tmp_factory in factory:
            tmp_factory.factory_step(lorry[0],prk_count)

    traci.close()
    sys.stdout.flush()

def get_options():
    optParser = optparse.OptionParser()
    optParser.add_option("--nogui", action="store_true",
                         default=False, help="run the commandline version of sumo")
    options, args = optParser.parse_args()
    return options


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


