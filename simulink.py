import matlab.engine

eng = matlab.engine.start_matlab()
model= 'Simulink_model/sdl_transmission_fault_detection'
out = eng.sim(model)
print(out)