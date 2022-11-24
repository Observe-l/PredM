import traci
import numpy as np
import pandas as pd
from csv import writer

import random
class Lorry(object):
    '''
    The class of lorry. 
    Parameters: lorry ID, health, position, destination ...
    Function: updata health, move to some positon, fix or broken ...
    '''
    def __init__(self, lorry_id:str = 'lorry_0', capacity:float = 2.0, weight:float = 0.0,\
                 state:str = 'delivery', position:str = 'Factory0', destination:str = 'Factory0', product:str = 'A', eng=None, mdl:str=None,\
                 path:str = 'result', time_broken:int = 86400, mdp_freq:float = 6*3600, env_step:int = 3600, broken_freq:float = 86400*10,\
                 maintenance_freq:float = 4*3600, repair_freq:float = 86400*3) -> None:
        '''
        Parameters:
        lorry_id: string
        capacity: The maximum capacity(t) of lorry. Default value is 10 t
        product: current loading product
        weight: Current weight of cargo(kg).
        state: The state of the lorry: waitting, loading, pending, delivery, repair, broken, maintenance
        position: string
        destination: string
        path: save the experiments result

        MDP parameter, unit is second
        time_broken: time based repair speed
        mdp_freq: mdp transfor frequency when lorry is running
        env_step: RL time step
        broken_freq: random failure frequency
        maintenance_freq: maintenance successful frequency
        repair_freq: repair succseeful frequency

        '''
        # Create lorry in sumo. If the lorry already exist, remove it first
        try:
            traci.vehicle.add(vehID=lorry_id,routeID=position + '_to_'+ destination, typeID='lorry')
        except:
            traci.vehicle.remove(vehID=lorry_id)
            traci.vehicle.add(vehID=lorry_id,routeID=position + '_to_'+ destination, typeID='lorry')
        traci.vehicle.setParkingAreaStop(vehID=lorry_id,stopID=position)
        
        self.id = lorry_id
        self.capacity = capacity
        self.weight = weight

        self.state = state
        self.position = position
        self.destination = destination
        self.product = product
        self.color = (255,255,0,255)
        self.recover_state = 'waitting'

        # sumo time
        self.time_step = 0
        # record total transported product
        self.total_product = 0.0
        self.product_record = pd.DataFrame({'time':[0.0], 'total_product':[0.0]})
        self.product_record.set_index(['time'], inplace=True)

        # self.reward = pd.DataFrame({'time':[0.0], 'total_product':[0.0]})
        # self.reward.set_index(['time'], inplace=True)

        # Markov state
        #    5 (lambda_0 = 0.013364)
        #0 1 2 3 4 (lambda_1=0.333442, lambda_m=0.653194)
        self.mk_state = 0
        lm_0 = env_step/broken_freq
        lm_1 = env_step/mdp_freq
        self.mu0 = env_step/maintenance_freq
        self.mu1 = env_step/repair_freq
        self.threshold1 = lm_0
        self.threshold2 = 1-lm_1
        # Transfer the state after time 'state_trans'
        self.state_trans = env_step
        self.step = 1

        # recover after time_broken
        self.time_broken = time_broken # 1 day
        self.time_repair = 3600 * 4 # 4 hours
        self.frequency = 86400 # 1 day

        # Temporal repaired time step
        self.step_repair = 0
        self.path = path + '/lorry_record.csv'

        # matlab engine
        self.eng = eng
        self.mdl = mdl

        # maintenance flag, when true, the engine start maintenance
        # default: False
        self.maintenance_flag = False
        # episode flag
        self.episode_flag = False

        # sensor reading
        self.sensor = pd.DataFrame({'s1':[],
                                    's2':[],
                                    's3':[],
                                    's4':[],
                                    's5':[],
                                    's6':[],
                                    's7':[],
                                    's8':[],
                                    's9':[],
                                    'MDPstate':[]
        })

    
    def update_lorry(self, capacity:float = 10000.0, weight:float = 0.0,\
                     state:str = 'delivery', position:str = 'Factory0', destination:str = 'Factory0') -> None:
        '''
        update the parameters
        '''
        self.capacity = capacity
        self.weight = weight

        self.state = state
        self.position = position
        self.destination = destination
    
    # def record_reward(self):
    #     self.product_record.at[self.time_step,'total_product'] = self.total_product

    def refresh_state(self,time_step, repair_flag) -> dict:
        '''
        get current state, refresh state
        '''
        self.time_step = time_step
        # record the transported product
        self.product_record.at[self.time_step,'total_product'] = self.total_product

        # Check current location, if the vehicle remove by SUMO, add it first
        try:
            tmp_pk = traci.vehicle.getStops(vehID=self.id)
            parking_state = tmp_pk[-1]
        except:
            print(f'{self.id}, position:{self.position}, destination:{self.destination}, parking: {traci.vehicle.getStops(vehID=self.id)}, state: {self.state}')
            print(f'weight: {self.weight}, mdp state: {self.mk_state}')
            parking_state = traci.vehicle.getStops(vehID=self.id)[-1]
        # except:
        #     traci.vehicle.add(vehID=self.id,routeID=self.destination + '_to_'+ self.destination, typeID='lorry')
        #     traci.vehicle.setParkingAreaStop(vehID=self.id,stopID=self.destination)
        #     traci.vehicle.setColor(typeID=self.id,color=self.color)
        #     parking_state = traci.vehicle.getStops(vehID=self.id)[-1]

        self.position = parking_state.stoppingPlaceID

        # fix some bug, ensure lorry stop when maintenance
        if self.mk_state > 5 and self.recover_state=='delivery' and len(tmp_pk)==1:
            self.lorry_stop()

        # Lorry maintenance
        if self.maintenance_flag and self.time_step%self.state_trans==1:
            self.maintenance()
        # Repair the engine
        if repair_flag:
            self.repair()
        # if self.state == 'broken':
        #     self.step_repair += 1
        #     # Repair the lorry, spend 1 day
        #     if self.step_repair % self.time_broken == 0:
        #         self.state = self.recover_state
        #         self.mk_state = 0
        #         self.step += 1
        #         # In sumo the lorry resume from stop
        #         traci.vehicle.resume(vehID=self.id)
        #         print(f'[recover] {self.id}')
        #         with open(self.path,'a') as f:
        #             f_csv = writer(f)
        #             f_csv.writerow([self.time_step,self.id,self.mk_state,'recover after broken'])

        if self.state == 'broken' and self.time_step % self.state_trans == 1:
            self.broken_repair()
        # mannually repair the engine
        elif self.state == 'repair':
            self.step_repair +=1
            if self.step_repair % self.time_repair == 0:
                self.state = self.recover_state
                self.mk_state = 0
                self.step += 1
                # In sumo the lorry resume from stop
                traci.vehicle.resume(vehID=self.id)
                print(f'[recover] {self.id}')
                with open(self.path,'a') as f:
                    f_csv = writer(f)
                    f_csv.writerow([self.time_step,self.id,self.mk_state,'recover after repaired'])
                
                # terminate the episode
                self.episode_flag = True
        # ignore the maintenance state
        elif self.mk_state > 3:
            pass
        elif parking_state.arrival < 0:
            self.state = 'delivery'
            self.step += 1
        elif self.weight == self.capacity and self.position == self.destination:
            self.state = 'pending for unloading'
        elif self.weight == 0:
            self.state = 'waitting'
        # Update the engine state and get sensor reading from Simulink
        if self.state == 'delivery' and self.step % self.state_trans ==0:
            self.MDP_model()
            if self.mk_state == 4 or self.mk_state == 5:
                print(f'[Broken] {self.id}')
                self.state = 'broken'
                with open(self.path,'a') as f:
                    f_csv = writer(f)
                    f_csv.writerow([self.time_step,self.id,self.mk_state,'broken'])
                self.lorry_stop()
        return {'state':self.state, 'postion':self.position}


    def lorry_stop(self):
        '''
        When lorry broken or we decide to repair / maintain the lorry,
        use this function to stop the lorry first
        Time-based function
        '''
        # The lorry shouldn't break at factory road, otherwise, let it move to the end of the road
        current_edge = traci.vehicle.getRoadID(vehID=self.id)
        factory_idx = ['Factory0','Factory1','Factory2','Factory3']
        # arrive the destination
        if self.destination == current_edge:
            if self.weight == 0:
                self.recover_state = 'waitting'
            else:
                self.recover_state = 'pending for unloading'
        # start from current factory
        elif current_edge in factory_idx:
            self.recover_state = 'delivery'
            try:
                # stop after 20 meters barking
                traci.vehicle.setStop(vehID=self.id,edgeID=traci.vehicle.getRoadID(vehID=self.id),pos=150)
            except:
                # stop at next edge. the length of the edge must longer than 25m
                tmp_idx = traci.vehicle.getRouteIndex(vehID=self.id)
                tmp_edge = traci.vehicle.getRoute(vehID=self.id)[tmp_idx+2]
                traci.vehicle.setStop(vehID=self.id,edgeID=tmp_edge,pos=0)
        else:
            self.recover_state = 'delivery'
            try:
                # stop after 20 meters barking
                traci.vehicle.setStop(vehID=self.id,edgeID=traci.vehicle.getRoadID(vehID=self.id),pos=traci.vehicle.getLanePosition(vehID=self.id)+25)
            except:
                # stop at next edge. the length of the edge must longer than 25m
                tmp_idx = traci.vehicle.getRouteIndex(vehID=self.id)
                try:
                    tmp_edge = traci.vehicle.getRoute(vehID=self.id)[tmp_idx+1]
                    traci.vehicle.setStop(vehID=self.id,edgeID=tmp_edge,pos=25)
                except:
                    tmp_edge = traci.vehicle.getRoute(vehID=self.id)[tmp_idx+2]
                    traci.vehicle.setStop(vehID=self.id,edgeID=tmp_edge,pos=0)

    def delivery(self, destination:str) -> None:
        '''
        delevery the cargo to another factory
        '''
        self.state = 'delivery'
        # Remove vehicle first, add another lorry. (If we want to use the dijkstra algorithm in SUMO, we must creat new vehicle)
        self.destination = destination
        traci.vehicle.changeTarget(vehID=self.id, edgeID=destination)
        # Move out the car parking area
        traci.vehicle.resume(vehID=self.id)
        # Stop at next parking area
        traci.vehicle.setParkingAreaStop(vehID=self.id, stopID=self.destination)
        #print(f'[move] {self.id} move from {self.position} to {self.destination}')

    def load_cargo(self, weight:float, product:str) -> tuple[str, float]:
        '''
        Load cargo to the lorry. Cannot exceed the maximum capacity. The unit should be 'kg'.
        After the lorry is full, the state will change to pending, and the color change to Red
        If lorry is not empty, it would be blue color
        '''
        self.product = product
        if self.weight + weight < self.capacity:
            self.weight += weight
            self.state = 'loading'
            # RGBA
            self.color = (0,0,255,255)
            traci.vehicle.setColor(typeID=self.id,color=self.color)
            return ('successful', 0.0)
        else:
            self.weight = self.capacity
            self.state = 'pending for delivery'
            self.color = (255,0,0,255)
            traci.vehicle.setColor(typeID=self.id,color=self.color)
            # After the lorry is full, record it
            self.total_product += self.weight
            return ('full', self.weight + weight - self.capacity)
    
    def unload_cargo(self, weight:float) -> tuple[str, float]:
        '''
        Unload cargo. If lorry is empty, health become waitting.
        '''
        self.state = 'unloading'
        self.color = (0,0,255,255)
        traci.vehicle.setColor(typeID=self.id,color=self.color)
        if weight <= self.weight:
            self.weight -= weight
            return ('successful', 0.0)
        else:
            remainning_weight = self.weight
            self.weight =0
            self.state = 'waitting'
            self.color = (0,255,0,255)
            traci.vehicle.setColor(typeID=self.id,color=self.color)
            return ('not enough', remainning_weight)
    
    def repair(self):
        if ((self.time_step+1) % self.frequency == 0) and self.state != 'broken':
            self.mk_state = 0
            self.step = 1
            self.recover_state = self.state
            with open(self.path,'a') as f:
                f_csv = writer(f)
                f_csv.writerow([self.time_step,self.id,self.mk_state,'repairing'])
            # If the lorry is running, let it stop first
            if self.state == 'delivery':
                self.lorry_stop()
            
            self.state = 'repair'
            print(f'[repair] {self.id} back to state {self.mk_state}')
    
    def broken_repair(self):
        lm = random.uniform(0,1)
        if lm < self.mu1:
            self.state = self.recover_state
            self.mk_state = 0
            self.step += 1
            # In sumo the lorry resume from stop
            if self.state == 'delivery':
                traci.vehicle.resume(vehID=self.id)
            print(f'[recover] {self.id}')
            with open(self.path,'a') as f:
                f_csv = writer(f)
                f_csv.writerow([self.time_step,self.id,self.mk_state,'recover after broken'])
            
            # terminate the episode
            self.episode_flag = True
        else:
            pass
        
    def maintenance(self):
        lm = random.uniform(0,1)
        if self.mk_state < 4:
            self.recover_state = self.state
            # If the lorry is running, let it stop first
            if self.state == 'delivery':
                self.lorry_stop()
            if lm < self.threshold1:
                self.mk_state = 5
                print(f'[Broken] {self.id}')
                self.state = 'broken'
                self.maintenance_flag = False
                return 'broken'
            else:
                self.mk_state += 6
                self.state = 'maintenance'
                print(f'[maintenance] {self.id} go to state {self.mk_state}')
                with open(self.path,'a') as f:
                    f_csv = writer(f)
                    f_csv.writerow([self.time_step,self.id,self.mk_state,'maintenance'])
                return 'maintenance'
        elif self.mk_state > 5:
            if lm < self.mu0:
                self.mk_state = max(0, self.mk_state-7)
                self.state = self.recover_state
                # In sumo the lorry resume from stop
                if self.state == 'delivery':
                    traci.vehicle.resume(vehID=self.id)
                self.maintenance_flag = False
                print(f'[recover] {self.id}')
                with open(self.path,'a') as f:
                    f_csv = writer(f)
                    f_csv.writerow([self.time_step,self.id,self.mk_state,'recover after maintenance'])

                # terminate the episode
                self.episode_flag = True
                return 'successful'
            else:
                return 'try again'
        else:
            return 'broken'

    
    def MDP_model(self) -> None:
        '''
        Update the Simulink model
        State 0: Normal
        State 1: Clutch A, locked fault
        State 2: Clutch B,C  locked fault
        State 3: Clutch D,E locked fault, F unlocked fault
        State 4: Clutch A,B unlocked fault, E,F locked fault
        State 5: Clutch A,B,C,D,E,F unlocked fault

        lm is a random number. 
        If lm < 0.013364, Markov state go to 5. 
        If lm > 0.666558, Markov state pluse 1
        Otherwise, no change
        '''
        self.sensor.drop(self.sensor.index, inplace=True)
        lm = random.uniform(0,1)
        if self.mk_state < 4:
            if lm < self.threshold1:
                self.mk_state = 5
            elif lm > self.threshold2:
                self.mk_state += 1
            else:
                self.mk_state = self.mk_state
        else:
            self.mk_state = self.mk_state
        print(f'[MDP state] {self.id} state: {self.mk_state}, time:{self.time_step}')
        
        # Clutch fault injection
        if self.mk_state == 0:
            clutch = np.array([-1,-1,-1,-1,-1,-1],dtype=np.int64)
        elif self.mk_state == 1:
            clutch = np.array([1,-1,-1,-1,-1,-1],dtype=np.int64)
        elif self.mk_state == 2:
            clutch = np.array([-1, 1, 1,-1,-1,-1],dtype=np.int64)
        elif self.mk_state == 3:
            clutch = np.array([-1,-1,-1, 1, 1, 0],dtype=np.int64)
        elif self.mk_state == 4:
            clutch = np.array([0, 0,-1,-1, 1, 1],dtype=np.int64)
        elif self.mk_state == 5:
            clutch = np.array([0,0,0,0,0,0],dtype=np.int64)

        # Simulation
        splid_len = 100
        try:
            self.eng.set_param(self.mdl+'/[A B C D E F]','Value',np.array2string(clutch),nargout=0)
        except:
            print(f'{self.id}, mdp: {self.mk_state}, time: {self.time_step}, state: {self.state}')
            self.eng.set_param(self.mdl+'/[A B C D E F]','Value',np.array2string(clutch),nargout=0)
        out = self.eng.sim(self.mdl)
        # Get time
        idx = [{'type':'.','subs':'yout'},{'type':'{}','subs':[2]},{'type':'.','subs':'Values'},{'type':'.','subs':'Time'}]
        tmp_out = out
        for tmp_idx in idx:
            tmp_out = self.eng.subsref(tmp_out,tmp_idx)
        actual_time = np.array(tmp_out)

        # Get actual drive ratio
        idx = [{'type':'.','subs':'yout'},{'type':'{}','subs':[2]},{'type':'.','subs':'Values'},{'type':'.','subs':'Data'}]
        tmp_out = out
        for tmp_idx in idx:
            tmp_out = self.eng.subsref(tmp_out,tmp_idx)
        actual_dr = np.array(tmp_out)

        for _ in range(splid_len):
            tmp_idx = [np.where(actual_time <= 4*i + 4/splid_len)[0][-1] for i in range(9)]
            tmp_act_dr = actual_dr[tmp_idx]
            tmp_sensor=pd.DataFrame(tmp_act_dr.T,columns=['s1','s2','s3','s4','s5','s6','s7','s8','s9'])
            tmp_sensor['MDPstate'] = self.mk_state
            self.sensor=pd.concat([self.sensor,tmp_sensor],ignore_index=True)
        




