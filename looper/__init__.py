import pyaudio # http://people.csail.mit.edu/hubert/pyaudio/
import wave
import math
import numpy as np
from looper.settings import LooperSettings

FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 44100
SAMPLE_SIZE = pyaudio.get_sample_size(FORMAT)

playback_definition_list = []

def initialize(looper_settings):

  global LOOP_SIZE_FRAMES
  global LOOP_SIZE_SAMPLES
  global LOOP_SIZE_BYTES
  loop_seconds = ( 60.0 / looper_settings.loop_bpm ) * looper_settings.loop_duration_beats
  LOOP_SIZE_FRAMES = math.floor(loop_seconds * RATE)
  LOOP_SIZE_SAMPLES = LOOP_SIZE_FRAMES * CHANNELS
  LOOP_SIZE_BYTES = LOOP_SIZE_SAMPLES * SAMPLE_SIZE

  global RECORD_LOOP_COUNT
  RECORD_LOOP_COUNT = looper_settings.record_loop_count # Total loops that will be recorded. After this is reached, no data will be available for new loop playback.

  global playback_position
  global playback_wave_data
  global recording_position
  global recording_wave_data
  playback_position = 0
  playback_wave_data = bytearray()
  recording_position = 0
  recording_wave_data = bytearray(LOOP_SIZE_BYTES * RECORD_LOOP_COUNT)

  global exit_looper
  exit_looper = False

def set_playback_definition_list(pdl):
  global playback_definition_list
  playback_definition_list = pdl

def audio_stream_callback(in_data, frame_count, time_info, status_flags):
  global playback_position
  global playback_wave_data
  global recording_position
  global recording_wave_data
  global exit_looper

  if exit_looper:
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

    playback_position = playback_position + ( loop_def.loop_end - loop_def.loop_start )

  out_wave_data_bytes = bytes(out_wave_data)

  playback_wave_data += out_wave_data_bytes

  # b = time.perf_counter()
  # print (b - a)

  return (out_wave_data_bytes, pyaudio.paContinue)

def start_stream():
  global p
  global stream
  p = pyaudio.PyAudio()
  stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, output=True, input=True, stream_callback=audio_stream_callback)

  global LATENCY_COMPENSATION
  LATENCY_COMPENSATION = int( RATE * ( stream.get_input_latency() + stream.get_output_latency() ) * CHANNELS * SAMPLE_SIZE )

  stream.start_stream()

def is_active():
  return stream and stream.is_active()

def stop_stream():
  global p
  global stream
  stream.stop_stream()
  stream.close()
  stream = None
  p.terminate()
  p = None
