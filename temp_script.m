x = 0:0.1:2*pi; % Define the range for x
y1 = sin(x);    % Calculate the sine of x
y2 = cos(x);    % Calculate the cosine of x
plot(x, y1, x, y2); % Plot both sine and cosine waves
title('Sine and Cosine Waves'); % Add a title
xlabel('x');      % Add x-axis label
ylabel('Function Value'); % Add y-axis label
legend('sin(x)', 'cos(x)'); % Add a legend
grid on;        % Turn on the grid