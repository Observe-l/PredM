import traci
import numpy as np
import pandas as pd

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
        get current state
        '''
        parking_state = traci.vehicle.getStops(vehID=self.id)[0]
        self.position = parking_state.stoppingPlaceID
        if parking_state.arrival < 0:
            self.state = 'delivery'
        elif parking_state.stoppingPlaceID == 'MainParking_0':
            self.state = 'free'
        else:
            self.state = 'waitting'
        return {'state':self.state, 'postion':self.position}
    
    def load_cargo(self, weight:float) -> tuple:
        '''
        Load cargo to the lorry. Cannot exceed the maximum capacity. The unit should be 'kg'.
        After the lorry is full, the state will change to pending, and the color change to Red
        If lorry is not empty, it would be blue color
        '''
        if self.weight + weight <= self.capacity:
            self.weight += weight
            self.state = 'loading'
            traci.vehicle.setColor(typeID=self.id,color=(0,0,255,255))
            return ('successful', 0.0)
        else:
            self.weight = self.capacity
            self.state = 'pending'
            traci.vehicle.setColor(typeID=self.id,color=(255,0,0,255))
            return ('full', self.weight + weight - self.capacity)
    
    def delivery(self, parking_available:dict, desitination:str, current_position:str):
        '''
        delevery the cargo to another factory
        '''
        if parking_available[desitination+'_0'] <= 4:
            # Select the new route
            traci.vehicle.setRouteID(vehID=self.id, routeID=current_position[0:-2] + '_to_' + desitination)
            # Move out the car parking area
            traci.vehicle.setParkingAreaStop(vehID=self.id, stopID=current_position, duration=0)
            traci.vehicle.setParkingAreaStop(vehID=self.id, stopID=desitination+'_0')
        else:
            traci.vehicle.rerouteParkingArea(vehID=self.id, parkingAreaID=desitination+'_1')
    
    def unload_cargo(self, weight:float):
        '''
        Unload cargo. If lorry is empty, health become waitting.
        '''
        assert weight < self.weight, f"cargo on {self.id} are not enough"
        self.weight -= weight
        if self.weight == 0:
            self.state = 'waitting'







