# %%
import numpy as np
import matplotlib.pyplot as plt
import os
import glob
from typing import List, Dict, Tuple
from tqdm import tqdm
from scipy import fft, signal
import pickle
from scipy.io.wavfile import read
from scipy.signal import resample
import librosa

# %%
from create_constellations import create_constellation
from create_hashes import create_hashes

# %%
songs = glob.glob('data/*.wav')

song_index = {}
database: Dict[int, List[Tuple[int, int]]] = {}
Fs_new = 16000

for index, filename in enumerate(tqdm(sorted(songs))):
    song_index[index] = filename
    #Fs, audio_input = read(filename)
    audio_input, Fs = librosa.load(filename, sr=12000) #down sample to 12k

    #num_samples = int(len(audio_input) * Fs_new / Fs)
    #audio_resampled = resample(audio_input, num_samples)
    #Fs = Fs_new
    if audio_input.ndim > 1: #make the data single channel mono
        audio_input = np.mean(audio_input, axis=1)

    constellation = create_constellation(audio_input, Fs)
    hashes = create_hashes(constellation, index)
    for hash, time_index_pair in hashes.items():
        if hash not in database:
            database[hash] = []
        database[hash].append(time_index_pair)
# %%
with open("database.pickle", 'wb') as db:
    pickle.dump(database, db, pickle.HIGHEST_PROTOCOL)
with open("song_index.pickle", 'wb') as songs:
    pickle.dump(song_index, songs, pickle.HIGHEST_PROTOCOL)
