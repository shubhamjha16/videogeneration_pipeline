import cv2
import os

def record_user_face(output_path="media/user_face.mp4", duration_seconds=10):
    """
    Helper script to record a short snippet of the user's face to use as a base for Lip-Sync.
    """
    print(f"🎬 Starting camera for {duration_seconds} seconds...")
    print("💡 TIP: Look directly at the camera and keep a neutral or friendly expression.")
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Error: Could not open camera.")
        return False

    # Get camera properties
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = 30 # Default

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    frames_to_record = duration_seconds * fps
    count = 0
    
    while count < frames_to_record:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Mirror for user convenience
        display_frame = cv2.flip(frame, 1)
        cv2.imshow('Recording... (Press Q to stop early)', display_frame)
        
        out.write(frame)
        count += 1
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    out.release()
    cv2.destroyAllWindows()
    
    if os.path.exists(output_path):
        print(f"✅ Recording saved to: {output_path}")
        return True
    return False

if __name__ == "__main__":
    if not os.path.exists("media"):
        os.makedirs("media")
    record_user_face()
