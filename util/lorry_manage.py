import traci
import numpy as np
import pandas as pd

from random import random
class Lorry(object):
    '''
    The class of lorry. 
    Parameters: lorry ID, health, position, desitination ...
    Function: updata health, move to some positon, fix or brocken ...
    '''
    def __init__(self, lorry_id:str = 'lorry_0', capacity:float = 10000.0, weight:float = 0.0,\
                 state:str = 'delivery', health:str = 'normal', position:str = 'MainParking_0', desitination:str = 'MainParking'):
        '''
        Parameters:
        lorry_id: string
        capacity: The maximum capacity(kg) of lorry. Default value is 10,000 kg
        weight: Current weight of cargo(kg).
        state: The job of the lorry. free, waitting, loading, pending, delivery.
        health: The healthy health. normal, fixing or brocken.
        position: string
        desitination: string
        '''
        self.id = lorry_id
        self.capacity = capacity
        self.weight = weight

        self.state = state
        self.health = health
        self.position = position
        self.desitination = desitination

        # Markov state
        #    5 (lambda_0 = 0.013364)
        #0 1 2 3 4 (lambda_1=0.333442, lambda_m=0.653194)
        self.mk_state = 0
    
    def update_lorry(self, capacity:float = 10000.0, weight:float = 0.0,\
                     state:str = 'delivery', health:str = 'normal', position:str = 'MainParking_0', desitination:str = 'MainParking'):
        '''
        update the parameters
        '''
        self.capacity = capacity
        self.weight = weight

        self.state = state
        self.health = health
        self.position = position
        self.desitination = desitination

    def refresh_state(self) -> dict:
        '''
        get current state, refresh state
        '''
        parking_state = traci.vehicle.getStops(vehID=self.id)[0]
        self.position = parking_state.stoppingPlaceID
        if self.health == 'dead':
            self.state = '                '
        elif parking_state.arrival < 0:
            self.state = 'delivery'
        elif parking_state.stoppingPlaceID == 'MainParking_0':
            self.state = 'free'
        elif self.weight == self.capacity and self.position == self.desitination:
            self.state = 'pending for unloading'
        elif self.weight == 0:
            self.state = 'waitting'

        if self.state == 'delivery':
            self.MDP_model()
            if self.mk_state == 4 or self.mk_state == 5:
                print(f'{self.id} is dead')
                self.health = 'dead'
                traci.vehicle.setSpeed(vehID=self.id, speed=0.0)
                
        return {'state':self.state, 'postion':self.position}
    
    def load_cargo(self, weight:float) -> tuple:
        '''
        Load cargo to the lorry. Cannot exceed the maximum capacity. The unit should be 'kg'.
        After the lorry is full, the state will change to pending, and the color change to Red
        If lorry is not empty, it would be blue color
        '''
        if self.weight + weight < self.capacity:
            self.weight += weight
            self.state = 'loading'
            traci.vehicle.setColor(typeID=self.id,color=(0,0,255,255))
            return ('successful', 0.0)
        else:
            self.weight = self.capacity
            self.state = 'pending for delivery'
            traci.vehicle.setColor(typeID=self.id,color=(255,0,0,255))
            return ('full', self.weight + weight - self.capacity)
    
    def delivery(self, parking_available:dict, desitination:str, current_position:str):
        '''
        delevery the cargo to another factory
        '''
        self.state = 'delivery'
        if parking_available[desitination+'_0'] <= 4:
            # Select the new route
            traci.vehicle.setRouteID(vehID=self.id, routeID=current_position[0:-2] + '_to_' + desitination)
            # Move out the car parking area
            self.desitination = desitination+'_0'
            traci.vehicle.setParkingAreaStop(vehID=self.id, stopID=current_position, duration=0)
            traci.vehicle.setParkingAreaStop(vehID=self.id, stopID=self.desitination)
        else:
            # Select the new route
            traci.vehicle.setRouteID(vehID=self.id, routeID=current_position[0:-2] + '_to_' + desitination)
            # Move out the car parking area
            self.desitination = desitination+'_1'
            traci.vehicle.setParkingAreaStop(vehID=self.id, stopID=current_position, duration=0)
            traci.vehicle.setParkingAreaStop(vehID=self.id, stopID=self.desitination)
            # traci.vehicle.rerouteParkingArea(vehID=self.id, parkingAreaID=desitination+'_1')
    
    def unload_cargo(self, weight:float):
        '''
        Unload cargo. If lorry is empty, health become waitting.
        '''
        # assert weight < self.weight, f"cargo on {self.id} are not enough"
        if weight < self.weight:
            self.weight -= weight
        else:
            self.weight =0
        self.state = 'unloading'
        traci.vehicle.setColor(typeID=self.id,color=(0,0,255,255))
        if self.weight == 0:
            self.state = 'waitting'
            traci.vehicle.setColor(typeID=self.id,color=(255,255,255,255))
    
    def MDP_model(self):
        # lm is a random number. 
        # If lm < 0.013364, Markov state go to 5. 
        # If lm > 0.666558, Markov state pluse 1
        # Otherwise, no change
        threshold1 = 0.00013364
        threshold2 = 0.986558
        lm = random()
        if self.mk_state < 4:
            if lm < threshold1:
                self.mk_state = 5
            elif lm > threshold2:
                self.mk_state += 1
            else:
                self.mk_state = self.mk_state
        else:
            self.mk_state = self.mk_state
        
        




