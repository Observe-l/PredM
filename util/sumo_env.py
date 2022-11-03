import gym
from gym import spaces
import numpy as np
import traci
import matlab.engine as engine

from .lorry import Lorry
from .factory import Factory

class sumoEnv(gym.Env):
    '''
    sumo environment. state is the engine state (or sensor reading), action is repaired or not
    '''
    def __init__(self, env_config):
        # There are 2 actions for every engines: repaired or not
        self.action_space = spaces.Discrete(2)
        # observation space, 5 sensor reading
        observation_min = -1000 * np.ones(5)
        observation_max = 1000 * np.ones(5)
        self.observation_space = spaces.Box(low=observation_min,high=observation_max)
        # init matlab model
        self._init_matlab()
        # Create Factory
        self.factory = [Factory(factory_id=f'Factory{i}', next_factory=f'Factory{i+1}') for i in range(4)]
        self.prk_count = {'Factory0': 0,'Factory1': 0,
                          'Factory2': 0,'Factory3': 0}
        

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

    def reset(self):
        '''
        reset the sumo map after 24 hours.
        '''
        traci.start(["sumo-gui", "-c", "map/SG_south_24h/osm.sumocfg","--threads","8"])
        self.lorry = [Lorry(lorry_id=f'lorry_{i}', eng=self.eng, mdl=self.mdl) for i in range(8)]

        self.done = False
        obs = np.zeros(5)
        return obs
    
    def step(self, action):
        traci.simulationStep()
        for prk_factory in range(4):
            self.prk_count[f'Factory{prk_factory}'] = traci.parkingarea.getVehicleCount(f'Factory{prk_factory}')
        tmp_state = [self.lorry[i].refresh_state() for i in range(8)]

        for tmp_factory in self.factory:
            tmp_factory.factory_step(self.lorry[0],self.prk_count)


        

