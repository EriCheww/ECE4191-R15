def main():
    import sys, select, time
    global last_key   # <-- needed because the UDP thread writes this

    print("\nL298N DC motor test\n")
    print("Controls:\n"
          "  w/s : both motors +/- speed\n"
          "  a/d : steer (A−/ B+ and A+/ B−)\n"
          "  Arrow ↑/↓ : big +/- to both\n"
          "  Arrow ←/→ : spin in place (A−/B+ and A+/B−)\n"
          "  x : stop (brake)\n"
          "  1/2 : test A/B solo (toggle), 3 : both\n"
          "  q : quit\n")

    # --- Try to init a joystick (only used if physically connected to the Pi) ---
    js = None
    if HAVE_PYGAME:
        try:
            pygame.init()
            pygame.joystick.init()
            if pygame.joystick.get_count() > 0:
                js = pygame.joystick.Joystick(0)
                js.init()
                print(f"PS4 controller detected on Pi: {js.get_name()}")
                print("Use Left Stick (LY=throttle, LX=turn). "
                      "L1: A-only, R1: B-only, Triangle: both, X: stop, Options: quit")
            else:
                print("No joystick found on Pi; falling back to keyboard/UDP controls.")
        except Exception as e:
            print(f"Joystick init error: {e}\nFalling back to keyboard/UDP.")

    # --- Motor objects created earlier: A, B ---
    mode = 3  # 1=A only, 2=B only, 3=both

    def set_by_mode(delta):
        if mode == 1:
            A.set_speed(A.speed + delta)
        elif mode == 2:
            B.set_speed(B.speed + delta)
        else:
            A.set_speed(A.speed + delta)
            B.set_speed(B.speed + delta)

    try:
        while True:
            if js is not None:
                # -------- Controller ON PI path --------
                pygame.event.pump()

                # Mode buttons
                if js.get_button(BTN_L1):  # A only
                    mode = 1
                elif js.get_button(BTN_R1):  # B only
                    mode = 2
                elif js.get_button(BTN_TRI):  # both
                    mode = 3
                if js.get_button(BTN_CROSS):  # stop
                    A.set_speed(0); B.set_speed(0)
                if js.get_button(BTN_OPTIONS):  # quit
                    break

                # Axes -> diff drive
                lx = js.get_axis(AX_LX)
                ly = js.get_axis(AX_LY)
                lx = 0 if abs(lx) < DEADZONE else lx
                ly = 0 if abs(ly) < DEADZONE else ly

                throttle = int(max(-1.0, min(1.0, -ly)) * 100)  # up=forward
                turn     = int(max(-1.0, min(1.0,  lx)) * 100)

                left_cmd  = max(-100, min(100, throttle - turn))
                right_cmd = max(-100, min(100, throttle + turn))

                if mode == 1:
                    A.set_speed(left_cmd)
                elif mode == 2:
                    B.set_speed(right_cmd)
                else:
                    A.set_speed(left_cmd)
                    B.set_speed(right_cmd)

            else:
                # -------- Keyboard/UDP path (your normal flow) --------
                # First prefer a UDP 'key' if present
                ch = last_key
                last_key = None

                # If no UDP, try a non-blocking keyboard read so UDP can still be processed
                if not ch:
                    # is there a byte waiting on stdin?
                    if select.select([sys.stdin], [], [], 0.01)[0]:
                        ch = getch()
                    else:
                        ch = None

                if ch:
                    if ch in ('q', 'Q'):
                        break
                    elif ch == '1':
                        mode = 1; print("\nMode: A only", end="")
                    elif ch == '2':
                        mode = 2; print("\nMode: B only", end="")
                    elif ch == '3':
                        mode = 3; print("\nMode: Both", end="")
                    elif ch == 'w':
                        set_by_mode(+STEP)
                    elif ch == 's':
                        set_by_mode(-STEP)
                    elif ch == 'x':
                        A.set_speed(0); B.set_speed(0)
                    elif ch == 'a':
                        A.set_speed(A.speed - STEP)
                        B.set_speed(B.speed + STEP)
                    elif ch == 'd':
                        A.set_speed(A.speed + STEP)
                        B.set_speed(B.speed - STEP)
                    elif ch == '\x1b[A':  # UP
                        set_by_mode(+BIG_STEP)
                    elif ch == '\x1b[B':  # DOWN
                        set_by_mode(-BIG_STEP)
                    elif ch == '\x1b[D':  # LEFT
                        A.set_speed(A.speed - BIG_STEP)
                        B.set_speed(B.speed + BIG_STEP)
                    elif ch == '\x1b[C':  # RIGHT
                        A.set_speed(A.speed + BIG_STEP)
                        B.set_speed(B.speed - BIG_STEP)

            print(f"\rA:{A.speed:+4d}%   B:{B.speed:+4d}% ", end="", flush=True)
            time.sleep(0.01)

    except KeyboardInterrupt:
        pass
    finally:
        print("\nExiting.")
        A.set_speed(0); B.set_speed(0)
