import socket, struct
import sounddevice as sd
import threading
import time
import numpy as np
from scipy.signal import resample_poly
import numpy as np
import pickle
from scipy import fft, signal
from scipy.io.wavfile import read
from create_constellations import create_constellation
from create_hashes import create_hashes
import librosa
import time
import keyboard
import cv2
import matplotlib.pyplot as plt

# from scipy.signal import get_window


# ===== Socket & audio config =====
HOST = "0.0.0.0" 
PORT = 50007
SAMPLE_RATE = 48000
CHANNELS = 1
PLAYBACK_BLOCKSIZE = 2048
# =================================


# ===== Model / inference config =====
TARGET_SR = 12000
WIN_SECONDS = 1.0
VOTE_LEN = 8                 # smoothing window
CONF_MIN = 0.85              # "no decision" below this
PRINT_EVERY = 0.5            # seconds between prints (approx; controlled by deque fill)
# ====================================


# ===== Adaptive RMS VAD config =====
RMS_MULTIPLIER = 1.25         # factor above noise floor
ALPHA_UP = 0.1                # smoothing for noise floor update
ALPHA_DOWN = 0.07
noise_floor = 0.04            # global adaptive noise baseline
calibrate = True              # flag to mark initial calibration
calibration_rms = []
vad = False
HANGOVER_SEC = 0.3            # stay in vad this long after it drops quiet
HANGOVER = int(round(HANGOVER_SEC / PRINT_EVERY))
hang = 0
# ====================================


# def band_rms(x, fs, f_low=1000, f_high=8000):
#     """Return RMS energy in [f_low, f_high] Hz band."""
#     N = len(x)
#     # Hann window to reduce leakage
#     win = get_window('hann', N)
#     X = np.fft.rfft(x * win)
#     freqs = np.fft.rfftfreq(N, 1/fs)
#     band = (freqs >= f_low) & (freqs <= f_high)
#     power = np.mean(np.abs(X[band])**2)
#     return np.sqrt(power / np.sum(win**2

def score_songs(hashes,database):
    matches_per_song = {}
    for hash, (sample_time, _) in hashes.items():
        if hash in database:
            matching_occurences = database[hash]
            for source_time, song_index in matching_occurences:
                if song_index not in matches_per_song:
                    matches_per_song[song_index] = []
                matches_per_song[song_index].append((hash, sample_time, source_time))
            

    # %%
    scores = {}
    for song_index, matches in matches_per_song.items():
        song_scores_by_offset = {}
        for hash, sample_time, source_time in matches:
            delta = source_time - sample_time
            if delta not in song_scores_by_offset:
                song_scores_by_offset[delta] = 0
            song_scores_by_offset[delta] += 1

        max = (0, 0)
        for offset, score in song_scores_by_offset.items():
            if score > max[1]:
                max = (offset, score)
        
        scores[song_index] = max

    # Sort the scores for the user
    scores = list(sorted(scores.items(), key=lambda x: x[1][1], reverse=True)) 
    
    return scores

def display_Image(lock):
    global displayImg
    global audioVolume
    global recordingGlobal

    volumeScale = 1000

    while True:
        with lock:
            img = displayImg
            volume = audioVolume
        if img is not None:
            imgSize = cv2.resize(img, (400, 400))
            # Overlay text on image
            if (recordingGlobal == True):
                text = f"Currently Recording..."
                colour = (0, 0, 255) #red
                cv2.putText(imgSize, text, (5, 15),cv2.FONT_HERSHEY_SIMPLEX, 0.5, colour, 1, cv2.LINE_AA)
            else:
                text = f"Waiting on Recording..."
                colour = (0, 255, 0) #green
                cv2.putText(imgSize, text, (5, 15),cv2.FONT_HERSHEY_SIMPLEX, 0.5, colour, 1, cv2.LINE_AA)
                volume = np.minimum(volume*volumeScale,100)
                textVolume = f"Average Volume:{volume:.2f}"
                cv2.putText(imgSize, textVolume, (5, 45),cv2.FONT_HERSHEY_SIMPLEX, 0.5, colour, 1, cv2.LINE_AA)

            cv2.imshow("Classifier Results",imgSize)
        if cv2.waitKey(30)==27:
            break
        time.sleep(0.2)
    cv2.destroyAllWindows()



