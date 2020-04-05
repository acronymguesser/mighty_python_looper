import pyaudio # http://people.csail.mit.edu/hubert/pyaudio/
import wave
import time
import numpy as np
import math

CHUNK = 44100
FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 44100
SAMPLE_SIZE = pyaudio.get_sample_size(FORMAT)
LATENCY_COMPENSATION = 2048 * 6 * SAMPLE_SIZE
LOOP_SIZE_FRAMES = 88200
LOOP_SIZE_SAMPLES = LOOP_SIZE_FRAMES * CHANNELS
LOOP_SIZE_BYTES = LOOP_SIZE_SAMPLES * SAMPLE_SIZE
RECORD_LOOP_COUNT = 6 # Total loops that will be recorded. After this is reached, no data will be available for new loop playback.

playback_position = 0
recording_position = 0
recording_wave_data = bytearray(LOOP_SIZE_BYTES * RECORD_LOOP_COUNT)
playback_wave_data = bytearray()
command_exit = False

wrecord = wave.open("record.wav", 'wb')
wrecord.setnchannels(CHANNELS)
wrecord.setsampwidth(SAMPLE_SIZE)
wrecord.setframerate(RATE)

wplayback = wave.open("playback.wav", 'wb')
wplayback.setnchannels(CHANNELS)
wplayback.setsampwidth(SAMPLE_SIZE)
wplayback.setframerate(RATE)

class FilePlaybackDefinition:
  def __init__(self, file_name, play_from, play_at, play_times):
    self.file_name = file_name
    self.play_from = play_from
    self.play_at = play_at
    self.play_times = play_times
    
    self.play_from_frames = self.play_from * LOOP_SIZE_FRAMES
    self.play_from_bytes = self.play_from * LOOP_SIZE_BYTES

    with wave.open(self.file_name, 'rb') as w:
      if w.getnchannels() != 2 or w.getsampwidth() != 2:
        raise Exception("Only 16-bit stereo files supported.")

      available_frames = min( w.getnframes() - self.play_from_frames, LOOP_SIZE_FRAMES )
      available_bytes = available_frames * CHANNELS * SAMPLE_SIZE

      self.wave_data = bytearray(LOOP_SIZE_BYTES)
      self.wave_data[0:available_bytes] = w.readframes(self.play_from_frames + available_frames)[self.play_from_bytes:self.play_from_bytes + available_bytes]

  def get_loop_wave_data(self):
    return self.wave_data

class RecordPlaybackDefinition:
  def __init__(self, play_from, play_at, play_times):
    self.play_from = play_from
    self.play_at = play_at
    self.play_times = play_times
    self.wave_data = bytearray(LOOP_SIZE_BYTES)

    self.filled = False # set to true when certain that the wave data can be fully reused
    self.play_from_bytes = self.play_from * LOOP_SIZE_BYTES

  def get_loop_wave_data(self):

    global recording_position
    global recording_wave_data

    if self.filled:
      return self.wave_data

    if recording_position < self.play_from_bytes:
      return self.wave_data # still zeros

    available_bytes = min( recording_position - self.play_from_bytes, LOOP_SIZE_BYTES )

    self.wave_data[0:available_bytes] = recording_wave_data[self.play_from_bytes:self.play_from_bytes + available_bytes]

    if available_bytes >= LOOP_SIZE_BYTES:
      self.filled = True

    return self.wave_data

playback_definition_list = []

# SETUP INITIAL COUNT
playback_definition_list = [
  FilePlaybackDefinition('click_120bpm.wav', play_from=0, play_at=0, play_times=99),
  FilePlaybackDefinition('layer1.wav', play_from=1, play_at=1, play_times=1),
  FilePlaybackDefinition('layer1.wav', play_from=2, play_at=2, play_times=99),
  RecordPlaybackDefinition(play_from=1, play_at=3, play_times=99)
  # RecordPlaybackDefinition(play_from=3, play_at=4, play_times=99)
]

p = pyaudio.PyAudio()

def audio_stream_callback(in_data, frame_count, time_info, status_flags):
  global playback_position
  global recording_position
  global recording_wave_data
  global playback_wave_data
  global command_exit

  if command_exit:
    return (bytes(), pyaudio.paComplete)

  # a = time.perf_counter()

  # APPEND RECORD

  recording_position = ( playback_position * SAMPLE_SIZE ) - LATENCY_COMPENSATION

  if recording_position < len(recording_wave_data):

    if recording_position < 0 and recording_position + len(in_data) > 0:
      # discard data before 0
      in_data = in_data[:-(recording_position + len(in_data))]
      recording_position = 0

    if recording_position + len(in_data) > len(recording_wave_data):
      in_data = in_data[recording_position + len(in_data) - len(recording_wave_data):]

    if recording_position >= 0 and len(in_data) > 0:
      recording_wave_data[recording_position:recording_position + len(in_data)] = in_data
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
        if loop_wave_data:

          loop_wave_data = np.frombuffer(
            loop_wave_data[loop_def.loop_start * SAMPLE_SIZE:loop_def.loop_end * SAMPLE_SIZE],
            dtype=np.uint16
          )

          loop_wave_data_list.append(loop_wave_data)

    if len(loop_wave_data_list):
      loop_def.loop_wave_data = np.sum(loop_wave_data_list, axis=0, dtype=np.uint16)
    else:
      loop_def.loop_wave_data = np.zeros(loop_def.loop_end - loop_def.loop_start, dtype=np.uint16)

    out_wave_data = np.concatenate([out_wave_data, loop_def.loop_wave_data])

  playback_position = playback_position + total_samples_to_playback

  out_wave_data_bytes = bytes(out_wave_data)

  playback_wave_data += out_wave_data_bytes

  # b = time.perf_counter()
  # print (b - a)

  return (out_wave_data_bytes, pyaudio.paContinue)

stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, output=True, input=True, stream_callback=audio_stream_callback)
stream.start_stream()

input()
command_exit = True

while stream.is_active():
  time.sleep(0.1)

stream.stop_stream()
stream.close()

wrecord.writeframes(recording_wave_data)
wrecord.close()

wplayback.writeframes(playback_wave_data)
wplayback.close()

p.terminate()