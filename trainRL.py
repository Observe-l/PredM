import ray
from ray import tune, air
from ray.tune.registry import register_env
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
    # def env_creator():
    #     return sumoEnv()
    # env = env_creator()
    # env_name = 'sumoEnv'
    # register_env(env_name, env_creator)

    # obs_space = env.observation_space
    # act_space = env.action_space
    # def gen_policy():
    #     return (None, obs_space, act_space)

    stop = {"training_iteration": 2}
    rllib_config = {"env":sumoEnv,
                    "env_config":{},
                    "framework":"torch",
                    "num_workers":1,
                    "multiagent":{
                        "policies":{"shared_policy"},
                        "policy_mapping_fn": (lambda agent_id, episode, **kwargs: "shared_policy"),
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