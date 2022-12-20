import ray
import os
from ray import tune, air
from ray.rllib.algorithms.ppo import PPO
from ray.rllib.policy.policy import PolicySpec
import optparse
import numpy as np
import time
from multi_lorry_LSTM import sumoEnv

ray.init()

stop = {'episodes_total':200}
config = {
        "env": sumoEnv,
        "env_config": {"algo":"train_LSTM_PPO",'repair':3,'maintain':4,'mdp':6,'step_len':7,'map':1},
        "disable_env_checking":True,
        "num_workers": 20,
        "num_cpus_per_worker": 1,
        "ignore_worker_failures":True,
        "recreate_failed_workers":True,
        "model": {
            "use_lstm": True,
            "lstm_cell_size": 256,
            "vf_share_layers": True
        },
        "multiagent":{
            "policies":{"shared_policy"},
            "policy_mapping_fn": (lambda agent_id, episode, **kwargs: "shared_policy"),
        },
        "framework": "torch",
}
ray_dir = "/hpctmp/ecelwh/PredM/Trained_Agents"
exp_name = "PPO_LSTM"

tunner = tune.Tuner(
    PPO,
    param_space=config,
    run_config=air.RunConfig(
        local_dir=ray_dir,
        name = exp_name,
        stop=stop,
        checkpoint_config=air.CheckpointConfig(
            checkpoint_frequency=1,
            num_to_keep=3,
            checkpoint_score_attribute='episode_reward_mean',
            checkpoint_at_end=True,
        ),
    )
)
result=tunner.fit()
best_checkpoint = result.get_best_result(metric='episode_reward_mean',mode='max',scope='avg').log_dir
print(best_checkpoint)
with open('PPO_LSTM_best_checkpoint.txt','w') as f:
    f.write(str(best_checkpoint))