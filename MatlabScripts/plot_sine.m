% Define the time vector
t = 0:0.1:2*pi; % From 0 to 2*pi with a step of 0.1

% Calculate the sine wave
y = sin(t);

% Create the plot
figure; % Create a new figure window
plot(t, y);

% Add labels and title
xlabel('Time (t)');
ylabel('Amplitude (sin(t))');
title('Sine Wave Plot');

% Add grid for better readability
grid on;

% Keep the plot window open until closed manually
% disp('Plot generated. Close the figure window to exit MATLAB.');
% pause; % This might not work well with -batch, depends on MATLAB version/setup
% Instead of pause, -batch usually exits after script completion.
% The plot window should remain open if MATLAB's graphics system allows it.
