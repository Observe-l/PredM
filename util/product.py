import traci
import numpy as np
import pandas as pd
from .lorry import Lorry
from .factory import Factory

class product_management(object):
    '''
    This class is based on the industry 4.0 project
    There are 2 final products: A(P123) and B(P234)
    '''
    
    def __init__(self, factory:list[Factory], lorry:list[Lorry]) -> None:
        '''
        Input the list of factories and the lorries
        Producding order:
        Factory0: produce P1
        Facotry1: produce P2, P12
        Factory3: produce P3, P23, A(P123)
        Factory4: produce P4, B(P234)
        '''
        self.factory = factory
        self.lorry = lorry
        self.p = np.array([1.0,1.0,1.0,1.0,1.0])
        self.et = 1200
        # Create the dictionary for product
        self.product_idx = {tmp_factory.id:tmp_factory.product.index.values.tolist() for tmp_factory in self.factory}
    
    def produce_product(self) -> None:
        '''
        Produce new product in all factories
        '''
        for tmp_factory in self.factory:
            tmp_factory.produce_product()
            for tmp_lorry in self.lorry:
                tmp_factory.unload_cargo(tmp_lorry)
    
    def transfer_product(self) -> None:
        s1 = np.zeros(len(self.factory))
        s2 = 0*np.eye(len(self.factory))
        s3 = np.zeros(len(self.factory))

        s3_pool = s3

        lorry_count = np.array([i.desitination for i in self.lorry])
        unique, counts = np.unique(lorry_count,return_counts=True)
        n_lory = dict(zip(unique, counts))

        for m in range(len(self.factory)):
            # Calculate s1
            tmp_factory = self.factory[m]
            tmp_product = self.product_idx[tmp_factory.id]
            tmp_storage = tmp_factory.container.loc[tmp_product,'storage'].max()
            s1[m] = self.p[0] * tmp_storage

            # Calculate s2
            # Get data from dataframe
            tmp_material = tmp_factory.product['material'].values
            tmp_ratio = tmp_factory.product['ratio'].values
            # Data processing, generate the list of material
            tmp_material = np.array([i.split(',') for i in tmp_material if type(i) is str]).flatten()
            tmp_ratio = np.array([i.split(',') for i in tmp_ratio if type(i) is str]).flatten()

            tmp_material, tmp_idx = np.unique(tmp_material,return_index=True)
            tmp_ratio = tmp_ratio[tmp_idx]
            for j in range(tmp_material.shape[0]):
                tmp_m = tmp_material[j]
                factory_idx = int([i for i in self.product_idx for item in self.product_idx[i] if item==tmp_m][0][-1])
                s2[m,factory_idx] += self.p[1]*(tmp_factory.product.loc[tmp_m,'rate']*tmp_ratio[j]*self.et - tmp_factory.container.loc[tmp_m,'storage'])
            # sum of each row
            # s2 = np.sum(s2,axis=1)

            # Calculate s3
            s3[m] = -n_lory[tmp_factory.id] * self.p[2]
            s3_pool[m] = -(n_lory[tmp_factory.id]-1) * self.p[2]
        
        s2 = np.sum(s2,axis=1)
        s = s1 + s2 + s3
        # Generate the lorry pool
        s_pool = (s1 + s2 + s3_pool>0)
        # lorry in the factory_idx could be assigned
        factory_idx = [self.factory[i].id for i in np.where(s_pool==True)[0]]
        lorry_pool = [i for i in self.lorry if i.desitination in factory_idx]

        # Assign the lorry
        factory_assign = self.factory[np.argmax(s)].id
        c = np.zeros(len(lorry_pool))
        for i in len(lorry_pool):
            tmp_lorry = lorry_pool[i]
            tmp_des = tmp_lorry.desitination
            traci.vehicle.changeTarget(vehID=tmp_lorry.id,edgeID=factory_assign)
            c[i] = traci.vehicle.getDrivingDistance(vehID=tmp_lorry.id, edgeID=factory_assign,position=0)
            traci.vehicle.changeTarget(vehID=tmp_lorry.id,edgeID=tmp_des)



