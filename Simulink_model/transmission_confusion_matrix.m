% Code to plot confusion matrix for the clutch fault classifier used in
% sdl_transmission_fault_detection
%% Plot Description:
%
% This plot indicates the performance of a transmission  clutch fault
% classifier used to predict fault type and location. The faults can be
% unlocked (the clutch fails to engage when its control pressure is
% activated) or locked (the clutch fails to disengage when the control
% pressure is deactivated). The faults can occur in any of the
% clutches.
%
% The horizontal axis is the true injected fault. The vertical axis is the
% predicted fault, based on the fault class with the highest
% probability-like score.
%
% This script adjusts the Velocity Source and load damping to test how
% different scenarios affect the classifier accuracy.

% Copyright 2021-2022 The MathWorks, Inc.

% Reuse figure if it exists, else create new figure
if ~exist('h1_sdl_transmission_fault_detection', 'var') || ...
        ~isgraphics(h1_sdl_transmission_fault_detection, 'figure')
    h1_sdl_transmission_fault_detection = figure('Name', 'sdl_transmission_fault_detection');
end
figure(h1_sdl_transmission_fault_detection)
clf(h1_sdl_transmission_fault_detection)

generate_confusion_matrix(h1_sdl_transmission_fault_detection,...
    'sdl_transmission_fault_detection', 6)


function generate_confusion_matrix(hfigure, model, numClutches)

% Get initial model configuration
originalFaultInjection = get_param([model '/[A B C D E F]'], 'Value');
original_slope         = get_param([model, '/Velocity Source'], 'slope');
original_initial_speed = get_param([model, '/Velocity Source'], 'initial_speed');
original_final_speed   = get_param([model, '/Velocity Source'], 'final_speed');
original_StopTime      = evalin('base', 'Tend');
original_load_damper   = get_param([model, '/Damper'], 'D');

% Configure model for fast iterations
set_param(model,'FastRestart','on');

% Initialize table of (actual injected fault, predicted fault)
confusion_matrix= zeros(12,12);

% Test different scenarios for each actual fault
% Adjust the Velocity Source initial and final speeds
baseInitialSpeeds= [  0.1  10]; % [rpm]
baseFinalSpeeds=   [ 20   100]; % [rpm]

% Adjust the coefficient of the damper at the follower
loadDampers= [5 20]; % [Ns/m]


% Iterate through each fault type and location. The first half of the
% iteration are unlocked faults. The second half of the iterations are
% locked faults.
for i = 1:2*numClutches
    % Initialize the injectedFault vector. -1 indicates no fault
    injectedFault= -1*ones(1, numClutches);
    if i <= numClutches
        % inject an unlocked fault in clutch i
        injectedFault(i)= 0;
    else
        % inject a locked fault in clutch i-numClutches
        injectedFault(i-numClutches)= 1;
    end
    set_param([model '/[A B C D E F]'], 'Value', mat2str(injectedFault) );

    for j= 1:length(baseFinalSpeeds)

        % Configure base speed scenario
        baseMinSpeed= baseInitialSpeeds(j);
        baseMaxSpeed= baseFinalSpeeds(j);
        slope= (baseMaxSpeed - baseMinSpeed)/original_StopTime;
        set_param([model, '/Velocity Source'], 'initial_speed', num2str(baseMinSpeed));
        set_param([model, '/Velocity Source'], 'final_speed', num2str(baseMaxSpeed));
        set_param([model, '/Velocity Source'], 'slope', num2str(slope));
    
        for k= 1:length(loadDampers)

            % Adjust damping at the follower
            loadDamper= loadDampers(k);
            set_param([model, '/Damper'], 'D', num2str(loadDamper));

            % Simulate the model and get the final prediction
            out= sim(model);
            prediction= out.yout{1}.Values.Data(:,:,end);
        
            % Retain the highest scoring prediction for the scenario
            prediction_for_run= zeros(1,2*numClutches);
            [~, idx] = max( prediction );
            prediction_for_run(idx)= 1;
        
            % update table of (actual injected fault, predicted fault)
            confusion_matrix(i,:)= confusion_matrix(i,:) + prediction_for_run;

        end
    end
end

% Reset model configuration
set_param( model,'FastRestart','off');
set_param([model '/[A B C D E F]'],    'Value',         originalFaultInjection);
set_param([model, '/Velocity Source'], 'slope',         original_slope);
set_param([model, '/Velocity Source'], 'initial_speed', original_initial_speed);
set_param([model, '/Velocity Source'], 'final_speed',   original_final_speed);
assignin('base', 'Tend', original_StopTime);
set_param([model, '/Damper'], 'D',   original_load_damper);

% Plot results
figure(hfigure);
h= heatmap(confusion_matrix');
xlabel('Actual fault');
ylabel('Predicted fault');
title('Clutch Fault Detection Confusion Matrix');

% Axis labels
clutchLabels= {'Unlocked A', 'Unlocked B', 'Unlocked C', 'Unlocked D', 'Unlocked E', 'Unlocked F',...
    'Locked A', 'Locked B', 'Locked C', 'Locked D', 'Locked E', 'Locked F'};
h.XData= clutchLabels;
h.YData= clutchLabels;

end
