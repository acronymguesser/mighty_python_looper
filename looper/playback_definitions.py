import math
import wave
import looper
import numpy as np

class FileLoopPlaybackDefinition:
  def __init__(self, file_name, play_from, play_at, play_times, overlap=False, duration=1):
    self.file_name = file_name
    self.play_from = play_from
    self.play_at = play_at
    self.play_times = play_times
    self.overlap = overlap
    self.duration = duration
    
    self.play_from_frames = self.play_from * looper.LOOP_SIZE_FRAMES
    self.play_from_bytes = self.play_from * looper.LOOP_SIZE_BYTES
    self.overlap_from_frames = self.play_from_frames + ( looper.LOOP_SIZE_FRAMES * self.duration )

    with wave.open(self.file_name, 'rb') as w:
      if w.getnchannels() != 2 or w.getsampwidth() != 2:
        raise Exception("Only 16-bit stereo files supported.")

      w.readframes(self.play_from_frames) # fast forward to loop start posotion

      available_frames = min( w.getnframes() - self.play_from_frames, looper.LOOP_SIZE_FRAMES * self.duration )
      available_bytes = available_frames * looper.CHANNELS * looper.SAMPLE_SIZE

      self.wave_data = bytearray(looper.LOOP_SIZE_BYTES * self.duration)
      self.wave_data[0:available_bytes] = w.readframes(available_frames)[0:available_bytes]

      # overlapped buffer

      if self.overlap:

        available_frames = min( w.getnframes() - self.overlap_from_frames, looper.LOOP_SIZE_FRAMES )
        available_bytes = available_frames * looper.CHANNELS * looper.SAMPLE_SIZE

        main_buffer = np.frombuffer(self.wave_data[0:available_bytes], dtype=np.uint16)
        overlapped_buffer = np.frombuffer(w.readframes(available_frames), dtype=np.uint16)

        mixed_buffer = np.sum([
          main_buffer,
          overlapped_buffer
        ], axis=0, dtype=np.uint16)

        self.wave_data_overlapped = bytearray(self.wave_data)
        self.wave_data_overlapped[0:available_bytes] = bytes(mixed_buffer)

  def get_loop_wave_data(self):

    loop_cycle = ( looper.playback_position_cycle - self.play_at ) % self.duration
    loop_from_bytes = loop_cycle * looper.LOOP_SIZE_BYTES

    if looper.playback_position_cycle == self.play_at:
      return self.wave_data[loop_from_bytes:loop_from_bytes + looper.LOOP_SIZE_BYTES]

    return self.wave_data_overlapped[loop_from_bytes:loop_from_bytes + looper.LOOP_SIZE_BYTES]

class FileSinglePlaybackDefinition:
  def __init__(self, file_name, play_from, play_at, play_times):
    self.file_name = file_name
    self.play_from = play_from
    self.play_at = play_at
    self.play_times = play_times

    self.play_from_frames = self.play_from * looper.LOOP_SIZE_FRAMES
    self.play_from_bytes = self.play_from * looper.LOOP_SIZE_BYTES

    with wave.open(self.file_name, 'rb') as w:
      if w.getnchannels() != 2 or w.getsampwidth() != 2:
        raise Exception("Only 16-bit stereo files supported.")

      available_frames = min( w.getnframes() - self.play_from_frames, looper.LOOP_SIZE_FRAMES * self.play_times )
      available_bytes = available_frames * looper.CHANNELS * looper.SAMPLE_SIZE

      self.wave_data = bytearray(looper.LOOP_SIZE_BYTES * self.play_times)
      self.wave_data[0:available_bytes] = w.readframes(self.play_from_frames + available_frames)[self.play_from_bytes:self.play_from_bytes + available_bytes]

  def get_loop_wave_data(self):
    loop_cycle = ( looper.playback_position_cycle - self.play_at )
    loop_from_bytes = loop_cycle * looper.LOOP_SIZE_BYTES
    return self.wave_data[loop_from_bytes:loop_from_bytes + looper.LOOP_SIZE_BYTES]

class RecordLoopPlaybackDefinition:
  def __init__(self, play_from, play_at, play_times, overlap=False, duration=1):
    self.play_from = play_from
    self.play_at = play_at
    self.play_times = play_times
    self.overlap = overlap
    self.duration = duration
    self.wave_data = bytearray(looper.LOOP_SIZE_BYTES * self.duration)

    self.filled = False # set to true when certain that the wave data can be fully reused
    self.play_from_bytes = self.play_from * looper.LOOP_SIZE_BYTES
    self.overlap_from_bytes = self.play_from_bytes + ( looper.LOOP_SIZE_BYTES * self.duration )

  def get_loop_wave_data(self):

    loop_cycle = ( looper.playback_position_cycle - self.play_at ) % self.duration
    loop_from_bytes = loop_cycle * looper.LOOP_SIZE_BYTES

    if self.filled:
      return self.wave_data[loop_from_bytes:loop_from_bytes + looper.LOOP_SIZE_BYTES]

    if looper.recording_position_bytes < self.play_from_bytes:
      return self.wave_data[loop_from_bytes:loop_from_bytes + looper.LOOP_SIZE_BYTES] # still zeros

    # main buffer

    available_bytes = min( looper.recording_position_bytes - self.play_from_bytes, ( looper.LOOP_SIZE_BYTES * self.duration ) )

    self.wave_data[0:available_bytes] = looper.recording_wave_data[self.play_from_bytes:self.play_from_bytes + available_bytes]

    if available_bytes < ( looper.LOOP_SIZE_BYTES * self.duration ):
      return self.wave_data[loop_from_bytes:loop_from_bytes + looper.LOOP_SIZE_BYTES]

    if not self.overlap:
      self.filled = True
      return self.wave_data[loop_from_bytes:loop_from_bytes + looper.LOOP_SIZE_BYTES]

    # overlapped buffer

    available_bytes = min( looper.recording_position_bytes - self.overlap_from_bytes, looper.LOOP_SIZE_BYTES )

    main_buffer = np.frombuffer(looper.recording_wave_data[self.play_from_bytes:self.play_from_bytes + available_bytes], dtype=np.uint16)
    overlapped_buffer = np.frombuffer(looper.recording_wave_data[self.overlap_from_bytes:self.overlap_from_bytes + available_bytes], dtype=np.uint16)

    mixed_buffer = np.sum([
      main_buffer,
      overlapped_buffer
    ], axis=0, dtype=np.uint16)

    self.wave_data[0:available_bytes] = bytes(mixed_buffer)

    if available_bytes >= looper.LOOP_SIZE_BYTES:
      self.filled = True

    return self.wave_data[loop_from_bytes:loop_from_bytes + looper.LOOP_SIZE_BYTES]
