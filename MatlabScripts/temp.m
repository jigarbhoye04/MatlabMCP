% Parameters for the sine wave
amplitude = 1; % Amplitude of the sine wave
frequency = 5; % Frequency in Hz
samplingRate = 100; % Sampling rate in Hz
duration = 2; % Duration in seconds

% Time vector
t = 0:1/samplingRate:duration;

% Sine wave
y = amplitude * sin(2 * pi * frequency * t);

% Plot the sine wave
figure;
plot(t, y);
xlabel('Time (s)');
ylabel('Amplitude');
title('Sine Wave');
grid on;