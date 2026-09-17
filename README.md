# Black Ops 7 Weapon Finder

This script was created to find weapons in Black Ops 7 using the default hub with a video resolution of 1920x1080.

## Background

I picked up a sniper in a game and made a clip. I forgot to mark the clip in steam background recording.

I generated a script that finds the weapons used in the match and has them exported to a folder.

## How it works

With a video of resolution 1920x1080;

The script looks at the weapon hud at the bottom left of the screen and finds grey  pixels

It crops to the weapon wheel and poorly attempts to limit duplicates by checking the previous frame for a match.

It is not perfect and it scrappy.

*This script might also work for other resolutions of clip, but you will need to modify the CROP_Y1, CROP_Y2
CROP_X1, CROP_X2 values*

## Note on preparing the steam background recording

Note if using steam background recording, first turn it into a video.
You can find the background recordings here:
`C:\Program Files (x86)\Steam\userdata\<user id>\gamerecordings\video\`

Find the session.mpd file, example:
`C:\Program Files (x86)\Steam\userdata\<user id>\gamerecordings\video\bg_1938090_20260917_000457\session.mpd`

In the same folder/directory run the ffmpeg command:
`ffmpeg -i session.mpd -c copy output.mp4`

Use that `output.mp4` in the program to find the weapon in question.

## Requirements

`Python 12+`

Library manager `uv`

Run `uv sync` to get started
*or what ever command your python manager uses to synchronize an environment with the `pyproject.toml`*

# Use of AI

If you wish to see the gemini chat to see my train of thought, please see the `./gemini chat/` folder.
