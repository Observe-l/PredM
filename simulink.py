import matlab.engine
import numpy as np
import pandas as pd


if __name__ == "__main__":
    # Start MATLAB without UI
    eng = matlab.engine.start_matlab()
    # Start MATLAB with the desktop
    # eng = matlab.engine.start_matlab("-desktop")
    model= 'Simulink_model/transmission_fault_detection'
    mdl = 'transmission_fault_detection'
    # Open the Simulink model
    eng.open_system(model,nargout=0)
    # Configure model for Fast restart
    eng.set_param(mdl,'FastRestart','on',nargout=0)
    # Get simulation results
    out = eng.sim(mdl)
    
    # Get the drive ratio
    DR_idx = [{'type':'.','subs':'yout'},{'type':'{}','subs':[2]},{'type':'.','subs':'Values'},{'type':'.','subs':'Data'}]
    tmp_out = out
    for tmp_idx in DR_idx:
        tmp_out = eng.subsref(tmp_out,tmp_idx)
    DR_sig=  tmp_out

    # Get the 

    

    eng.quit()