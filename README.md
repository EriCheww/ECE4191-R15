# ECE4191-R15

[Unit]
Description=Python Auto Run on Boot
After=network.target

[Service]
ExecStart=/usr/bin/python3 /home/pi/myscript.py 
WorkingDirectory=/home/pi
StandardOutput=journal
StandardError=journal
Restart=no
User=pi

[Install]
WantedBy=multi-user.target
