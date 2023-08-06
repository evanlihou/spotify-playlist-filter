from dotenv import load_dotenv
load_dotenv()
import os

import spotipy
from spotipy.oauth2 import SpotifyOAuth

from util import chunks

scope = "playlist-read-private playlist-modify-private"

incoming_playlist_id = os.environ['INCOMING_PLAYLIST_ID']
outgoing_playlist_id = os.environ['OUTGOING_PLAYLIST_ID']
spotify = spotipy.Spotify(client_credentials_manager=SpotifyOAuth(scope=scope))

results = spotify.playlist_items(
    incoming_playlist_id, limit=100,additional_types=['track'],
    fields="next,items(track(id,uri,name,album(id,name,genres),artists(id,name,genres)))")

items = results['items']
while results['next']:
    results = spotify.next(results)
    items.extend(results['items'])

good_tracks = []

print('Starting with', len(items), 'tracks')

features = {}
for chunk in chunks([i['track']['id'] for i in items], 100):
    results = spotify.audio_features(chunk)
    features.update({f['id']: f for f in results})

for item in items:
    # genres = []
    # artists = spotify.artists([a['id'] for a in item['track']['artists']])['artists']
    # for artist in artists:
    #     genres.extend(artist['genres'])
    # if 'classical' in '\t'.join(genres):
    #     continue
    track = item['track']

    if track['id'] not in features:
        print('WARN: Track', track['id'], 'does not have features. Excluding.')
        continue

    if features[track['id']]['instrumentalness'] > 0.4 or features[track['id']]['energy'] < 0.3:
        continue

    good_tracks.append(track['uri'])
    print(track['id'], ' - ', features[track['id']]['instrumentalness'], features[track['id']]['energy'], track['name'])

print('Ending with', len(good_tracks), 'tracks')

should_replace = input('Replace contents of playlist with these songs? (y/n)  ')
if should_replace == 'y':
    results = spotify.playlist_items(
        outgoing_playlist_id, limit=100,additional_types=['track'],
        fields="next,items(track(uri))")

    existing_items = results['items']
    while results['next']:
        results = spotify.next(results)
        existing_items.extend(results['items'])
    
    existing_items = [i['track']['uri'] for i in existing_items]
    
    tracks_to_remove = []
    tracks_to_add = []

    for track in good_tracks:
        if track not in existing_items:
            tracks_to_add.append(track)
    
    for track in existing_items:
        if track not in good_tracks:
            tracks_to_remove.append(track)
    
    print('Add', len(tracks_to_add), 'remove', len(tracks_to_remove))

    for tracks in chunks(tracks_to_add, 100):
        spotify.playlist_add_items(outgoing_playlist_id, tracks, None)
    
    for tracks in chunks(tracks_to_remove, 100):
        spotify.playlist_remove_all_occurrences_of_items(outgoing_playlist_id, tracks)

