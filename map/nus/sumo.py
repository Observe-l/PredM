import traci

if __name__ == "__main__":
    # traci.start(['sumo','--threads','8',],port=19856)
    # a = traci.connect(port=19856, host="atlas9.nus.edu.sg")
    # a.close()
    traci.init(port=19856,host="atlas9.nus.edu.sg")

    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
    
    