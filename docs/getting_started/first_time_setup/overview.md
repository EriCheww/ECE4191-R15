# First Time Setup

This page guides users through the **first-time setup and initialization** of the R15 Wildlife Monitoring Rover.  

It focuses on preparing the system for operation — installing required software, configuring the network, and verifying communication between the onboard computer and the control laptop.

These steps are intended **only for the initial setup**. 

Once the system has been installed and configured, future sessions (such as daily operation or field deployment) will not require repeating this full process — only powering on and launching the control interface.

The setup process ensures that:

- All required hardware and software components are available and correctly connected.  
- The onboard Raspberry Pi and control computer are properly configured for communication.  
- Essential dependencies, such as Python, GStreamer, and Git, are installed and verified.  
- The network connection between the rover, router, and control computer is stable before first operation.  

Following this section prepares the R15 Rover for first-time initialization and ensures all future runs are **faster, more reliable, and ready for field operation**.

This guide is divided into three sections:

1. **Control Laptop Setup** – Installing required tools, configuring the GUI interface, and verifying communication with the rover.  
2. **Onboard Computer (Raspberry Pi Zero 2 W) Setup** – Installing the operating system, enabling SSH, and preparing software dependencies.  
3. **Optional Server Setup** – Setting up a relay or remote access server for extended-range or multi-client operation.
