import optparse

# from sumo_env import sumoEnv
# from train_env import sumoEnv
from single_lorry_eva import sumoEnv

def get_options():
    optParse = optparse.OptionParser()
    optParse.add_option("-r","--repair",default=3,type=int,help="repair mean (days)")
    optParse.add_option("-m","--maintain",default=4,type=int,help="maintain mean (hours)")
    optParse.add_option("-d","--density",default=1,type=int,help="traffic density")
    options, args = optParse.parse_args()
    return options

if __name__ == '__main__':
    options = get_options()
    env = sumoEnv({'algo':f'daily-repair-{options.repair}days_maintain-{options.maintain}hours_density-{options.density}','repair':options.repair,'maintain':options.maintain,'map':options.density})
    # init the env
    obs = env.reset()
    reward = 0
    done_state = False
    step_count = 2

    while done_state == False:
        action = {}
        tmp_act = 0
        if step_count % 288 ==0:
            tmp_act = 1
        for tmp_key in obs:
            action[tmp_key] = tmp_act
        # action = agent.compute_single_action(observation=obs)
        obs, reward, done_state, _ = env.step(action)
        step_count += 1
