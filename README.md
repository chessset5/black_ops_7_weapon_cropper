This script was created to find weapons in Black Ops 7 using the default hub with a video resolution of 1920x1080.

It is not perfect and it scrappy.

Note if using steam background recording, first turn it into a video.
You can find the background recordings here:
`C:\Program Files (x86)\Steam\userdata\<user id>\gamerecordings\video`

Find the session.mpd file, example:
`C:\Program Files (x86)\Steam\userdata\<user id>\gamerecordings\video\bg_1938090_20260917_000457\session.mpd`

In the same folder/directory run the ffmpeg command:
`ffmpeg -i session.mpd -c copy output.mp4`

Use that `output.mp4` in the program to find the weapon in question.
