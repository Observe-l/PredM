import ray
import os
from ray import tune, air
from ray.tune.registry import register_env
from ray.rllib.algorithms import dqn, ppo, sac

import optparse

from sumo_env import sumoEnv

def get_options():
    optParse = optparse.OptionParser()
    optParse.add_option("-a","--algorithm",default="PPO",type=str,help="PPO, DQN or SAC")
    optParse.add_option("-w","--workers",default=4,type=int,help="number of workers")
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

    stop = {'episodes_total':500}
    rllib_config = {"env":sumoEnv,
                    "env_config":{"algo":folder,"num_workers":options.workers},
                    "framework":"torch",
                    "num_workers":options.workers,
                    "ignore_worker_failures":True,
                    "recreate_failed_workers":True,
                    "multiagent":{
                        "policies":{"shared_policy"},
                        "policy_mapping_fn": (lambda agent_id, episode, **kwargs: "shared_policy"),
                    }
    }

    ray_dir = os.path.expanduser('~') + "/4days"
    tunner = tune.Tuner(
        algo,
        param_space=rllib_config,
        run_config=air.RunConfig(
            local_dir=ray_dir,
            stop=stop,
            checkpoint_config=air.CheckpointConfig(
                checkpoint_frequency=10,
                checkpoint_at_end=True,
            ),
        )
    )
    tunner.fit()
    ray.shutdown()