import ray
import os
from ray import tune, air
from ray.rllib.algorithms import dqn, ppo, sac
import optparse

# from sumo_env import sumoEnv
# from train_env import sumoEnv
from single_lorry_eva import sumoEnv

def get_options():
    optParse = optparse.OptionParser()
    optParse.add_option("-r","--repair",default=3,type=int,help="repair mean (days)")
    optParse.add_option("-m","--maintain",default=4,type=int,help="maintain mean (hours)")
    options, args = optParse.parse_args()
    return options

if __name__ == '__main__':
    options = get_options()
    env = sumoEnv({'algo':f'repair-{options.repair}days_maintain-{options.maintain}hours','repair':options.repair,'maintain':options.maintain})
    # init the env
    obs = env.reset()
    reward = 0
    done_state = False

    while done_state == False:
        action = {}
        for tmp_key in obs:
            action[tmp_key] = 0
        # action = agent.compute_single_action(observation=obs)
        obs, reward, done_state, _ = env.step(action)