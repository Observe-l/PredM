import ray
import os
from ray import tune, air
from ray.rllib.algorithms import ppo

import optparse
from single_lorry_eva import sumoEnv

def get_options():
    optParse = optparse.OptionParser()
    optParse.add_option("-r","--repair",default=3,type=int,help="repair mean (days)")
    optParse.add_option("-m","--maintain",default=4,type=int,help="maintain mean (hours)")
    options, args = optParse.parse_args()
    return options

if __name__ == '__main__':
    options = get_options()
    ray.init()
    rllib_config = {"env":sumoEnv,
                "env_config":{'algo':f'GTrXL_PPO-repair-{options.repair}days_maintain-{options.maintain}hours','repair':options.repair,'maintain':options.maintain},
                "framework":"tf2",
                "num_workers":1,
                "ignore_worker_failures":True,
                "recreate_failed_workers":True,
                "disable_env_checking": True,
                "model": {
                    "use_attention": True,
                    "max_seq_len": 20,
                    "attention_num_transformer_units": 1,
                    "attention_dim": 32,
                    "attention_memory_inference": 20,
                    "attention_memory_training": 20,
                    "attention_num_heads": 6,
                    "attention_head_dim": 32,
                    "attention_position_wise_mlp_dim": 32,
                },
    }
    agent=ppo.PPO(config=rllib_config)
    agent.restore('/home/lwh/ray_results/transformer/PPO_2022-12-04_20-48-38/PPO_sumoEnv_f940c_00000_0_2022-12-04_20-48-39/checkpoint_000040')
    result = agent.train()