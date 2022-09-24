from tkinter.messagebox import NO
import traci
import numpy as np
import pandas as pd

from .lorry_manage import Lorry

class Factory(object):
    '''
    The class of factory
    '''
    def __init__(self, factory_id:str = 'Factory1', next_factory:str = 'Factory2', product_rate:dict = {'A':200.0}, capacity:float=10000000.0):
        self.id = factory_id
        self.next_factory = next_factory
        if next_factory == 'Factory5':
            self.next_factory = 'Factory1'

        self.product= pd.DataFrame(product_rate.items(),columns=['product','rate'])
        self.product['storage'] = [0.0] * len(product_rate)

        self.capacity = capacity
        self.container = 0
    
    def produce_product(self):
        '''
        Produce new product.
        '''
        if self.container < self.capacity:
            self.product['storage'] = self.product[['rate','storage']].sum(axis=1)
            self.container = self.product['storage'].sum()
    
    def load_cargo(self, lorry:Lorry, parking_available:dict):
        '''
        Load cargo to the lorry in current factory
        '''
        if self.id in lorry.position and (lorry.state == 'waitting' or lorry.state == 'loading'):
            if lorry.state == 'waitting':
                print(f'Start loading cargo at:{self.id}')
            if self.container >= 1000:
                lorry_state, exceed_cargo =  lorry.load_cargo(1000)
                self.product.loc[0,'storage'] = self.product.loc[0,'storage'] - (1000-exceed_cargo)
                self.container = self.product['storage'].sum()
            else:
                lorry_state, exceed_cargo =  lorry.load_cargo(self.container)
                self.product.loc[0,'storage'] = exceed_cargo
                self.container = self.product['storage'].sum()
            if lorry_state == 'full':
                lorry.delivery(parking_available, self.next_factory,lorry.position)
    def unload_cargo(self,lorry:Lorry):
        '''
        Unload cargo to container
        '''
        if self.id in lorry.position and (lorry.state == 'pending for unloading' or lorry.state == 'unloading'):
            if lorry.state == 'pending for unloading':
                print(f'start unloading at:{self.id}')
            lorry.unload_cargo(200)
    
    def factory_step(self, lorry:Lorry, parking_available:dict):
        self.produce_product()
        self.unload_cargo(lorry)
        self.load_cargo(lorry, parking_available)
        if lorry.state != 'stop':
            print(f'lorry id:{lorry.id}, current state:{lorry.state}, current weight:{lorry.weight}, mk_state:{lorry.mk_state}')


