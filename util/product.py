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
        s2 = np.zeros((len(self.factory),self.factory[0].container.shape[0]))
        s3 = np.zeros(len(self.factory))
        for tmp_factory in self.factory:
            # Calculate s1
            tmp_product = self.product_idx[tmp_factory.id]
            tmp_storage = tmp_factory.container.loc[tmp_product,'storage'].max()
            s1 = self.p[0] * min(tmp_storage,self.lorry[0].capacity)
            # Calculate s2
            