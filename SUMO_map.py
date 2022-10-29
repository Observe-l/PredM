import sys
import optparse
import matlab.engine as engine

import os
import numpy as np
import pandas as pd

import multiprocessing
import threading
from util.lorry_manage import Lorry
from util.factory_manage import Factory

PARK_CAPACITY = 4

# we need to import python modules from the $SUMO_HOME/tools directory
if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("please declare environment variable 'SUMO_HOME'")

from sumolib import checkBinary
import traci




def run(eng,mdl:str):
    prk_count = {'Factory0': 0,'Factory1': 0,
                 'Factory2': 0,'Factory3': 0}
    # Generate 8 lorries
    lorry = [Lorry(lorry_id=f'lorry_{i}', eng=eng, mdl=mdl) for i in range(8)]
    # Gendrate 4 Factories
    factory = [Factory(factory_id=f'Factory{i}', next_factory=f'Factory{i+1}') for i in range(4)]
    '''
    execute the TraCI control loop
    run 86400 seconds (24 hours)
    '''
    for _ in range(86400):
        traci.simulationStep()
        # Check Parking area. Current count save in prk_count.
        for prk_factory in range(4):
            prk_count[f'Factory{prk_factory}'] = traci.parkingarea.getVehicleCount(f'Factory{prk_factory}')
        tmp_state = [lorry[i].refresh_state() for i in range(8)]

        # Produce product and develievery
        for tmp_factory in factory:
            tmp_factory.factory_step(lorry[0],prk_count)

    traci.close()
    # sys.stdout.flush()

def get_options():
    optParser = optparse.OptionParser()
    optParser.add_option("--nogui", action="store_true",
                         default=False, help="run the commandline version of sumo")
    optParser.add_option("--share_engine", action="store_true",
                         default=False, help="connect to matlab engine")
    options, args = optParser.parse_args()
    return options


if __name__ == "__main__":
    options = get_options()
    
    # this script has been called from the command line. It will start sumo as a
    # server, then connect and run
    mdl = 'transmission_fault_detection'
    if options.nogui:
        sumoBinary = checkBinary('sumo')
    else:
        sumoBinary = checkBinary('sumo-gui')

    eng = engine.connect_matlab()
    try:
        stop_time = eng.evalin('base', 'Tend')
        print('Connect to current MATLAB session')
    except:
        print('No running session, create new MATLAB session')
        print('Starting Simulink')
        eng.open_system(mdl,nargout=0)
        stop_time = eng.evalin('base', 'Tend')
            

    # Enable faster start and compiler the model
    print('Compiling the model')
    eng.set_param(mdl,'FastRestart','on',nargout=0)
    out = eng.sim(mdl)

    # Initial the model
    clutch = -1*np.ones(6,dtype=np.int64)
    eng.set_param(mdl+'/[A B C D E F]','Value',np.array2string(clutch),nargout=0)
    init_clutch = eng.get_param(mdl + '/[A B C D E F]', 'Value')
    traci.start([sumoBinary, "-c", "map/SG_south_24h/osm.sumocfg","--threads","8"])
    # Connect to redpc
    # traci.init(port=45687,host='redpc')

    # Reload sumo map
    # traci.load(["-c", "map/SG_south_24h/osm.sumocfg","--threads","8"])
    
    run(eng,mdl)
    eng.quit()


