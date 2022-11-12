import sys
import optparse
from csv import writer

import matlab.engine as engine

import os
import numpy as np
import pandas as pd

import multiprocessing
import threading
from util.lorry import Lorry
from util.factory import Factory
from util.product import product_management


# we need to import python modules from the $SUMO_HOME/tools directory
if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("please declare environment variable 'SUMO_HOME'")

from sumolib import checkBinary
import traci

def run(eng,mdl:str,repair_flag:bool):
    # Generate 8 lorries
    lorry_num = 4
    lorry = [Lorry(lorry_id=f'lorry_{i}', eng=eng, mdl=mdl) for i in range(lorry_num)]
    # Gendrate 4 Factories
    factory = [Factory(factory_id='Factory0', produce_rate=[['P1',0.05,None,None]]),
               Factory(factory_id='Factory1', produce_rate=[['P2',0.1,None,None],['P12',0.025,'P1,P2','1,1']]),
               Factory(factory_id='Factory2', produce_rate=[['P3',0.05,None,None],['P23',0.025,'P2,P3','1,1'],['A',0.025,'P12,P3','1,1']]),
               Factory(factory_id='Factory3', produce_rate=[['P4',0.05,None,None],['B',0.025,'P23,P4','1,1']])
              ]
    product = product_management(factory,lorry)
    '''
    execute the TraCI control loop
    run 86400 seconds (24 hours)
    '''
    result_file = 'result.csv'
    with open(result_file,'w') as f:
        f_csv = writer(f)
        f_csv.writerow(['time','A','B','P12','P23','current_lorry'])
    with open('lorry_record.csv','w') as f:
        f_csv = writer(f)
        f_csv.writerow(['time','lorry id','MDP','state'])

    for time_step in range(86400*7):
        traci.simulationStep()

        tmp_state = [lorry[i].refresh_state(time_step,repair_flag) for i in range(lorry_num)]

        # Produce product and develievery
        product.produce_load()
        product.lorry_manage()
        # record every 1 min
        if time_step % 60 == 0:
            with open(result_file,'a') as f:
                f_csv = writer(f)
                tmp_A = round(factory[2].product.loc['A','total'],3)
                tmp_B = round(factory[3].product.loc['B','total'],3)
                tmp_P12 = round(factory[1].product.loc['P12','total'],3)
                tmp_P23 = round(factory[2].product.loc['P23','total'],3)
                tmp_lorry = len([i for i in lorry if i.state != 'broken' and i.state != 'repair'])
                tmp_time = round((time_step / 3600),3)
                f_csv.writerow([tmp_time,tmp_A,tmp_B,tmp_P12,tmp_P23,tmp_lorry])
                # f.write(f'{tmp_time}\t{tmp_A}\t{tmp_B}\t{tmp_P12}\t{tmp_P23}\n')

            # print every 5 min
            if time_step % 300 == 0:
                print('s is:\n',product.s)
                print('s1 is:\n',product.s1)
                print('s2 is:\n',product.s2)
                print(f'current time: {time_step}')
            # if time_step > 2000:
            #     print(factory[1].container)

    traci.close()
    # sys.stdout.flush()

def get_options():
    optParser = optparse.OptionParser()
    optParser.add_option("--nogui", action="store_true",
                         default=False, help="run the commandline version of sumo")
    optParser.add_option("--repair", action="store_true",
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
    if options.repair:
        repair_flag = True
        print('repair engine every day')
    else:
        repair_flag = False
        print('baseline')
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
    traci.start([sumoBinary, "-c", "map/3km_1week/osm.sumocfg","--threads","6"])
    # Connect to redpc
    # traci.init(port=45687,host='redpc')

    # Reload sumo map
    # traci.load(["-c", "map/SG_south_24h/osm.sumocfg","--threads","8"])
    
    run(eng,mdl,repair_flag)
    eng.quit()


