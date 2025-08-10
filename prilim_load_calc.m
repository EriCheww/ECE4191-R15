%% Clear all, Close all, clc
clear all; close all; clc;

% All variables are in SI units

%% Define Variables 
% Constants
g = 9.81; % gravity

k_sf = 1; % Spring Constant of Spring Front (SF)
k_sm = 1; % Spring Constant of Spring Middle (SM)
k_sr = 1; % Spring Constant of Spring Rear (SR)

x_sf = 1; % Max SF travel distance
x_sm = 1; % Max SM travel distance
x_sr = 1; % Max SR travel distance 

preload_ratio_sf = 0.2; % Preload ratio of the SF
preload_ratio_sm = 0.2; % Preload ratio of the SM
preload_ratio_sr = 0.2; % Preload ratio of the SR

alpha_4 = 1; % Angle of the SF (radians)
alpha_5 = 1; % Angle of the SR (radians)
alpha_6 = 1; % Angle of the SM (radians)

% Friction Constants
friction_ratio = 0.2; % friction ratio of on the ground
contact_patch_area_ratio = 0.2; % Ratio of the total contact patch area 

d13 = 1; % Distance from W3 to W4
d14 = 1; % Distance from W4 to W5

% Motor Charecteristics
torque_motor = 1; % Output Motor Torque
r_w1 = 1; % Radius of the W1 Sprocket
gearbox_ratio = 1; % Motor Gearbox Ratio

% Mass
m_w1 = 1; % Mass of Wheel 1 (W1)
m_w2 = 1; % Mass of Wheel 2 (W2)
m_w3 = 1; % Mass of Wheel 3 (W3)
m_w4 = 1; % Mass of Wheel 4 (W4)
m_w5 = 1; % Mass of Wheel 5 (W5)

m_fsa = 1; % Mass of Front Swing Arm (FSA)
m_msa = 1; % Mass of Middle Swing Arm (MSA)
m_rsa = 1; % Mass of Rear Swing Arm (RSA)

m_msf = 1; % Mass of Main Sub-Frame (MSF)

m_sf = 1; % Mass of Spring Front (SF)
m_sm = 1; % Mass of Spring Middle (SM)
m_sr = 1; % Mass of Spring Rear (SR)

m_fastner = 1; % Total Mass of Fasteners on one half 
m_body = 1; % Mass of body and payload
m_treads = 1; % Mass of treads

% Sprung Mass
m_sprung = 2*(m_msf + m_w1 + m_sf + m_sm + m_sr + m_treads + m_fastner) + m_body; % Total Sprung Mass

% Total Mass
m_total = 2*(m_msf + m_w1 + m_w2 + m_w3 + m_w4 + m_w5 + m_fsa + m_msa + m_rsa + m_sf + m_sm + m_sr + m_treads + m_fastner) + m_body;

%% Forces
% Unsprung Forces 
F_usprung_w3 = (m_w3 + m_w2 + m_fsa)*g + k_sf*x_sf*sin(alpha_4)*preload_ratio_sf; % W3 Unsprung Forces
F_usprung_w4 = (m_w4 + m_msa)*g + k_sm*x_sm*cos(alpha_6)*preload_ratio_sm; % W4 Unsprung Forces 
F_usprung_w5 = (m_w5 + m_rsa)*g + k_sr*x_sr*sin(alpha_5)*preload_ratio_sr; % W5 Unsprung Forces

% Spung Forces 
F_sprung = 0.5*m_sprung*g; % Force from Half the Sprung Mass

% Friction Forces
F_fric_w3 = 0.5*friction_ratio*contact_patch_area_ratio*(F_usprung_w3 + F_sprung/3)*d13;
F_fric_w4 = 0.5*friction_ratio*contact_patch_area_ratio*(F_usprung_w4 + F_sprung/3)*(d13 + d14);
F_fric_w5 = 0.5*friction_ratio*contact_patch_area_ratio*(F_usprung_w5 + F_sprung/3)*d14;

% Driving Force
F_drive = 2*(gearbox_ratio*(torque_motor/r_w1) - (F_fric_w3 + F_fric_w4 + F_fric_w5));
acceleration_drive = F_drive/m_total