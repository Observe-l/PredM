import ray
from ray import tune, air
from ray.tune.registry import register_env
from ray.rllib.algorithms import dqn, ppo, sac

import optparse

from sumo_env import sumoEnv

def get_options():
    optParse = optparse.OptionParser()
    optParse.add_option("-a","--algorithm",default="PPO",type=str,help="PPO, DQN or SAC")
    options, args = optParse.parse_args()
    return options

if __name__ == '__main__':
    options = get_options()
    ray.init()

    if options.algorithm == "DQN":
        algo = dqn.DQN
        folder = "DQN"
    elif options.algorithm == "SAC":
        algo = sac.SAC
        folder = "SAC"
    else:
        algo = ppo.PPO
        folder = "PPO"

    stop = {'episodes_total':140}
    rllib_config = {"env":sumoEnv,
                    "env_config":{"algo":folder},
                    "framework":"torch",
                    "num_workers":2,
                    "multiagent":{
                        "policies":{"shared_policy"},
                        "policy_mapping_fn": (lambda agent_id, episode, **kwargs: "shared_policy"),
                    }
    }

    tunner = tune.Tuner(
        algo,
        param_space=rllib_config,
        run_config=air.RunConfig(
            stop=stop,
            checkpoint_config=air.CheckpointConfig(
                num_to_keep=5
            ),
        )
    )
    tunner.fit()
    ray.shutdown()