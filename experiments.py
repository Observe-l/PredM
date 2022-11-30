import ray
import os
from ray import tune, air
from ray.rllib.algorithms import dqn, ppo, sac
import optparse

from sumo_env import sumoEnv
# from train_env import sumoEnv

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
                "framework":"torch",
                "num_workers":1,
                "ignore_worker_failures":True,
                "recreate_failed_workers":True,
                "multiagent":{
                    "policies":{"shared_policy"},
                    "policy_mapping_fn": (lambda agent_id, episode, **kwargs: "shared_policy"),
                }
    }
    if options.algorithm == "DQN":
        agent=dqn.DQN(config=rllib_config)
        agent.restore('/home/lwh/ray_results/sumo_env/DQN_2022-11-27_23-30-33/DQN_sumoEnv_6f13c_00000_0_2022-11-27_23-30-34/checkpoint_000068')
        folder = "DQN"
    elif options.algorithm == "SAC":
        agent=sac.SAC(config=rllib_config)
        agent.restore('/home/lwh/ray_results/sumo_env/SAC_2022-11-28_00-04-22/SAC_sumoEnv_2838a_00000_0_2022-11-28_00-04-22/checkpoint_000639')
        folder = "SAC"
    else:
        agent=ppo.PPO(config=rllib_config)
        agent.restore('/home/lwh/ray_results/sumo_env/PPO_2022-11-27_23-30-57/PPO_sumoEnv_7d335_00000_0_2022-11-27_23-30-58/checkpoint_000019')
        folder = "PPO"



    env = sumoEnv({'algo':folder})
    # init the env
    obs = env.reset()
    reward = 0
    done_state = {'__all__': False}
    obs.keys()

    while done_state['__all__'] == False:
        action = {}
        for tmp_key in obs:
            action[tmp_key] = agent.compute_single_action(observation=obs[tmp_key],policy_id='shared_policy')
        obs, reward, done_state, _ = env.step(action)
    ray.shutdown()