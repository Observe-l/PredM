import ray
from ray import tune, air
from ray.rllib.algorithms import dqn, ppo, sac
# from ray.rllib.agents.dqn import DQNTrainer
# from ray.rllib.agents.sac import SACTrainer
# from ray.rllib.agents.ppo import PPOTrainer

from sumo_env import sumoEnv

if __name__ == '__main__':
    ray.init()
    # algo = ppo.PPO(
    #     env=sumoEnv,
    #     config={
    #         'env_config':{}
    #     }
    # )
    # algo.train()
    stop = {"training_iteration": 2}
    rllib_config = {"env":sumoEnv,
                    "env_config":{},
                    "framework":"torch",
                    "model":{
                        "conv_filters":[[k,100,9] for k in range(1,13)]
                    }
    }

    tunner = tune.Tuner(
        ppo.PPO,
        param_space=rllib_config,
        run_config=air.RunConfig(
            name='PPO_result',
            stop=stop
        )
    )
    tunner.fit()
    ray.shutdown()