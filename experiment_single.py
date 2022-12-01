import ray
import os
from ray import tune, air
from ray.rllib.algorithms import dqn, ppo, sac
import optparse

# from sumo_env import sumoEnv
# from train_env import sumoEnv
from multiple_lorry import sumoEnv

def get_options():
    optParse = optparse.OptionParser()
    optParse.add_option("-a","--algorithm",default="PPO",type=str,help="PPO, DQN or SAC")
    options, args = optParse.parse_args()
    return options

if __name__ == '__main__':
    options = get_options()
    ray.init()
    rllib_config = {"env":sumoEnv,
                "env_config":{"algo":"init"},
                "framework":"tf2",
                "num_workers":1,
                "ignore_worker_failures":True,
                "recreate_failed_workers":True,
    }
    if options.algorithm == "DQN":
        agent=dqn.DQN(config=rllib_config)
        agent.restore('/home/lwh/ray_results/single_agent/DQN_2022-12-01_11-09-06/DQN_sumoEnv_83f85_00000_0_2022-12-01_11-09-06/checkpoint_000081')
        folder = "DQN_single"
    elif options.algorithm == "SAC":
        agent=sac.SAC(config=rllib_config)
        agent.restore('/home/lwh/ray_results/sumo_env/SAC_2022-11-28_00-04-22/SAC_sumoEnv_2838a_00000_0_2022-11-28_00-04-22/checkpoint_000639')
        folder = "SAC_single"
    else:
        agent=ppo.PPO(config=rllib_config)
        agent.restore('/home/lwh/ray_results/sumo_env/PPO_2022-11-27_23-30-57/PPO_sumoEnv_7d335_00000_0_2022-11-27_23-30-58/checkpoint_000019')
        folder = "PPO_single"



    env = sumoEnv({'algo':folder})
    # init the env
    obs = env.reset()
    reward = 0
    done_state = False

    while done_state == False:
        action = agent.compute_single_action(observation=obs)
        obs, reward, done_state, _ = env.step(action)
    ray.shutdown()