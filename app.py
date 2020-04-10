import sys, getopt
import wave
import time
import looper

def main(argv):

  looper_config_path = "looper_config"

  try:
    opts, *_ = getopt.getopt(argv, "" , ["config="])
  except getopt.GetoptError as err:
    print(err)
    exit()

  for o, a in opts:
    if o == "--config":
      looper_config_path = a
      if looper_config_path.endswith(".py"):
        looper_config_path = looper_config_path[:-3]

  looper_config = __import__(looper_config_path)

  looper.initialize(looper_config.get_looper_settings())
  looper.set_playback_definition_list(looper_config.get_playback_definition_list())

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

if __name__ == "__main__":
   main(sys.argv[1:])