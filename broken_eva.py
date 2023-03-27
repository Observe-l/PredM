import gym
from gym import spaces
from ray.rllib.env.multi_agent_env import MultiAgentEnv
from csv import writer
from pathlib import Path
import numpy as np
import traci
import sys
import optparse

from util.lorry_eva import Lorry
from util.factory import Factory
from util.product import product_management

class sumoEnv(MultiAgentEnv):
    '''
    sumo environment. state is the engine state (or sensor reading), action is repaired or not
    '''
    def __init__(self, env_config:dict):
        # 12 lorries
        self.config = env_config
        self.lorry_num =  self.config["truck"]
        self.path = f'/home/lwh/Documents/Code/PredM/result/' + self.config['algo'] +'_' + str(self.config["truck"])
        # get cpu num
        self.num_cpu = "20"
        # Select traffic density
        if self.config['map'] == 2:
            self.map_file = "map/3km_1week_10/osm.sumocfg"
        elif self.config['map'] == 3:
            self.map_file = "map/3km_1week_15/osm.sumocfg"
        elif self.config['map'] == 4:
            self.map_file = "map/3km_1week_20/osm.sumocfg"
        else:
            self.map_file = "map/3km_1week/osm.sumocfg"
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
            print('restart sumo')
        except:
            pass
        print(f"using {self.num_cpu} cpus")
        traci.start(["sumo", "-c", "/home/lwh/Documents/Code/PredM/"+self.map_file,"--threads",self.num_cpu,"--no-warnings","True"])
        # Create lorry
        self.lorry = [Lorry(lorry_id=f'lorry_{i}', path=self.path, capacity=0.5,
                    repair_freq=int(self.config['repair']*86400), env_step=self.mdp_step, maintenance_freq=self.config['maintain']*3600,mdp_freq = self.config['mdp']*3600) for i in range(self.lorry_num)]
#         self.lorry = [Lorry(lorry_id=f'lorry_{i}', path=self.path, capacity=0.5,
#                     time_broken=int(1*86400), env_step=self.mdp_step, mdp_freq=0.6*3600, maintenance_freq=0.4*3600) for i in range(self.lorry_num)]
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
            tmp_state = [tmp_lorry.refresh_state(time_step=current_time + (self.sumo_repeat-1)*86400*self.config['step_len'], repair_flag=False) for tmp_lorry in self.lorry]
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
        observation = {tmp_lorry.id:tmp_lorry.sensor[self.tmp_col].values.flatten() for tmp_lorry in self.lorry}
#         observation = self.lorry[0].sensor[self.tmp_col].values.flatten()

        self.done['__all__'] = False
        return observation
    
    def step(self, action_dict:dict):
        self.step_num += 1
        # lorry pool, only select normal lorry, i.e,. not 'broken'
        # action is a dictionary
        lorry_pool_id = [tmp_lorry.id for tmp_lorry in self.lorry if tmp_lorry.state != 'broken' and tmp_lorry.state != 'repair' and tmp_lorry.state != 'maintenance']
        for tmp_key in action_dict.keys():
            if action_dict[tmp_key] == 1 and tmp_key in lorry_pool_id:
                for i in range(len(self.lorry)):
                    if self.lorry[i].id == tmp_key:
                        self.lorry[i].maintenance_flag = True

        # get reward before step
        last_trans = {tmp_lorry.id:tmp_lorry.total_product for tmp_lorry in self.lorry}
        for _ in range(self.mdp_step):
            traci.simulationStep()
            current_time = traci.simulation.getTime()
            tmp_state = [tmp_lorry.refresh_state(time_step=current_time + (self.sumo_repeat-1)*86400*self.config['step_len'], repair_flag=False) for tmp_lorry in self.lorry]
            self.product.produce_load()
            self.product.lorry_manage()

        lorry_pool = [tmp_lorry for tmp_lorry in self.lorry if tmp_lorry.state != 'broken' and tmp_lorry.state != 'repair' and tmp_lorry.state != 'maintenance']
        
        # Read sensor reading. Only those normal lorries can be selected
        observation = {tmp_lorry.id:tmp_lorry.sensor[self.tmp_col].values.flatten() for tmp_lorry in self.lorry}
        # Get the reward
        current_trans = {tmp_lorry.id:tmp_lorry.total_product for tmp_lorry in self.lorry}
        reward = {}
        tmp_reward = 0
        self.cumulate_reward = 0
        for tmp_lorry in self.lorry:
            reward[tmp_lorry.id] = current_trans[tmp_lorry.id] - last_trans[tmp_lorry.id]
            tmp_reward += reward[tmp_lorry.id]
            self.cumulate_reward += current_trans[tmp_lorry.id]

        # Record the result
        with open(self.result_file,'a') as f:
            f_csv = writer(f)
            tmp_A = round(self.factory[2].product.loc['A','total'],3)
            tmp_B = round(self.factory[3].product.loc['B','total'],3)
            tmp_P12 = round(self.factory[1].product.loc['P12','total'],3)
            tmp_P23 = round(self.factory[2].product.loc['P23','total'],3)
            tmp_lorry = len([i for i in self.lorry if i.state != 'broken' and i.state != 'repair' and i.state != 'maintenance'])
            tmp_time = round(current_time / 3600 + (self.sumo_repeat-1)*self.config['step_len']*24,3)
            f_csv.writerow([tmp_time,tmp_A,tmp_B,tmp_P12,tmp_P23,tmp_lorry])
            
        with open(self.reward_file,'a') as f:
            f_csv =writer(f)
            tmp_time = round(current_time / 3600 + (self.sumo_repeat-1)*self.config['step_len']*24,3)
            f_csv.writerow([tmp_time, tmp_reward, self.cumulate_reward])
        # Terminate the episode after 1 week
        if current_time >= 86400*self.config['step_len']:
            self.done['__all__'] = True

        return observation, reward, self.done, {}
    
    def render(self):
        pass


def get_options():
    optParse = optparse.OptionParser()
    optParse.add_option("-n","--number",default=12,type=int,help="number of turcks")
    options, args = optParse.parse_args()
    return options


def main():
    options = get_options()

    env_config = {"algo":"broken_eva", "repair":3, "maintain":4, "mdp":6, "step_len":7, "truck":options.number, "map":1}
    eva_env = sumoEnv(env_config)
    eva_env.reset()
    # Default action: None
    tmp_action = {"all":0}
    obs, rew, done_flag, _ = eva_env.step(tmp_action)
    while done_flag['__all__'] == False:
        obs, rew, done_flag, _ = eva_env.step(tmp_action)

if __name__ == '__main__':
    main()