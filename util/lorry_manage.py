import traci
import numpy as np
import pandas as pd

class Lorry(object):
    '''
    The class of lorry. 
    Parameters: lorry ID, status, position, desitination ...
    Function: updata status, move to some positon, fix or brocken ...
    '''
    def __init__(self, lorry_id:str = 'lorry_0', capacity:float = 10000.0, weight:float = 0.0,\
                 schedule:str = 'delivery', status:str = 'normal', position:list = [0,0], desitination:str = 'MainParking'):
        '''
        Parameters:
        lorry_id: string
        capacity: The maximum capacity(kg) of lorry. Default value is 10,000 kg
        weight: Current weight of cargo(kg).
        schedule: The job of the lorry. free, waitting, loading, pending, delivery.
        status: The healthy status. normal, fixing or brocken.
        position: string
        desitination: string
        '''
        self.id = lorry_id
        self.capacity = capacity
        self.weight = weight

        self.schedule = schedule
        self.status = status
        self.position = position
        self.desitination = desitination
    
    def update_lorry(self, capacity:float = 10000.0, weight:float = 0.0,\
                     schedule:str = 'delivery', status:str = 'normal', position:list = [0,0], desitination:str = 'MainParking'):
        '''
        update the parameters
        '''
        self.capacity = capacity
        self.weight = weight

        self.schedule = schedule
        self.status = status
        self.position = position
        self.desitination = desitination

    def refresh_schedule(self) -> tuple:
        '''
        get current schedule
        '''
        stop_status = traci.vehicle.getStops(vehID=self.id)[0]
        if stop_status.arrival < 0:
            self.schedule = 'delivery'
        elif stop_status.stoppingPlaceID == 'MainParking':
            self.schedule = 'free'
        else:
            self.schedule = 'waitting'
        return (self.schedule, stop_status.stoppingPlaceID)

    def update_possition(self):
        '''
        update the position
        '''
        self.position = traci.vehicle.getPosition(vehID=self.id)
    
    def load_cargo(self, weight:float) -> tuple:
        '''
        Load cargo to the lorry. Cannot exceed the maximum capacity. The unit should be 'kg'.
        After the lorry is full, the schedule will change to pending, and the color change to Red
        If lorry is not empty, it would be blue color
        '''
        if self.weight + weight <= self.capacity:
            self.weight += weight
            self.schedule = 'loading'
            traci.vehicle.setColor(typeID=self.id,color=(0,0,255,255))
            return ('successful', 0.0)
        else:
            self.weight = self.capacity
            self.schedule = 'pending'
            traci.vehicle.setColor(typeID=self.id,color=(255,0,0,255))
            return ('full', self.weight + weight - self.capacity)
    
    def delivery(self, parking_available:dict, desitination:str):
        '''
        delevery the cargo to another factory
        '''
        if parking_available[desitination+'_0'] > 0:
            traci.vehicle.rerouteParkingArea(vehID=self.id, parkingAreaID=desitination+'_0')
        else:
            traci.vehicle.rerouteParkingArea(vehID=self.id, parkingAreaID=desitination+'_1')
    
    def unload_cargo(self, weight:float):
        '''
        Unload cargo. If lorry is empty, status become waitting.
        '''
        assert weight < self.weight, f"cargo on {self.id} are not enough"
        self.weight -= weight
        if self.weight == 0:
            self.schedule = 'waitting'







