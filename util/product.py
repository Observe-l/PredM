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
        self.p = np.array([1.0,1.0,15.0,1.0,1.0])
        self.et = 1200
        # Create the dictionary for product
        # self.product_idx = {tmp_factory.id:tmp_factory.product.index.values.tolist() for tmp_factory in self.factory}
        self.product_idx = {'Factory0':['P1'],'Factory1':['P2','P12'],'Factory2':['P3','P23'],'Factory3':['P4']}
        self.product_trans = {'Factory0':['P1'],'Factory1':['P2','P12'],'Factory2':['P3','P23'],'Factory3':[]}
        self.transport_idx = {'P1':'Factory1',
                              'P2':'Factory2','P12':'Factory2',
                              'P3':'Factory3','P23':'Factory3'}
    
    def produce_load(self) -> None:
        '''
        Produce new product in all factories
        '''
        # Continue loading
        for tmp_lorry in self.lorry:
            if tmp_lorry.state == 'loading':
                for tmp_factory in self.factory:
                    if tmp_factory.id == tmp_lorry.position:
                        tmp_result = tmp_factory.load_cargo(tmp_lorry,tmp_lorry.product)
                        if tmp_result == 'full':
                            tmp_lorry.delivery(self.transport_idx[tmp_lorry.product])



        for tmp_factory in self.factory:
            tmp_factory.produce_product()
            for tmp_lorry in self.lorry:
                tmp_factory.unload_cargo(tmp_lorry)
            # Start loading the product to lorry.
            # Only when the product is enough to full the lorry
            tmp_product = self.product_idx[tmp_factory.id]
            lorry_pool = [lorry for lorry in self.lorry if lorry.position == tmp_factory.id and lorry.state == 'waitting']
            lorry_duplicate = [lorry.product for lorry in self.lorry if lorry.position == tmp_factory.id and lorry.state == 'loading']
            for item in tmp_product:
                # print(item not in lorry_duplicate)
                if (tmp_factory.container.loc[item,'storage']/0.05 > 100) and (item not in lorry_duplicate) and (len(lorry_pool)>0):
                    tmp_factory.load_cargo(lorry_pool[0],item)
                    



    
    def lorry_manage(self) -> None:
        s1 = np.zeros(len(self.factory))
        s2 = 0*np.eye(len(self.factory))
        s3 = np.zeros(len(self.factory))

        s3_pool = s3

        lorry_count = np.array([i.position for i in self.lorry])
        n_lory = {'Factory0':np.count_nonzero(lorry_count=='Factory0'),
                  'Factory1':np.count_nonzero(lorry_count=='Factory1'),
                  'Factory2':np.count_nonzero(lorry_count=='Factory2'),
                  'Factory3':np.count_nonzero(lorry_count=='Factory3')}
        for m in range(len(self.factory)):
            # Calculate s1
            tmp_factory = self.factory[m]
            tmp_product = self.product_trans[tmp_factory.id]
            if len(tmp_product) > 0:
                tmp_storage = tmp_factory.container.loc[tmp_product,'storage'].max()
                s1[m] = self.p[0] * min(tmp_storage,self.lorry[0].capacity)
            else:
                s1[m] = 0

            # Calculate s2
            # Get data from dataframe
            tmp_material = tmp_factory.product['material'].values
            tmp_ratio = tmp_factory.product['ratio'].values
            # Data processing, generate the list of material
            tmp_material = np.array([i.split(',') for i in tmp_material if type(i) is str]).flatten()
            tmp_ratio = np.array([i.split(',') for i in tmp_ratio if type(i) is str],dtype=np.float64).flatten()

            tmp_material, tmp_idx = np.unique(tmp_material,return_index=True)
            tmp_ratio = tmp_ratio[tmp_idx]
            for j in range(tmp_material.shape[0]):
                tmp_m = tmp_material[j]
                factory_idx = int([i for i in self.product_idx for item in self.product_idx[i] if item==tmp_m][0][-1])
                product_slice = tmp_factory.product[tmp_factory.product['material'].str.contains(tmp_m) == True]
                s2[m,factory_idx] += self.p[1]*(tmp_factory.container.loc[tmp_m,'storage'] - product_slice.iloc[0]['rate']*tmp_ratio[j]*self.et)
            # sum of each row
            # s2 = np.sum(s2,axis=1)

            # Calculate s3
            s3[m] = -n_lory[tmp_factory.id] * self.p[2]
            s3_pool[m] = -(n_lory[tmp_factory.id]-1) * self.p[2]
        
        s2 = np.sum(s2,axis=1)
        s = s1 + s2 + s3
        # Generate the lorry pool
        s_pool = (s1 + s2 + s3_pool<0)
        # lorry in the factory_idx could be assigned
        factory_idx = [self.factory[i].id for i in np.where(s_pool==True)[0]]
        lorry_pool = [i for i in self.lorry if i.position in factory_idx and i.state == 'waitting']

        # Assign the lorry
        # print(s)
        if np.max(s) >0 and len(lorry_pool) >0 :
            factory_assign = self.factory[np.argmax(s)].id
            c = np.zeros(len(lorry_pool))
            for i in range(len(lorry_pool)):
                tmp_lorry = lorry_pool[i]
                tmp_des = tmp_lorry.destination
                traci.vehicle.changeTarget(vehID=tmp_lorry.id,edgeID=factory_assign)
                c[i] = traci.vehicle.getDrivingDistance(vehID=tmp_lorry.id, edgeID=factory_assign,pos=0)
                traci.vehicle.changeTarget(vehID=tmp_lorry.id,edgeID=tmp_des)
            
            print(f'Assign {lorry_pool[c.argmax()].id} to {factory_assign}')
            lorry_pool[c.argmax()].delivery(destination=factory_assign)
            




