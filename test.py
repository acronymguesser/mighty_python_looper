import pyaudio # http://people.csail.mit.edu/hubert/pyaudio/
import wave
import time
import numpy as np
import math

CHUNK = 44100
FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 44100
SAMPLE_SIZE = 2
LATENCY_COMPENSATION = 2048 * 6
LOOP_SIZE_FRAMES = 88200
LOOP_SIZE_SAMPLES = LOOP_SIZE_FRAMES * CHANNELS
LOOP_SIZE_BYTES = LOOP_SIZE_SAMPLES * SAMPLE_SIZE
RECORD_LOOP_COUNT = 6 # Total loops that will be recorded. After this is reached, no data will be available for new loop playback.

playback_position = 0
recording_position = 0
recording_wave_data = np.zeros(LOOP_SIZE_SAMPLES * RECORD_LOOP_COUNT, dtype=np.uint16)

class FilePlaybackDefinition:
  def __init__(self, file_name, play_at, play_times):
    self.file_name = file_name
    self.play_at = play_at
    self.play_times = play_times

    with wave.open(self.file_name, 'rb') as wclick:
      if wclick.getnchannels() != 2 or wclick.getsampwidth() != 2:
        raise Exception("Only 16-bit stereo files supported.")

      frames = wclick.getnframes()
      self.wave_data = np.frombuffer(wclick.readframes(frames), dtype=np.uint16)
      self.wave_data = np.take(self.wave_data, range(0, LOOP_SIZE_SAMPLES))

  def get_loop_wave_data(self):
    return self.wave_data

class RecordPlaybackDefinition:
  def __init__(self, play_from, play_at, play_times):
    self.play_from = play_from
    self.play_at = play_at
    self.play_times = play_times
    self.wave_data = np.zeros(LOOP_SIZE_SAMPLES, dtype=np.uint16)
    self.wave_data2 = bytearray(LOOP_SIZE_BYTES)

    self.filled = False # set to true when certain that the wave data can be fully reused
    self.play_from_samples = self.play_from * LOOP_SIZE_SAMPLES
    self.play_from_bytes = self.play_from_samples * SAMPLE_SIZE

  def get_loop_wave_data(self):

    global recording_position
    global recording_wave_data

    if self.filled:
      return self.wave_data

    if recording_position < self.play_from_samples:
      return self.wave_data # still zeros

    available_samples = min( recording_position - self.play_from_samples, LOOP_SIZE_SAMPLES )
    available_bytes = available_samples * SAMPLE_SIZE

    self.wave_data = np.frombuffer(
      recording_wave_data.tobytes()[self.play_from_bytes:self.play_from_bytes + available_bytes],
      dtype=np.uint16)

    if available_samples >= LOOP_SIZE_SAMPLES:
      self.filled = True

    return self.wave_data

playback_definition_list = []

# SETUP INITIAL COUNT
playback_definition_list = [
  FilePlaybackDefinition('click_120bpm.wav', play_at=0, play_times=99),
  RecordPlaybackDefinition(play_from=1, play_at=3, play_times=99)
  # RecordPlaybackDefinition(play_from=3, play_at=4, play_times=99)
]

p = pyaudio.PyAudio()

# streamr = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)

def click_callback(in_data, frame_count, time_info, status_flags):
  global playback_position
  global recording_position
  global recording_wave_data

  # APPEND RECORD

  in_data = np.frombuffer(in_data, dtype=np.uint16)

  recording_position = playback_position - LATENCY_COMPENSATION

  if recording_position < len(recording_wave_data):

    if recording_position < 0 and recording_position + len(in_data) > 0:
      # discard data before 0
      in_data = in_data[:-(recording_position + len(in_data))]
      recording_position = 0

    if recording_position + len(in_data) > len(recording_wave_data):
      in_data = in_data[recording_position + len(in_data) - len(recording_wave_data):]

    if recording_position >= 0 and len(in_data) > 0:
      np.put(
        recording_wave_data,
        range(recording_position, recording_position + len(in_data)),
        in_data)

      recording_position += len(in_data)

  # GENERATE PLAYBACK 

  out_wave_data = np.zeros(0, dtype=np.uint16)

  class LoopDef:
    def __init__(self, loopn, loop_start, loop_end):
      self.loopn = loopn
      self.loop_start = loop_start
      self.loop_end = loop_end
      self.loop_wave_data = np.zeros(self.loop_end - self.loop_start, dtype=np.uint16)

  loop_def_list = []

  total_samples_to_playback = frame_count * CHANNELS

  current_loop = LoopDef(
    loopn = math.floor( playback_position / LOOP_SIZE_SAMPLES ),
    loop_start = playback_position % LOOP_SIZE_SAMPLES,
    loop_end = min( ( playback_position % LOOP_SIZE_SAMPLES ) + total_samples_to_playback, LOOP_SIZE_SAMPLES )    
  )
  loop_def_list.append(current_loop)

  if math.floor( ( playback_position + total_samples_to_playback ) / LOOP_SIZE_SAMPLES ) > current_loop.loopn:
    next_loop = LoopDef(
      loopn = current_loop.loopn + 1,
      loop_start = 0,
      loop_end = total_samples_to_playback - ( current_loop.loop_end - current_loop.loop_start )
    )
    loop_def_list.append(next_loop)

  for loop_def in loop_def_list:

    loop_wave_data_list = []

    for playback_definition in playback_definition_list:

      if playback_definition.play_at <= loop_def.loopn and playback_definition.play_at + playback_definition.play_times > loop_def.loopn:

        loop_wave_data = playback_definition.get_loop_wave_data()
        if len(loop_wave_data) > 0:

          loop_wave_data = np.take(
            loop_wave_data,
            range( loop_def.loop_start, loop_def.loop_end ))

          loop_wave_data_list.append(loop_wave_data)

    if len(loop_wave_data_list):
      loop_def.loop_wave_data = np.sum(loop_wave_data_list, axis=0, dtype=np.uint16)
    else:
      loop_def.loop_wave_data = np.zeros(loop_def.loop_end - loop_def.loop_start, dtype=np.uint16)

    out_wave_data = np.concatenate([out_wave_data, loop_def.loop_wave_data])

  playback_position = playback_position + total_samples_to_playback

  return (out_wave_data, pyaudio.paContinue)

stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, output=True, input=True, stream_callback=click_callback)
stream.start_stream()

input()

stream.stop_stream()
stream.close()

p.terminate()