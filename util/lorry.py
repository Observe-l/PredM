import traci
import numpy as np
import pandas as pd

from random import random
class Lorry(object):
    '''
    The class of lorry. 
    Parameters: lorry ID, health, position, destination ...
    Function: updata health, move to some positon, fix or broken ...
    '''
    def __init__(self, lorry_id:str = 'lorry_0', capacity:float = 10.0, weight:float = 0.0,\
                 state:str = 'delivery', position:str = 'Factory0', destination:str = 'Factory0', product:str = 'A', eng=None, mdl:str=None) -> None:
        '''
        Parameters:
        lorry_id: string
        capacity: The maximum capacity(t) of lorry. Default value is 10 t
        product: current loading product
        weight: Current weight of cargo(kg).
        state: The job of the lorry. free, waitting, loading, pending, delivery, repair, broken
        position: string
        destination: string
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

        # Markov state
        #    5 (lambda_0 = 0.013364)
        #0 1 2 3 4 (lambda_1=0.333442, lambda_m=0.653194)
        self.mk_state = 0
        lm_0 = 1/36
        lm_1 = 1/6
        self.threshold1 = lm_0
        self.threshold2 = 1-lm_1
        # Transfer the state after running 1 hour
        self.state_trans = 3600
        self.step = 1

        # recover after time_broken
        self.time_broken = 86400 # 1 day
        self.time_repair = 3600 *4 # 4 hours
        self.frequency = 86400 # 1 day

        # Temporal repaired time step
        self.step_tmp = 0


        self.actual_dr, self.expected_dr, self.actual_speed, self.expected_speed = np.zeros(4)

        # matlab engine
        self.eng = eng
        self.mdl = mdl

        # sensor reading
        self.sensor = pd.DataFrame({'c1':[],
                                    'c2':[],
                                    'c3':[],
                                    'c4':[],
                                    'c5':[],
                                    'c6':[],
                                    's1':[],
                                    's2':[],
                                    's3':[],
                                    's4':[],
                                    'state':[],
                                    'time_step':[]
        })

        self.g1=self.eng.evalin('base','g1')
        self.g2=self.eng.evalin('base','g2')
        self.g3=self.eng.evalin('base','g3')

    
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

    def refresh_state(self,time_step) -> dict:
        '''
        get current state, refresh state
        '''
        # Check current location
        try:
            parking_state = traci.vehicle.getStops(vehID=self.id)[-1]
        except:
            traci.vehicle.add(vehID=self.id,routeID=self.destination + '_to_'+ self.destination, typeID='lorry')
            traci.vehicle.setParkingAreaStop(vehID=self.id,stopID=self.destination)
            traci.vehicle.setColor(typeID=self.id,color=self.color)
            parking_state = traci.vehicle.getStops(vehID=self.id)[-1]


        self.position = parking_state.stoppingPlaceID
        # Repair the engine
        if self.state == 'broken':
            self.step_tmp += 1
            # Repair the lorry, spend 1 day
            if self.step_tmp % self.time_broken == 0:
                traci.vehicle.setStop(vehID=self.id,edgeID=traci.vehicle.getRoadID(vehID=self.id),pos=traci.vehicle.getLanePosition(vehID=self.id),duration=0)
                self.state = 'delivery'
                self.mk_state = 0
                self.step += 1
                print(f'[recover] {self.id}')
                with open('baseline_lorry_record','a') as f:
                    f.write(f'{time_step}\t{self.id}\t\t{self.mk_state}\trecover after broken\n')
        # mannually repair the engine
        elif self.state == 'repair':
            self.step_tmp +=1
            if self.step_tmp % self.time_repair == 0:
                traci.vehicle.setStop(vehID=self.id,edgeID=traci.vehicle.getRoadID(vehID=self.id),pos=traci.vehicle.getLanePosition(vehID=self.id),duration=0)
                self.state = self.recover_state
                self.mk_state = 0
                self.step += 1
                print(f'[recover] {self.id}')
                with open('baseline_lorry_record','a') as f:
                    f.write(f'{time_step}\t{self.id}\t\t{self.mk_state}\trecover after repaired\n')

        elif parking_state.arrival < 0:
            self.state = 'delivery'
            self.step += 1
        elif self.weight == self.capacity and self.position == self.destination:
            self.state = 'pending for unloading'
        elif self.weight == 0:
            self.state = 'waitting'
        

        # Update the engine state and get sensor reading from Simulink
        if self.state == 'delivery' and self.step % self.state_trans ==0:
            self.MDP_model(time_step)
            if self.mk_state == 4 or self.mk_state == 5:
                print(f'[Broken] {self.id}')
                self.state = 'broken'
                with open('baseline_lorry_record','a') as f:
                    f.write(f'{time_step}\t{self.id}\t\t{self.mk_state}\tbroken\n')
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

                
        return {'state':self.state, 'postion':self.position}
    
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
            return ('full', self.weight + weight - self.capacity)
    
    def delivery(self, destination:str) -> None:
        '''
        delevery the cargo to another factory
        '''
        self.state = 'delivery'
        # Remove vehicle first, add another lorry. (If we want to use the dijkstra algorithm in SUMO, we must creat new vehicle)
        self.destination = destination
        traci.vehicle.changeTarget(vehID=self.id, edgeID=destination)
        # Move out the car parking area
        traci.vehicle.setParkingAreaStop(vehID=self.id, stopID=self.position, duration=0)
        # Stop at next parking area
        traci.vehicle.setParkingAreaStop(vehID=self.id, stopID=self.destination)
        print(f'[move] {self.id} move from {self.position} to {self.destination}')
    
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
    
    def repaire(self,time_step):
        if ((time_step+1) % self.frequency == 0) and self.state != 'broken':
            self.mk_state = 0
            self.step = 1
            with open('baseline_lorry_record','a') as f:
                f.write(f'{time_step}\t{self.id}\t\t{self.mk_state}\trepair\n')
            # If the lorry is running, let it stop first
            if self.state == 'delivery':
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
            self.recover_state = self.state
            self.state = 'repair'
            print(f'[repair] {self.id} back to state {self.mk_state}')

    
    def MDP_model(self,time_step) -> None:
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


        lm = random()
        if self.mk_state < 4:
            if lm < self.threshold1:
                self.mk_state = 5
            elif lm > self.threshold2:
                self.mk_state += 1
            else:
                self.mk_state = self.mk_state
        else:
            self.mk_state = self.mk_state
        print(f'[MDP state] {self.id} state: {self.mk_state}')
        
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
        self.eng.set_param(self.mdl+'/[A B C D E F]','Value',np.array2string(clutch),nargout=0)
        out = self.eng.sim(self.mdl)
        # Get actual drive ratio
        idx = [{'type':'.','subs':'yout'},{'type':'{}','subs':[2]},{'type':'.','subs':'Values'},{'type':'.','subs':'Data'}]
        tmp_out = out
        for tmp_idx in idx:
            tmp_out = self.eng.subsref(tmp_out,tmp_idx)
        self.actual_dr = np.array(tmp_out)

        # # Get expected drive ratio
        # idx = [{'type':'.','subs':'yout'},{'type':'{}','subs':[3]},{'type':'.','subs':'Values'},{'type':'.','subs':'Data'}]
        # tmp_out = out
        # for tmp_idx in idx:
        #     tmp_out = self.eng.subsref(tmp_out,tmp_idx)
        # self.expected_dr = np.array(tmp_out)

        # Get actual speed
        idx = [{'type':'.','subs':'yout'},{'type':'{}','subs':[6]},{'type':'.','subs':'Values'},{'type':'.','subs':'Data'}]
        tmp_out = out
        for tmp_idx in idx:
            tmp_out = self.eng.subsref(tmp_out,tmp_idx)
        self.actual_speed = np.array(tmp_out)

        # Get expected speed
        idx = [{'type':'.','subs':'yout'},{'type':'{}','subs':[5]},{'type':'.','subs':'Values'},{'type':'.','subs':'Data'}]
        tmp_out = out
        for tmp_idx in idx:
            tmp_out = self.eng.subsref(tmp_out,tmp_idx)
        self.expected_speed = np.array(tmp_out)

        # Get gear command, there are 6 gears
        idx = [{'type':'.','subs':'yout'},{'type':'{}','subs':[4]},{'type':'.','subs':'Values'},{'type':'.','subs':'Data'}]
        tmp_out = out
        for tmp_idx in idx:
            tmp_out = self.eng.subsref(tmp_out,tmp_idx)
        self.gear_command = np.array(tmp_out).reshape(self.actual_dr.shape[0],6)

        self.expected_dr = np.zeros(self.actual_dr.shape)
        for i in range(self.gear_command.shape[0]):
            # Gear R
            if (self.gear_command[i] == [1,0,0,1,0,1]).all():
                self.expected_dr[i,0] = -self.g1/(self.g2*(1+self.g1))
            # Gear 1
            elif (self.gear_command[i] == [0,0,1,1,0,1]).all():
                self.expected_dr[i,0] = self.g1/(self.g3*(1+self.g1))
            # Gear 2
            elif (self.gear_command[i] == [0,0,1,0,1,1]).all():
                self.expected_dr[i,0] = self.g1*(1+self.g2)/((1+self.g1)*(self.g3+self.g2))
            # Gear 3
            elif (self.gear_command[i] == [1,0,1,0,0,1]).all():
                self.expected_dr[i,0] = self.g1/(1+self.g1)
            # Gear 4
            elif (self.gear_command[i] == [0,1,1,0,0,1]).all():
                self.expected_dr[i,0] = (self.g3*(1+self.g1)-1)/(self.g3*(1+self.g1))
            # Gear 5
            elif (self.gear_command[i] == [1,1,1,0,0,0]).all():
                self.expected_dr[i,0] = 1.0
            # Gear 6
            elif (self.gear_command[i] == [1,1,0,0,0,1]).all():
                self.expected_dr[i,0] = (self.g2*(1+self.g1)+1)/(self.g2*(1+self.g1))
            # Gear 7
            elif (self.gear_command[i] == [0,1,0,0,1,1]).all():
                self.expected_dr[i,0] = (1+self.g2)/self.g2
            # Gear 0
            else: 
                self.expected_dr[i,0] = 0


        tmp_array = np.concatenate((self.gear_command.T,self.actual_speed.T,self.expected_speed.T,self.actual_dr.T,self.expected_dr.T)).T
        tmp_sensor=pd.DataFrame(tmp_array,columns=['c1','c2','c3','c4','c5','c6','s1','s2','s3','s4'])
        tmp_sensor['state'] = f'MDP{self.mk_state}'
        tmp_sensor['time_step']=time_step
        self.sensor=pd.concat([self.sensor,tmp_sensor],ignore_index=True)        
        