def classify_audio(audio_data_copy, lock, sound_index_lookup, database, images):
    # This function takes in the recorded audio array, prepares it to then compute the hashes and volume. 
    # Then it updates the image to display and volume based on the result 
    global displayImg, recordingGlobal, audioVolume

    audioInput = audio_data_copy.astype(np.float32) / 32768.0

    audioInput = librosa.resample(audioInput, orig_sr=SAMPLE_RATE, target_sr=TARGET_SR)
    constellation = create_constellation(audioInput, TARGET_SR)
    hashes = create_hashes(constellation, None)
    scores = score_songs(hashes, database)
    bestScoreID, bestScore = scores[0]
    bestAnimal = sound_index_lookup[bestScoreID][5:-5]
    volume = librosa.feature.rms(y=audioInput, S=TARGET_SR).mean()

    with lock:
        displayImg = images[bestAnimal]
        recordingGlobal = False # Tells the display script if to display blank image or animal
        audioVolume = volume


def main():
    global displayImg
    global audioVolume
    global recordingGlobal

    displayImg = None
    recordingGlobal = False
    audioVolume = 0.0
    recording = False
    audioBuffer = []
    showPlot = 0 # Change to 1 to display a spectrogram plot of the recorded audio

    lock = threading.Lock()
    threading.Thread(target=display_Image, args=(lock,), daemon=True).start()

    # TCP Connection Setup
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen(1)
    print(f"[Server] Listening on {HOST}:{PORT} ...")
    conn, addr = s.accept()
    print(f"[Server] Client connected from {addr}")
    
    images = { #dictionary of image titles and locations
        "Bat": cv2.imread("images/bat.jpg"),
        "FrogmouthTawny": cv2.imread("images/frogmouthtawny.jpg"),
        "Snake": cv2.imread("images/snake.jpg"),
        "Cockatoo": cv2.imread("images/cockatoo.jpg"),
        "Crocodile": cv2.imread("images/crocodile.jpg"),
        "Dingo": cv2.imread("images/dingo.jpg"),
        "Duck": cv2.imread("images/duck.jpg"),
        "Frog": cv2.imread("images/frog.jpg"),
        "Koala": cv2.imread("images/koala.jpg"),
        "Kookaburra": cv2.imread("images/kookaburra.jpg"),
        "Magpie": cv2.imread("images/magpie.jpg"),
        "Platypus": cv2.imread("images/platypus.jpg"),
        "Possum": cv2.imread("images/possum.jpg"),
        "Wombat": cv2.imread("images/wombat.jpg"),
        "Black": cv2.imread("images/Black.jpg")
    }

    #load database
    database = pickle.load(open('database.pickle', 'rb'))
    sound_index_lookup = pickle.load(open("song_index.pickle", "rb"))

    with sd.OutputStream(samplerate=SAMPLE_RATE,
                            channels=CHANNELS,
                            dtype='int16',
                            blocksize=PLAYBACK_BLOCKSIZE) as stream:
        
        try:
            print('Press "p" to start/stop recording:')
            while True:
                if keyboard.is_pressed('p'):
                    recording = not recording
                    if recording:
                        print("Recording has started.")
                        audioBuffer = []
                        with lock:
                            displayImg = images["Black"]
                            recordingGlobal = True
                    elif (recording == False):
                        print("Recording stopped.")
                        if len(audioBuffer) > 0:
                            playbackData = np.concatenate(audioBuffer)
                            if (showPlot == 1):
                                # Compute Short-Time Fourier Transform (STFT)
                                audioInput = playbackData.astype(np.float32) / 32768.0
                                D = librosa.stft(audioInput)
                                # Convert amplitude to decibels
                                S_db = librosa.amplitude_to_db(abs(D), ref=np.max)
                                plt.figure(figsize=(12, 4))
                                librosa.display.specshow(S_db, sr=48000, x_axis='time', y_axis='log')
                                plt.colorbar(format='%+2.0f dB')
                                plt.title("Spectrogram (dB)")
                                plt.show()

                            threading.Thread(target=classify_audio, args=(playbackData.copy(), lock, sound_index_lookup, database, images),daemon=True).start()
                        else:
                            print("No audio was recorded... sad!")

                    while keyboard.is_pressed('p'):
                        time.sleep(0.2) #avoid double presses

                # First read 4-byte length header
                header = b''
                while len(header) < 4:
                    chunk = conn.recv(4 - len(header))
                    if not chunk:
                        print("[Client] Server disconnected")
                        return
                    header += chunk
                (length,) = struct.unpack("!I", header)

                # Then read 'length' bytes of audio
                audio_data = b''
                while len(audio_data) < length:
                    chunk = conn.recv(length - len(audio_data))
                    if not chunk:
                        print("[Client] Server disconnected")
                        return
                    audio_data += chunk

                # Convert bytes back to int16 numpy array
                pcm = np.frombuffer(audio_data, dtype=np.int16)

                # Play audio
                stream.write(pcm)

                # Generate recording array
                if recording:
                    audioBuffer.append(pcm)
                    
        except KeyboardInterrupt:
            print("\n[Server] shutting down")    
        finally:
            conn.close()
            s.close()            


if __name__ == "__main__":
    main()