from looper.playback_definitions import FilePlaybackDefinition, RecordPlaybackDefinition

playback_definition_list = []

# SETUP INITIAL COUNT
playback_definition_list = [
  FilePlaybackDefinition('click_120bpm.wav', play_from=0, play_at=0, play_times=99),
  FilePlaybackDefinition('layer1.wav', play_from=1, play_at=1, play_times=1),
  FilePlaybackDefinition('layer1.wav', play_from=2, play_at=2, play_times=99),
  RecordPlaybackDefinition(play_from=1, play_at=3, play_times=99)
  # RecordPlaybackDefinition(play_from=3, play_at=4, play_times=99)
]
