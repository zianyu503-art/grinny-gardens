"""Encode trailer frames (fNNNNN.jpg) + audio.wav into an H.264/AAC MP4 using Blender's built-in FFmpeg.

usage: blender -b --factory-startup --python tools/encode_video.py -- <frames_dir> <out.mp4> [fps]
"""
import os
import sys

import bpy

args = sys.argv[sys.argv.index("--") + 1:]
src, out = args[0], args[1]
fps = int(args[2]) if len(args) > 2 else 30
frames = sorted(f for f in os.listdir(src) if f.startswith("f") and f.endswith(".jpg"))

sc = bpy.context.scene
sc.render.resolution_x, sc.render.resolution_y = 1280, 720
sc.render.resolution_percentage = 100
sc.render.fps = fps
sc.frame_start, sc.frame_end = 1, len(frames)
ed = sc.sequence_editor_create()
strips = ed.strips if hasattr(ed, "strips") else ed.sequences
img = strips.new_image("frames", os.path.join(src, frames[0]), 1, 1)
for f in frames[1:]:
    img.elements.append(f)
wav = os.path.join(src, "audio.wav")
if os.path.exists(wav):
    strips.new_sound("audio", wav, 2, 1)

r = sc.render
if hasattr(r.image_settings, "media_type"):  # Blender 5: pick video output before the container
    r.image_settings.media_type = "VIDEO"
r.image_settings.file_format = "FFMPEG"
r.ffmpeg.format = "MPEG4"
r.ffmpeg.codec = "H264"
# VHS grain is expensive to compress: use a fixed bitrate instead of constant quality
r.ffmpeg.constant_rate_factor = "NONE"
r.ffmpeg.video_bitrate = 6000
r.ffmpeg.maxrate = 9000
r.ffmpeg.gopsize = 30
r.ffmpeg.ffmpeg_preset = "GOOD"
r.ffmpeg.audio_codec = "AAC"
r.ffmpeg.audio_bitrate = 192
r.ffmpeg.audio_channels = "STEREO"
r.ffmpeg.audio_mixrate = 48000
r.filepath = out
bpy.ops.render.render(animation=True)
print("ENCODED", out, len(frames), "frames")
