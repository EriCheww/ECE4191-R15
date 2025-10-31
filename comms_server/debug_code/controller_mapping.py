import pygame

pygame.init()
pygame.joystick.init()

# Initialize controller
if pygame.joystick.get_count() == 0:
    print("No controller connected!")
    exit()

js = pygame.joystick.Joystick(0)
js.init()
print(f"Detected controller: {js.get_name()}")
print(f"Number of buttons: {js.get_numbuttons()}")
print("Press buttons to see their indices (press ESC to quit)...\n")

running = True
while running:
    for event in pygame.event.get():
        # Exit on ESC
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            running = False
        
        # Detect button press
        if event.type == pygame.JOYBUTTONDOWN:
            print(f"Button {event.button} pressed")
        elif event.type == pygame.JOYBUTTONUP:
            print(f"Button {event.button} released")

pygame.quit()
