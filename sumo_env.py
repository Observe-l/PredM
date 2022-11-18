import gym
from gym import spaces
import numpy as np
import traci
import matlab.engine as engine

from util.lorry import Lorry
from util.factory import Factory
from util.product import product_management

class sumoEnv(gym.Env):
    '''
    sumo environment. state is the engine state (or sensor reading), action is repaired or not
    '''
    def __init__(self, env_config):
        # 12 lorries
        self.lorry_num = 12
        self.path = 'result/gym_12lorry__broken-3'
        self.result_file = self.path + '/lorry_record.csv'
        
        # There are 2 actions: repaired or not
        self.action_space = spaces.Tuple([spaces.Discrete(2) for _ in range(self.lorry_num)])
        # observation space, 9 sensor reading
        # observation_min = -10 * np.ones(9*self.lorry_num)
        # observation_max = 10 * np.ones(9*self.lorry_num)
        self.observation_space = spaces.Box(low=-10,high=10,shape=(self.lorry_num, 100, 9))
        # init matlab model
        self._init_matlab()
        # init sumo
        

    def _init_matlab(self):
        # Connect to matlab & simulink model
        self.mdl = 'transmission_fault_detection'
        self.eng = engine.connect_matlab()
        try:
            stop_time = self.eng.evalin('base', 'Tend')
            print('Connect to current MATLAB session')
        except:
            print('No running session, create new MATLAB session')
            print('Starting Simulink')
            self.eng.open_system(self.mdl,nargout=0)
            stop_time = self.eng.evalin('base', 'Tend')
        # Enable faster start and compiler the model
        print('Compiling the model')
        self.eng.set_param(self.mdl,'FastRestart','on',nargout=0)
        out = self.eng.sim(self.mdl)

        # Initial the model
        clutch = -1*np.ones(6,dtype=np.int64)
        self.eng.set_param(self.mdl+'/[A B C D E F]','Value',np.array2string(clutch),nargout=0)
        init_clutch = self.eng.get_param(self.mdl + '/[A B C D E F]', 'Value')
    
    def _init_sumo(self):
        # Close existing traci connection
        try:
            traci.close()
        except:
            pass
        traci.start(["sumo", "-c", "map/3km_1week/osm.sumocfg","--threads","8"])
        # Create lorry
        self.lorry = [Lorry(lorry_id=f'lorry_{i}', eng=self.eng, mdl=self.mdl, path=self.path, capacity=0.5,
                    time_broken=int(3*86400), labmda1=1/(6*1)) for i in range(self.lorry_num)]
        # Create factory
        self.factory = [Factory(factory_id='Factory0', produce_rate=[['P1',0.05,None,None]]),
                Factory(factory_id='Factory1', produce_rate=[['P2',0.1,None,None],['P12',0.025,'P1,P2','1,1']]),
                Factory(factory_id='Factory2', produce_rate=[['P3',0.05,None,None],['P23',0.025,'P2,P3','1,1'],['A',0.025,'P12,P3','1,1']]),
                Factory(factory_id='Factory3', produce_rate=[['P4',0.05,None,None],['B',0.025,'P23,P4','1,1']])
                ]
        # The lorry and factory mamanent
        self.product = product_management(self.factory,self.lorry)

    def reset(self):
        '''
        reset the sumo map after 24 hours.
        '''
        self._init_sumo()
        self.done = False
        self.observation = np.zeros((self.lorry_num, 100, 9))
        return self.observation
    
    def step(self, action):
        traci.simulationStep()
        tmp_state = [self.lorry[i].refresh_state() for i in range(self.lorry_num)]


