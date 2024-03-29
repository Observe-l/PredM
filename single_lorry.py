import gym
from gym import spaces
from ray.rllib.env.env_context import EnvContext
from csv import writer
from pathlib import Path
import numpy as np
import traci

from util.lorry import Lorry
from util.factory import Factory
from util.product import product_management

class sumoEnv(gym.Env):
    '''
    sumo environment. state is the engine state (or sensor reading), action is repaired or not
    '''
    def __init__(self, env_config:EnvContext):
        # 12 lorries
        self.lorry_num = 12
        self.path = f'result/RL-' + env_config['algo']
        # get cpu num
        self.num_cpu = "8"
        # Create folder
        Path(self.path).mkdir(parents=True, exist_ok=True)
        self.lorry_file = self.path + '/lorry_record.csv'
        self.result_file = self.path + '/result.csv'
        self.reward_file = self.path + '/reward.csv'
        
        # There are 2 actions: repaired or not, convert decimal to binary
        # self.action_space = spaces.Tuple([spaces.Discrete(2) for _ in range(self.lorry_num)])
        self.action_space = spaces.Discrete(2)
        # mdp step, 5 min, unit is second
        self.mdp_step = 300
        # sumo step 86400*7
        # sumo repeating times
        self.sumo_repeat = 0
        # observation space, 9 sensor reading
        self.observation_space = spaces.Box(low=-2,high=2,shape=(9,))
        self.done = False

        self.episode_count = 0
        self.step_num = 0
        # init record
        with open(self.result_file,'w') as f:
            f_csv = writer(f)
            f_csv.writerow(['time','A','B','P12','P23','current_lorry'])
        with open(self.lorry_file,'w') as f:
            f_csv = writer(f)
            f_csv.writerow(['time','lorry id','MDP','state'])
        with open(self.reward_file,'w') as f:
            f_csv = writer(f)
            f_csv.writerow(['step','reward','cumulate reward'])
        
    def init_sumo(self):
        # Close existing traci connection
        try:
            traci.close()
            print('restart sumo')
        except:
            pass
        print(f"using {self.num_cpu} cpus")
        traci.start(["sumo", "-c", "map/3km_1week/osm.sumocfg","--threads",self.num_cpu])
        # Create lorry
        self.lorry = [Lorry(lorry_id=f'lorry_{i}', path=self.path, capacity=0.5,
                    time_broken=int(3*86400), env_step=self.mdp_step) for i in range(self.lorry_num)]
        # self.lorry = [Lorry(lorry_id=f'lorry_{i}', path=self.path, capacity=0.5,
        #             time_broken=int(1*86400), env_step=self.mdp_step, mdp_freq=0.6*3600, maintenance_freq=0.4*3600) for i in range(self.lorry_num)]
        # Create factory
        self.factory = [Factory(factory_id='Factory0', produce_rate=[['P1',5,None,None]]),
                Factory(factory_id='Factory1', produce_rate=[['P2',10,None,None],['P12',2.5,'P1,P2','1,1']]),
                Factory(factory_id='Factory2', produce_rate=[['P3',5,None,None],['P23',2.5,'P2,P3','1,1'],['A',2.5,'P12,P3','1,1']]),
                Factory(factory_id='Factory3', produce_rate=[['P4',5,None,None],['B',2.5,'P23,P4','1,1']])
                ]
        # The lorry and factory mamanent
        self.product = product_management(self.factory, self.lorry)

        for _ in range(self.mdp_step*2):
            traci.simulationStep()
            current_time = traci.simulation.getTime()
            tmp_state = [tmp_lorry.refresh_state(time_step=current_time + (self.sumo_repeat-1)*86400/2, repair_flag=False) for tmp_lorry in self.lorry]
            self.product.produce_load()
            self.product.lorry_manage()

    def reset(self):
        # Reset episode
        print(f'episode:{self.episode_count}')
        self.episode_count += 1
        self.cumulate_reward = 0
        # init sumo
        self.sumo_repeat += 1
        self.init_sumo()
            
        # lorry pool, only select normal lorry, i.e,. not 'broken'
        lorry_pool = [tmp_lorry for tmp_lorry in self.lorry if tmp_lorry.state != 'broken' and tmp_lorry.state != 'repair' and tmp_lorry.state != 'maintenance']
    
        # Get column name
        self.tmp_col = self.lorry[0].sensor.columns[0:9]
        # Read sensor reading, obs is a dictionary, key is the lorry id
        # observation = np.array([tmp_lorry.sensor[self.tmp_col].values for tmp_lorry in self.lorry])
        # observation = {tmp_lorry.id:tmp_lorry.sensor[self.tmp_col].values for tmp_lorry in self.lorry_pool}
        observation = self.lorry[0].sensor[self.tmp_col].values.flatten()

        self.done = False
        return observation
    
    def step(self, action):
        self.step_num += 1
        # lorry pool, only select normal lorry, i.e,. not 'broken'
        # action is a dictionary
        lorry_pool = [tmp_lorry for tmp_lorry in self.lorry if tmp_lorry.state != 'broken' and tmp_lorry.state != 'repair' and tmp_lorry.state != 'maintenance']

        if action == 1 and self.lorry[0] in lorry_pool:
            self.lorry[0].maintenance_flag = True

        # get reward before step
        last_trans = np.array(self.lorry[0].total_product)
        for _ in range(self.mdp_step):
            traci.simulationStep()
            current_time = traci.simulation.getTime()
            tmp_state = [tmp_lorry.refresh_state(time_step=current_time + (self.sumo_repeat-1)*86400/2, repair_flag=False) for tmp_lorry in self.lorry]
            self.product.produce_load()
            self.product.lorry_manage()

        lorry_pool = [tmp_lorry for tmp_lorry in self.lorry if tmp_lorry.state != 'broken' and tmp_lorry.state != 'repair' and tmp_lorry.state != 'maintenance']
        
        # Read sensor reading. Only those normal lorries can be selected
        observation = self.lorry[0].sensor[self.tmp_col].values.flatten()
        # Get the reward
        current_trans = np.array(self.lorry[0].total_product)
        reward = current_trans - last_trans
        self.cumulate_reward += reward

        # Record the result
        with open(self.result_file,'a') as f:
            f_csv = writer(f)
            tmp_A = round(self.factory[2].product.loc['A','total'],3)
            tmp_B = round(self.factory[3].product.loc['B','total'],3)
            tmp_P12 = round(self.factory[1].product.loc['P12','total'],3)
            tmp_P23 = round(self.factory[2].product.loc['P23','total'],3)
            tmp_lorry = len([i for i in self.lorry if i.state != 'broken' and i.state != 'repair' and i.state != 'maintenance'])
            tmp_time = round(current_time / 3600 + (self.sumo_repeat-1)*7*24,3)
            f_csv.writerow([tmp_time,tmp_A,tmp_B,tmp_P12,tmp_P23,tmp_lorry])
            
        with open(self.reward_file,'a') as f:
            f_csv =writer(f)
            tmp_time = round(current_time / 3600 + (self.sumo_repeat-1)*7*24,3)
            f_csv.writerow([tmp_time, reward, self.cumulate_reward])
        # Terminate the episode after 1 week
        if current_time >= 86400/2:
            self.done = True
        
        return observation, reward, self.done, {}
    
    def render(self):
        pass
