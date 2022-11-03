import traci
import numpy as np
import pandas as pd

from random import random
class Lorry(object):
    '''
    The class of lorry. 
    Parameters: lorry ID, health, position, desitination ...
    Function: updata health, move to some positon, fix or broken ...
    '''
    def __init__(self, lorry_id:str = 'lorry_0', capacity:float = 10.0, weight:float = 0.0,\
                 state:str = 'delivery', position:str = 'Factory0', desitination:str = 'Factory1', product:str = 'P1', eng=None, mdl:str=None) -> None:
        '''
        Parameters:
        lorry_id: string
        capacity: The maximum capacity(t) of lorry. Default value is 10 t
        product: current loading product
        weight: Current weight of cargo(kg).
        state: The job of the lorry. free, waitting, loading, pending, delivery, fixing, broken
        position: string
        desitination: string
        '''
        # Create lorry in sumo. If the lorry already exist, remove it first
        try:
            traci.vehicle.add(vehID=lorry_id,routeID=position + '_to_'+ desitination, typeID='lorry')
        except:
            traci.vehicle.remove(vehID=lorry_id)
            traci.vehicle.add(vehID=lorry_id,routeID=position + '_to_'+ desitination, typeID='lorry')
        traci.vehicle.setParkingAreaStop(vehID=lorry_id,stopID=position)
        
        self.id = lorry_id
        self.capacity = capacity
        self.weight = weight

        self.state = state
        self.position = position
        self.desitination = desitination
        self.product = product

        # Markov state
        #    5 (lambda_0 = 0.013364)
        #0 1 2 3 4 (lambda_1=0.333442, lambda_m=0.653194)
        self.mk_state = 0
        self.threshold1 = 0.013364
        self.threshold2 = 1-0.333442
        # Transfer the state every 8 minutes(480 seconds / sumo time)
        self.state_trans = 480
        self.step = 1

        # Temporal repaired time step
        self.step_tmp = 0


        self.actual_dr, self.expected_dr, self.actual_speed, self.expected_speed = np.zeros(4)

        # matlab engine
        self.eng = eng
        self.mdl = mdl

    
    def update_lorry(self, capacity:float = 10000.0, weight:float = 0.0,\
                     state:str = 'delivery', position:str = 'Factory0', desitination:str = 'Factory1') -> None:
        '''
        update the parameters
        '''
        self.capacity = capacity
        self.weight = weight

        self.state = state
        self.position = position
        self.desitination = desitination

    def refresh_state(self) -> dict:
        '''
        get current state, refresh state
        '''
        # Check current location
        parking_state = traci.vehicle.getStops(vehID=self.id)[0]
        self.position = parking_state.stoppingPlaceID
        if parking_state.arrival < 0 and self.state != 'broken':
            self.state = 'delivery'
            self.step += 1
        elif self.weight == self.capacity and self.position == self.desitination:
            self.state = 'pending for unloading'
        elif self.weight == 0:
            self.state = 'waitting'
        # Repair the engine
        elif self.state == 'broken':
            self.step_tmp += 1
            # Recover after 10 minutes
            if self.step_tmp == 600:
                traci.vehicle.setSpeed(vehID=self.id, speed=-1)
        # Update the engine state and get sensor reading from Simulink
        if self.state == 'delivery' and self.step % self.state_trans ==0:
            self.MDP_model()
            if self.mk_state == 4 or self.mk_state == 5:
                print(f'{self.id} is broken')
                self.state = 'broken'
                traci.vehicle.setSpeed(vehID=self.id, speed=0.0)
                
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
            traci.vehicle.setColor(typeID=self.id,color=(0,0,255,255))
            return ('successful', 0.0)
        else:
            self.weight = self.capacity
            self.state = 'pending for delivery'
            traci.vehicle.setColor(typeID=self.id,color=(255,0,0,255))
            return ('full', self.weight + weight - self.capacity)
    
    def delivery(self, desitination:str) -> None:
        '''
        delevery the cargo to another factory
        '''
        self.state = 'delivery'
        # Remove vehicle first, add another lorry. (If we want to use the dijkstra algorithm in SUMO, we must creat new vehicle)
        self.desitination = desitination
        traci.vehicle.changeTarget(vehID=self.id, edgeID=desitination)
        # Move out the car parking area
        traci.vehicle.setParkingAreaStop(vehID=self.id, stopID=self.position, duration=0)
        # Stop at next parking area
        traci.vehicle.setParkingAreaStop(vehID=self.id, stopID=self.desitination)
    
    def unload_cargo(self, weight:float) -> tuple[str, float]:
        '''
        Unload cargo. If lorry is empty, health become waitting.
        '''
        self.state = 'unloading'
        traci.vehicle.setColor(typeID=self.id,color=(0,0,255,255))
        if weight <= self.weight:
            self.weight -= weight
            return ('successful', 0.0)
        else:
            remainning_weight = self.weight
            self.weight =0
            self.state = 'waitting'
            traci.vehicle.setColor(typeID=self.id,color=(0,255,0,255))
            return ('not enough', remainning_weight)
    
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
        print(f'{self.id} state: {self.mk_state}')
        
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

        # Get expected drive ratio
        idx = [{'type':'.','subs':'yout'},{'type':'{}','subs':[3]},{'type':'.','subs':'Values'},{'type':'.','subs':'Data'}]
        tmp_out = out
        for tmp_idx in idx:
            tmp_out = self.eng.subsref(tmp_out,tmp_idx)
        self.expected_dr = np.array(tmp_out)

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
        
        




