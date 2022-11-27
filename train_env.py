import gym
from gym import spaces
from ray.rllib.env.multi_agent_env import MultiAgentEnv
from ray.rllib.env.env_context import EnvContext
from csv import writer
from pathlib import Path
import numpy as np
import traci

from util.lorry import Lorry
from util.factory import Factory
from util.product import product_management

class sumoEnv(MultiAgentEnv):
    '''
    sumo environment. state is the engine state (or sensor reading), action is repaired or not
    '''
    def __init__(self, env_config:EnvContext):
        # 12 lorries
        self.lorry_num = 12
        self.path = f'result/RL-' + env_config['algo'] + f'-worker{env_config.worker_index}'
        # get cpu num
        self.num_cpu = str(env_config['num_workers'])
        # Create folder
        Path(self.path).mkdir(parents=True, exist_ok=True)
        self.lorry_file = self.path + '/lorry_record.csv'
        self.result_file = self.path + '/result.csv'
        self.reward_file = self.path + 'reward.csv'
        
        # There are 2 actions: repaired or not
        # self.action_space = spaces.Tuple([spaces.Discrete(2) for _ in range(self.lorry_num)])
        self.action_space = spaces.Discrete(2)
        # mdp step, 1 min, unit is second
        self.mdp_step = 300
        # sumo step 86400*7
        # sumo repeating times
        self.sumo_repeat = 0
        # observation space, 9 sensor reading
        # self.observation_space = spaces.Box(low=-10,high=10,shape=(self.lorry_num, 100, 9))
        self.observation_space = spaces.Box(low=-10,high=10,shape=(100,9))
        # init sumo
        self.done = {}

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
        except:
            pass
        print(f"using {self.num_cpu} cpus")
        traci.start(["sumo", "-c", "map/3km_1week/osm.sumocfg","--threads",self.num_cpu])
        # Create lorry
        self.lorry = [Lorry(lorry_id=f'lorry_{i}', path=self.path, capacity=0.5,
                    time_broken=int(3*86400), env_step=self.mdp_step, mdp_freq=0.6*3600, maintenance_freq=0.4*3600) for i in range(self.lorry_num)]
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
        print(f'episode:{self.episode_count}, \'done flag:\'{self.done}')
        self.episode_count += 1

        # init sumo
        self.sumo_repeat += 1
        self.init_sumo()
            
        # lorry pool, only select normal lorry, i.e,. not 'broken'
        self.lorry_pool = [tmp_lorry for tmp_lorry in self.lorry if tmp_lorry.state != 'broken' and tmp_lorry.state != 'repair' and tmp_lorry.state != 'maintenance']
    
        # Get column name
        self.tmp_col = self.lorry[0].sensor.columns[0:9]
        # Read sensor reading, obs is a dictionary, key is the lorry id
        # observation = np.array([tmp_lorry.sensor[self.tmp_col].values for tmp_lorry in self.lorry])
        observation = {tmp_lorry.id:tmp_lorry.sensor[self.tmp_col].values for tmp_lorry in self.lorry_pool}
        self.done['__all__'] = False
        for tmp_lorry in self.lorry:
            self.done[tmp_lorry.id] = False
            print(f'dong state is: {self.done}')
        return observation
    
    def step(self, action_dict:dict):
        print(f'new step, action: {action_dict}')
        self.step_num += 1
        # lorry pool, only select normal lorry, i.e,. not 'broken'
        # action is a dictionary
        for tmp_key in action_dict.keys():
            if action_dict[tmp_key] == 1:
                self.lorry[int(tmp_key[-1])].maintenance_flag = True

        # get reward before step
        last_trans = {tmp_lorry.id:tmp_lorry.total_product for tmp_lorry in self.lorry}
        for _ in range(self.mdp_step):
            traci.simulationStep()
            current_time = traci.simulation.getTime()
            tmp_state = [tmp_lorry.refresh_state(time_step=current_time + (self.sumo_repeat-1)*86400/2, repair_flag=False) for tmp_lorry in self.lorry]
            self.product.produce_load()
            self.product.lorry_manage()
            # Terminate episode after all lorry are broken
            for tmp_lorry in self.lorry:
                if tmp_lorry.state == 'broken':
                    self.done[tmp_lorry.id] = True
                    self.done['__all__'] = all(self.done[tmp_idx]==True for tmp_idx in self.done if tmp_idx != '__all__')
                    print(f'dong state is: {self.done}')
            if self.done['__all__']:
                break
        
        lorry_dic = [tmp_idx for tmp_idx in self.done if self.done[tmp_idx] == False]
        # Only those normal lorry can be selected
        self.lorry_pool = [tmp_lorry for tmp_lorry in self.lorry if tmp_lorry.id in lorry_dic and tmp_lorry.state != 'broken' and tmp_lorry.state != 'repair' and tmp_lorry.state != 'maintenance']
        
        # Read sensor reading. Only those normal lorries can be selected
        observation = {tmp_lorry.id:tmp_lorry.sensor[self.tmp_col].values for tmp_lorry in self.lorry_pool}
        # Get the reward, 1 hour
        reward = {}
        current_trans = {tmp_lorry.id:tmp_lorry.total_product for tmp_lorry in self.lorry}
        tmp_reward = 0
        tmp_cumulate = 0
        for tmp_lorry in self.lorry:
            reward[tmp_lorry.id] = current_trans[tmp_lorry.id] - last_trans[tmp_lorry.id]
            # After lorry broken remove it from gym env
            if tmp_lorry.id in lorry_dic:
                reward[tmp_lorry.id] = 0
            tmp_reward += reward[tmp_lorry.id]
            tmp_cumulate += current_trans[tmp_lorry.id]

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
            tmp_step = self.step_num
            f_csv.writerow([tmp_step, tmp_reward, tmp_cumulate])
        # Terminate the episode after 1 week
        if current_time >= 86400/2:
            self.done['__all__'] = True
        
        return observation, reward, self.done, {}
    
    def render(self):
        pass
