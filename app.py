import wave
import time
import looper

looper.initialize(loop_bpm=120, loop_duration_beat=4, record_loop_count=6)

# this module uses settings assigned during looper.initialize, so it must be called after it
playback_definition_list = __import__("playback_definitions").playback_definition_list
looper.set_playback_definition_list(playback_definition_list)

looper.start_stream()

input()
looper.exit_looper = True

while looper.is_active():
  time.sleep(0.1)

looper.stop_stream()

wrecord = wave.open("record.wav", 'wb')
wrecord.setnchannels(looper.CHANNELS)
wrecord.setsampwidth(looper.SAMPLE_SIZE)
wrecord.setframerate(looper.RATE)
wrecord.writeframes(looper.recording_wave_data)
wrecord.close()

wplayback = wave.open("playback.wav", 'wb')
wplayback.setnchannels(looper.CHANNELS)
wplayback.setsampwidth(looper.SAMPLE_SIZE)
wplayback.setframerate(looper.RATE)
wplayback.writeframes(looper.playback_wave_data)
wplayback.close()
