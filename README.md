# PredM
Predictive Maintenance

We integrated [SUMO](https://www.eclipse.org/sumo/) & Simulink & [OMNeT++](https://omnetpp.org/) to simulate the vehicle engine fault and factory machine engine fault.

### SUMO map

We use [open street map](https://sumo.dlr.de/docs/Tutorials/OSMWebWizard.html) to generate Singapore map and use the satellite background. The traffic duration is 86400 seconds(24 hours). We use the car-only network and didn't import any pedestrians.

The traffic density:

| type   | Through Traffic Factor | Count |
| ------ | ---------------------- | ----- |
| Cars   | 2                      | 2     |
| Trucks | 1                      | 1     |
| Bus    | 1                      | 1     |



![SG_south_gui_label](./figure/SG_south_gui_label.png)

There are 4 factories on the map: 

| no.       | location              |
| --------- | --------------------- |
| Factory 0 | Dairy Farm Walk       |
| Factory 1 | Defu South Street 1   |
| Factory 2 | Pasir Panjang Drive 3 |
| Factory 3 | Marina E Dr           |

### Simulink model

Because the vehicles' engine are too complicated, we only simulate Lepelletier Gear Set. We use the example model from Simulink which can be found at [Transmission Fault Detection Harness](https://www.mathworks.com/help/sdl/ug/transmission-fault-detection.html). There are 6 clutches which may get stuck or slip. We use the MDP model to represent the engine state transitions, the state will change every 480 seconds (8 minutes)

![MDP](./figure/MDP.png)

![Simulink_model](./figure/Simulink_model.png)

Each MDP state corresponding to a clutch fault state:

| MDP  | A              | B              | C              | D              | E              | F              | array                    |
| ---- | -------------- | -------------- | -------------- | -------------- | -------------- | -------------- | ------------------------ |
| 0    | No fault       | No fault       | No fault       | No fault       | No fault       | No fault       | [-1, -1, -1, -1, -1, -1] |
| 1    | Locked fault   | No fault       | No fault       | No fault       | No fault       | No fault       | [1, -1, -1, -1, -1, -1]  |
| 2    | No fault       | Locked fault   | Locked fault   | No fault       | No fault       | No fault       | [1, 1, -1, -1, -1, -1]   |
| 3    | No fault       | No fault       | No fault       | Locked fault   | Locked fault   | Unlocked fault | [-1, -1, -1, 1, 1, 0]    |
| 4    | Unlocked fault | Unlocked fault | No fault       | No fault       | Locked fault   | Locked fault   | [0, 0, -1, -1, 1, 1]     |
| 5    | Unlocked fault | Unlocked fault | Unlocked fault | Unlocked fault | Unlocked fault | Unlocked fault | [0, 0, 0, 0, 0, 0]       |

|          | # Goods / week                                               |
| -------- | ------------------------------------------------------------ |
| Baseline | No maintenance (breakdown: 1 day to repair)                  |
| Daily    | 4 hours everyday  (back to state 0), breakdown: 1 day to repair |
| PARL     | 4 hours (back to state 0), breakdown: 1 day to repair        |

