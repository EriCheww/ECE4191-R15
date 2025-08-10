%% Clear all, Close all, clc
clear all; close all; clc;

% All variables are in SI units
%Most values selected within a range of acceptable values
%actual values to be determined once model is complete

%% Define Variables 
% Constants
g = 9.81; % gravity


% Based on the scale of our car, most off the shelf RC spring-Damper units are as follows:
%1/16 scale RC shock (55-70mm) 0.3-0.8 N/ mm
%1/18 Scale RC buggy shocks (45-55mm) 0.25-0.6 N/mm
%As a starting point assuming shocks are approximately 0.5 N/mm (500 N/m)

k_sf = 500; % Spring Constant of Spring Front (SF)
k_sm = 500; % Spring Constant of Spring Middle (SM)
k_sr = 500; % Spring Constant of Spring Rear (SR)


%Given a 1/16 RC shock, given (manufacturer spec)
%Eye-to-eye at rest: ~60 mm
%Stroke: ~12 mm



x_sf = 12; % Max SF travel distance (directly from spec)
x_sm = 12; % Max SM travel distance
x_sr = 12; % Max SR travel distance 

%Preload travel = how much the spring (or suspension) is already compressed when the vehicle is at rest, before any extra load/movement.
%approximation 
preload_travel= 3;

%Maximum travel = total usable stroke before hitting bump stops or coil bind.
%preload ration= preload travel/max avaialbale travel

preload_ratio_sf = preload_travel/x_sf; % Preload ratio of the SF
preload_ratio_sm = preload_travel/x_sm; % Preload ratio of the SM
preload_ratio_sr = preload_travel/x_sr; % Preload ratio of the SR

%all approximations
alpha_4 = 2.3; % Angle of the SF (radians)
alpha_5 = pi/2; % Angle of the SR (radians)
alpha_6 = -0.39; % Angle of the SM (radians)

% Friction Constants
friction_ratio = 0.7; % friction ratio of on the ground
contact_patch_area_ratio = 0.35; % Ratio of the total contact patch area 

d13 = 0.1; % Distance from W3 to W4 (~100mm)
d14 = 0.1; % Distance from W4 to W5

% Motor Charecteristics
torque_motor = 1.2; % Output Motor Torque
r_w1 = 0.0258; % Radius of the W1 Sprocket
gearbox_ratio = 1; % Motor Gearbox Ratio, since torque_motor_out is AFTER gearbox

% Mass
m_w1 = 0.06; % Mass of Wheel 1 (W1) Idler
m_w2 = 0.05; % Mass of Wheel 2 (W2)
m_w3 = 0.05; % Mass of Wheel 3 (W3)
m_w4 = 0.06; % Mass of Wheel 4 (W4) Drive sprocket
m_w5 = 0.05; % Mass of Wheel 5 (W5)

m_fsa = 0.020; % Mass of Front Swing Arm (FSA)
m_msa = 0.020; % Mass of Middle Swing Arm (MSA)
m_rsa = 0.020; % Mass of Rear Swing Arm (RSA)

m_msf = 0.150; % Mass of Main Sub-Frame (MSF)

m_sf = 0.010; % Mass of Spring Front (SF)
m_sm = 0.010; % Mass of Spring Middle (SM)
m_sr = 0.010; % Mass of Spring Rear (SR)

m_fastner = 0.060; % Total Mass of Fasteners on one half 
m_body = 0.80; % Mass of body and payload
m_treads = 0.060; % Mass of treads

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