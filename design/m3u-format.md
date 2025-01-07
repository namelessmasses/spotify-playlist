# M3U Format 

- https://docs.fileformat.com/audio/m3u/
- https://en.wikipedia.org/wiki/M3U

# Overview

- Not a standard format.
- Line based file locations.
  - Local absolute path.
  - Local relative (to the M3U file) path.
  - Remote URL.
- '#' based metadata for #EXTM3U
- #EXTINF track metadata.
    - Track length in seconds.
    - Track display title.
- #PLAYLIST playlist title.

# Initial assumptions

- The system shall assume that all tracks have `#EXTINF` metadata.
- The system shall process a `#PLAYLIST` metadata entry and use its value as the playlist title, if one exists.

# Processing

1. The system shall Read the file line by line.
1. The system shall reject the file if the first line is not `#EXTM3U`.
1. The system shall use the `#PLAYLIST` metadata entry as the playlist title.
1. The system shall use each `#EXTINF` metadata entry as a track.
1. The system shall use the track title as the search query.
1. The system shall parse the track title as `#EXTINF:track_length and key-value properties,track_title`.