import gym
from gym import spaces
from csv import writer
from pathlib import Path
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
        # Create folder
        Path(self.path).mkdir(parents=True, exist_ok=True)
        self.lorry_file = self.path + '/lorry_record.csv'
        self.result_file = self.path + '/result.csv'
        
        # There are 2 actions: repaired or not
        self.action_space = spaces.Tuple([spaces.Discrete(2) for _ in range(self.lorry_num)])
        # mdp step, 10 min, unit is second
        self.mdp_step = 600
        # sumo step 86400*7
        self.sumo_step = 0
        # sumo repeating times
        self.sumo_repeat = 0
        # observation space, 9 sensor reading
        self.observation_space = spaces.Box(low=-10,high=10,shape=(self.lorry_num, 100, 9))
        # init matlab model
        self.init_matlab()
        # init record
        with open(self.result_file,'w') as f:
            f_csv = writer(f)
            f_csv.writerow(['time','A','B','P12','P23','current_lorry'])
        with open(self.lorry_file,'w') as f:
            f_csv = writer(f)
            f_csv.writerow(['time','lorry id','MDP','state'])
        

    def init_matlab(self):
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
    
    def init_sumo(self):
        # Close existing traci connection
        try:
            traci.close()
        except:
            pass
        traci.start(["sumo", "-c", "map/3km_1week/osm.sumocfg","--threads","8"])
        # Create lorry
        self.lorry = [Lorry(lorry_id=f'lorry_{i}', eng=self.eng, mdl=self.mdl, path=self.path, capacity=0.5,
                    time_broken=int(3*86400), env_step=self.mdp_step) for i in range(self.lorry_num)]
        # Create factory
        self.factory = [Factory(factory_id='Factory0', produce_rate=[['P1',0.05,None,None]]),
                Factory(factory_id='Factory1', produce_rate=[['P2',1,None,None],['P12',0.25,'P1,P2','1,1']]),
                Factory(factory_id='Factory2', produce_rate=[['P3',0.5,None,None],['P23',0.25,'P2,P3','1,1'],['A',0.25,'P12,P3','1,1']]),
                Factory(factory_id='Factory3', produce_rate=[['P4',0.5,None,None],['B',0.25,'P23,P4','1,1']])
                ]
        # The lorry and factory mamanent
        self.product = product_management(self.factory, self.lorry)
        # lorry pool, only select normal lorry, i.e,. not 'broken'
        self.lorry_pool = [tmp_lorry for tmp_lorry in self.lorry if tmp_lorry.state != 'broken' and tmp_lorry.state != 'repair' and tmp_lorry.state != 'maintenance']

    def reset(self):
        '''
        reset the sumo map after 24 hours.
        '''
        self.sumo_repeat += 1
        self.init_sumo()
        self.done = False
        self.sumo_step = 0
        self.step_num = 1
        for _ in range(3600):
            traci.simulationStep()
            self.sumo_step += 1
            current_time = traci.simulation.getTime()
            tmp_state = [tmp_lorry.refresh_state(time_step=current_time + (self.sumo_repeat-1)*86400*7, repair_flag=False) for tmp_lorry in self.lorry]
            self.product.produce_load()
            self.product.lorry_manage()
        # lorry pool, only select normal lorry, i.e,. not 'broken'
        self.lorry_pool = [tmp_lorry for tmp_lorry in self.lorry if tmp_lorry.state != 'broken' and tmp_lorry.state != 'repair' and tmp_lorry.state != 'maintenance']
        # update the action space and observation space
        self.action_space = spaces.Tuple([spaces.Discrete(2) for _ in range(len(self.lorry_pool))])
        self.observation_space = spaces.Box(low=-10,high=10,shape=(len(self.lorry_pool), 100, 9))
    
        # Get column name
        self.tmp_col = self.lorry[0].sensor.columns[0:9]
        # Read sensor reading
        observation = np.array([tmp_lorry.sensor[self.tmp_col].values for tmp_lorry in self.lorry_pool])
        # print(observation)
        # update transported product
        current_time = traci.simulation.getTime()
        # Calculate the reward
        last_trans = np.sum([tmp_lorry.product_record.loc[current_time - 3600,'total_product'] for tmp_lorry in self.lorry])
        current_trans = np.sum([tmp_lorry.product_record.loc[current_time,'total_product'] for tmp_lorry in self.lorry])
        reward = current_trans - last_trans
        return observation
    
    def step(self, action):
        # action is a tuple. 0 
        for tmp_idx in np.where(np.array(action))[0]:
            self.lorry_pool[tmp_idx].maintenance_flag = True
        for _ in range(self.mdp_step):
            traci.simulationStep()
            self.sumo_step += 1
            current_time = traci.simulation.getTime()
            tmp_state = [tmp_lorry.refresh_state(time_step=current_time + (self.sumo_repeat-1)*86400*7, repair_flag=False) for tmp_lorry in self.lorry]
            self.product.produce_load()
            self.product.lorry_manage()
        # lorry pool, only select normal lorry, i.e,. not 'broken'
        self.lorry_pool = [tmp_lorry for tmp_lorry in self.lorry if tmp_lorry.state != 'broken' and tmp_lorry.state != 'repair' and tmp_lorry.state != 'maintenance']
        # update the action space and observation space
        self.action_space = spaces.Tuple([spaces.Discrete(2) for _ in range(len(self.lorry_pool))])
        self.observation_space = spaces.Box(low=-10,high=10,shape=(len(self.lorry_pool), 100, 9))

        # Read sensor reading
        observation = np.array([tmp_lorry.sensor[self.tmp_col].values for tmp_lorry in self.lorry_pool])
        # Get the reward, 1 hour
        last_trans = np.sum([tmp_lorry.product_record.loc[current_time - 3600,'total_product'] for tmp_lorry in self.lorry])
        current_trans = np.sum([tmp_lorry.product_record.loc[current_time,'total_product'] for tmp_lorry in self.lorry])
        reward = current_trans - last_trans

        # Record the result
        with open(self.result_file,'a') as f:
            f_csv = writer(f)
            tmp_A = round(self.factory[2].product.loc['A','total'],3)
            tmp_B = round(self.factory[3].product.loc['B','total'],3)
            tmp_P12 = round(self.factory[1].product.loc['P12','total'],3)
            tmp_P23 = round(self.factory[2].product.loc['P23','total'],3)
            tmp_lorry = len([i for i in self.lorry if i.state != 'broken' and i.state != 'repair' and i.state != 'maintenance'])
            tmp_time = round((self.sumo_step / 3600)+(self.sumo_repeat-1)*7*24,3)
            f_csv.writerow([tmp_time,tmp_A,tmp_B,tmp_P12,tmp_P23,tmp_lorry])

        if self.sumo_step >= 86400*7:
            self.done = True
        
        return observation, reward, self.done, {}
    
    def render(self):
        pass
