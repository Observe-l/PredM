import ray
import os
from ray import tune, air
from ray.tune.registry import register_env
from ray.rllib.algorithms import dqn, ppo, sac

import optparse

from sumo_env import sumoEnv
# from train_env import sumoEnv

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

    stop = {'episodes_total':200}
    rllib_config = {"env":sumoEnv,
                    "env_config":{"algo":folder},
                    "framework":"tf2",
                    "num_workers":options.workers,
                    "ignore_worker_failures":True,
                    "recreate_failed_workers":True,
    }

    ray_dir = os.path.expanduser('~') + "/7days"

    # ray_dir = "/hpctmp/ecelwh/single_agent"
    tunner = tune.Tuner(
        algo,
        param_space=rllib_config,
        run_config=air.RunConfig(
            local_dir=ray_dir,
            stop=stop,
            checkpoint_config=air.CheckpointConfig(
                checkpoint_frequency=1,
                num_to_keep=100,
                checkpoint_at_end=True,
                checkpoint_score_attribute='reward',
            ),
        )
    )
    result = tunner.fit()
    ray.shutdown()