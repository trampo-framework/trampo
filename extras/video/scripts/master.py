"""Two-pass loudnorm to -16 LUFS, true peak -1.5 dBTP. Run: python3 -I scripts/master.py out/music-raw.wav out/music.wav"""
import json
import subprocess
import sys

src, dst = sys.argv[1], sys.argv[2]
target = 'I=-16:TP=-1.5:LRA=11'
p = subprocess.run(['ffmpeg', '-hide_banner', '-i', src, '-af', f'loudnorm={target}:print_format=json', '-f', 'null', '-'],
                   capture_output=True, text=True, check=True)
err = p.stderr
d = json.loads(err[err.rindex('{'):err.rindex('}') + 1])
measured = (f"measured_I={d['input_i']}:measured_TP={d['input_tp']}:measured_LRA={d['input_lra']}"
            f":measured_thresh={d['input_thresh']}:offset={d['target_offset']}")
subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', src, '-af', f'loudnorm={target}:{measured}:linear=true',
                '-ar', '48000', dst], check=True)
print('input', d['input_i'], 'LUFS, true peak', d['input_tp'])
