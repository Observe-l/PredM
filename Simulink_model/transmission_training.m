% Code to generate data of commanded clutch states : transmission drive ratio
%% Function Description:
%
% generateTrainingData sweeps through the full-factorial set of all
% possible locked/unlocked clutch states of the transmission to collect
% the corresponding drive ratios. Injected clutch states override the
% model's Gear Command. generateTrainingData puts the model in Fast Restart
% mode to collect the data without recompiling the model in between
% iterations. generateTrainingData also sets the simulation stop time to 10
% second and the Velocity Source to a low constant speed to reduce
% execution time.
%
% The last column of the generated 2D matrix, clutch_DR_table, corresponds
% to the measured drive ratio, defined as transmission output rotational
% velocity / input rotational velocity. The remaining columns correspond to
% a set of clutch states, with each column corresponding to the clutches in
% alphabetical order. For the 7-speed Lepelletier transmission with 6
% clutches, columns 1-6 of clutch_DR_table correspond to clutches A, B, C,
% D, and E, respectively. A clutch state with a value of '0' represents an
% unlocked clutch, and a value '1' represents a clutch for which the
% control pressure is activated.
%
% If the clutch state is specified as '1', then it is still possible for
% the clutch to slip. This occurs for at least 1 clutch when a set of 
% clutch states is overconstrained. When the input flag,
% excludeStateswithSlippingClutches, is set to 1, the outputted table
% excludes states with activated control pressure that are slipping.

% Copyright 2021-2022 The MathWorks, Inc.

excludeStateswithSlippingClutches= 1;
clutch_DR_table = generateTrainingData(excludeStateswithSlippingClutches);

function clutch_DR_table = generateTrainingData(excludeStateswithSlippingClutches)
% Generate table of commanded clutch states : transmission drive ratios

% Obtain the full-factorial set of all possible locked/unlocked clutch states
numClutches= 6;
allClutchCombinations= dec2bin(0:(2^numClutches-1)) - '0';

% Get initial model configuration
model= 'transmission_fault_detection';
originalFaultInjection = get_param([model '/[A B C D E F]'], 'Value');
original_slope         = get_param([model, '/Velocity Source'], 'slope');
original_initial_speed = get_param([model, '/Velocity Source'], 'initial_speed');
original_final_speed   = get_param([model, '/Velocity Source'], 'final_speed');
original_StopTime      = evalin('base', 'Tend');

% Configure model for obtaining steady-state drive ratios
set_param(model,'FastRestart','on');
set_param([model, '/Velocity Source'], 'slope', '0.5');
set_param([model, '/Velocity Source'], 'initial_speed', '0.1');
set_param([model, '/Velocity Source'], 'final_speed', '1');
set_param([model, '/Gear Command'], 'Repeating_Sequence', '[-1:9]');
set_param([model, '/Gear Command'], 'sample_time', '4');
assignin('base', 'Tend', 10);

% Initialize vector of drive ratios for each state
DriveRatios_mat=zeros(length(allClutchCombinations), 1);

for i = 1:length(allClutchCombinations) 

    % Set clutch state
    clutchCombination= allClutchCombinations(i,:);
    set_param([model '/[A B C D E F]'], 'Value', mat2str(clutchCombination) );

    % Simulate transmission
    out= sim(model);

    % Get the drive ratio of this locked/unlocked clutch state
    DR_sig=  out.yout{2}.Values.Data;
    
    % Get index halfway through simulation
    ind_SS= round(length(DR_sig)/2);

    % Record mean DR of second half of simulation
    DriveRatio_current= mean(DR_sig(ind_SS:end));

    % If specified, indicate that this clutch state contains at least 1
    % clutches that is slipping when the control pressure is activated.
    % This likely indicates an overconstrained clutch state.
    if excludeStateswithSlippingClutches
        % Check if any cutches are slipping
        simlog= out.simlog_transmission_fault_detection;
        overConstrained= checkForOverConstraint('ABCDEF',clutchCombination, simlog, ind_SS);
        if overConstrained
            DriveRatio_current = inf;
        end
    end

    % store drive ratio in vector
    DriveRatios_mat(i) = round(DriveRatio_current, 6);
end

% Unpack the clutch state in each clutch state set
clutchA = allClutchCombinations(:,1);
clutchB = allClutchCombinations(:,2);
clutchC = allClutchCombinations(:,3);
clutchD = allClutchCombinations(:,4);
clutchE = allClutchCombinations(:,5);
clutchF = allClutchCombinations(:,6);

% Store measured drive ratio for each clitch state in a table
resultsTable = table(clutchA, clutchB, clutchC, clutchD, clutchE, clutchF, DriveRatios_mat);
resultsTable.Properties.VariableNames{'DriveRatios_mat'} = 'DriveRatio';

% Ignore overConstrained states if excludeStateswithSlippingClutches is enabled
validDriveRatiosInd = resultsTable.DriveRatio < inf;
resultsTableValid = resultsTable(validDriveRatiosInd,:);

% Output
clutch_DR_table= table2array(resultsTableValid);

% Reset model configuration
set_param( model,'FastRestart','off');
set_param([model '/[A B C D E F]'],    'Value',         originalFaultInjection);
set_param([model, '/Velocity Source'], 'slope',         original_slope);
set_param([model, '/Velocity Source'], 'initial_speed', original_initial_speed);
set_param([model, '/Velocity Source'], 'final_speed',   original_final_speed);
assignin('base', 'Tend', original_StopTime);

end

%--------------------------------------------------------------------------
function overConstrained= checkForOverConstraint(clutchNames, clutchCombination, simlog, ind_SS)
% Check for slipping clutches in the 7-Speed Lepelletier transmission.
% A clutch that should be locked is slipping if the clutch state command is
% locked, but the clutch state M indicates slip (-1 or 1)

    overConstrained= 0; % initial assumption

    for i= 1:length(clutchNames)
        clutch= clutchNames(i);
        clutch_command= clutchCombination(i);
        simulated_clutch_state= simlog.x7_Speed_Lepelletier.(['Clutch_' clutch]).fundamental_clutch.M.series.values('1');
        mean_clutch_state= mean(simulated_clutch_state(ind_SS:end));
        % If clutch is commanded to lock but it is not locked
        if clutch_command == 1 && mean_clutch_state ~= 0
            % Transmission is overconstrained
            overConstrained= 1;
        end
    end

end

