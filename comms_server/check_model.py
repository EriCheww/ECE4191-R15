from ultralytics import YOLO
m = YOLO("best.pt")
r = m.predict("test.jpg", conf=0.10, verbose=False)
print("classes:", m.names)
print("boxes:", len(r[0].boxes) if r else 0)
