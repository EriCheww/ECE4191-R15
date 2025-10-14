# %%
import numpy as np
import matplotlib.pyplot as plt
import pickle
from scipy import fft, signal
from scipy.io.wavfile import read
from create_constellations import create_constellation
from create_hashes import create_hashes
import librosa
import time

#Fs, audio_input = read("Wombat.wav")
audio_input, Fs = librosa.load('Kookbara.wav', sr=12000)

startTime=time.time()
if audio_input.ndim > 1:
    audio_input = np.mean(audio_input, axis=1)

constellation = create_constellation(audio_input, Fs)
hashes = create_hashes(constellation, None)

# %%
database = pickle.load(open('database.pickle', 'rb'))
song_index_lookup = pickle.load(open("song_index.pickle", "rb"))


def score_songs(hashes):
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

scores = score_songs(hashes)
for song_index, score in scores:
    print(f"{song_index_lookup[song_index]=}: Score of {score[1]} at {score[0]}")

currentTime=time.time()
totalTime=currentTime-startTime
print(f"Time taken = {totalTime}")

# # %%
# song_scores_by_offset = {}
# for hash, sample_time, source_time in matches_per_song[0]:
#     delta = source_time - sample_time
#     if delta not in song_scores_by_offset:
#         song_scores_by_offset[delta] = 0
#     song_scores_by_offset[delta] += 1
# plt.scatter(song_scores_by_offset.keys(), song_scores_by_offset.values())


# %%
