import wave
import looper

class FilePlaybackDefinition:
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

      available_frames = min( w.getnframes() - self.play_from_frames, looper.LOOP_SIZE_FRAMES )
      available_bytes = available_frames * looper.CHANNELS * looper.SAMPLE_SIZE

      self.wave_data = bytearray(looper.LOOP_SIZE_BYTES)
      self.wave_data[0:available_bytes] = w.readframes(self.play_from_frames + available_frames)[self.play_from_bytes:self.play_from_bytes + available_bytes]

  def get_loop_wave_data(self):
    return self.wave_data

class RecordPlaybackDefinition:
  def __init__(self, play_from, play_at, play_times):
    self.play_from = play_from
    self.play_at = play_at
    self.play_times = play_times
    self.wave_data = bytearray(looper.LOOP_SIZE_BYTES)

    self.filled = False # set to true when certain that the wave data can be fully reused
    self.play_from_bytes = self.play_from * looper.LOOP_SIZE_BYTES

  def get_loop_wave_data(self):

    if self.filled:
      return self.wave_data

    if looper.recording_position < self.play_from_bytes:
      return self.wave_data # still zeros

    available_bytes = min( looper.recording_position - self.play_from_bytes, looper.LOOP_SIZE_BYTES )

    self.wave_data[0:available_bytes] = looper.recording_wave_data[self.play_from_bytes:self.play_from_bytes + available_bytes]

    if available_bytes >= looper.LOOP_SIZE_BYTES:
      self.filled = True

    return self.wave_data
