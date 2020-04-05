from looper.playback_definitions import FilePlaybackDefinition, RecordPlaybackDefinition
from looper.settings import LooperSettings

def get_looper_settings():
  ls = LooperSettings()
  ls.loop_bpm = 120
  ls.loop_duration_beat = 4
  ls.record_loop_count = 12
  return ls

# SETUP INITIAL COUNT
def get_playback_definition_list():
  return [
    FilePlaybackDefinition('click_120bpm.wav', play_from=0, play_at=0, play_times=99),
    FilePlaybackDefinition('layer1.wav', play_from=1, play_at=1, play_times=1),
    FilePlaybackDefinition('layer1.wav', play_from=2, play_at=2, play_times=99),
    RecordPlaybackDefinition(play_from=1, play_at=3, play_times=99, overlap=True)
    # RecordPlaybackDefinition(play_from=3, play_at=4, play_times=99)
  ]
