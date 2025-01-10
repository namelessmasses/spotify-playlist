#!/usr/bin/python3

import json


def convert(m3u_filename):
    '''
    1. The system shall Read the file line by line.
    1. The system shall reject the file if the first line is not `#EXTM3U`.
    1. The system shall use the `#PLAYLIST` metadata entry as the playlist title.
    1. The system shall use each `#EXTINF` metadata entry as a track.
    1. The system shall use the track title as the search query.
    1. The system shall parse the track title as `#EXTINF:track_length and key-value properties,track_title`.
    '''
    with open(m3u_filename, "r") as f:
        lines = f.readlines()

    lines = [line.strip() for line in lines if line.strip() and line.startswith("#")]

    if lines[0] != "#EXTM3U":
        raise ValueError("Invalid M3U file")
    
    tracks = []
    playlist_title = None
    
    for line in lines:
        if line.startswith("#PLAYLIST"):
            playlist_title = line.split(":")[1]
            continue
        
        if line.startswith("#EXTINF"):
            track_title = line.split(",")[1]
            tracks.append(track_title)
            
    if not tracks:
        raise ValueError("No tracks found")
    
    if not playlist_title:
        # Use the basename of the input filename as the playlist title
        playlist_title = '.'.join(m3u_filename.split("/")[-1].split(".")[:-1])
    
    # Create the JSON object
    # {
    #     "playlist_name": "Playlist Title",
    #     "playlist_tracks": [
    #         {
    #             "track_title": "Artist - Title"
    #         },
    #         ...
    #     ]
    # }
    playlist = {
        "playlist_name": playlist_title,
        "playlist_tracks": [{"track_title": track} for track in tracks]
    }
    
    # write out the JSON object to a file
    with open(f"{playlist_title}.json", "w") as f:
        f.write(json.dumps(playlist))
            

if __name__ == "__main__":
    import sys
    convert(sys.argv[1])
