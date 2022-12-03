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
                "disable_env_checking": True,
    }
    if options.algorithm == "DQN":
        agent=dqn.DQN(config=rllib_config)
        agent.restore('/hpctmp/e0724734/single_agent/DQN_2022-12-01_15-27-38/DQN_sumoEnv_a24ff_00000_0_2022-12-01_15-27-39/checkpoint_000220')
        folder = "DQN_single"
    elif options.algorithm == "SAC":
        agent=sac.SAC(config=rllib_config)
        agent.restore('/hpctmp/e0724734/single_agent/SAC_2022-12-01_17-36-10/SAC_sumoEnv_96ff5_00000_0_2022-12-01_17-36-11/checkpoint_000342')
        folder = "SAC_single"
    else:
        agent=ppo.PPO(config=rllib_config)
        agent.restore('/hpctmp/e0724734/single_agent/PPO_2022-12-01_21-30-18/PPO_sumoEnv_4bf78_00000_0_2022-12-01_21-30-18/checkpoint_000013')
        folder = "PPO_single"



    env = sumoEnv({'algo':folder})
    # init the env
    obs = env.reset()
    reward = 0
    done_state = False

    while done_state == False:
        action = {}
        for tmp_key in obs:
            action[tmp_key] = agent.compute_single_action(observation=obs[tmp_key])
        # action = agent.compute_single_action(observation=obs)
        obs, reward, done_state, _ = env.step(action)
    ray.shutdown()