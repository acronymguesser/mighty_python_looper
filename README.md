# MIGHTY PYTHON LOOPER #

## What is it? ##

It is basically an audio looper. You play something, and the app records it 
and then plays it in a continuous loop until you stop it.

## But... why? Doesn't any DAW do  that nowadays? ##

I wrote this small app because I desperately needed a looper to play my music,
and for some really unfortunate timing, my personal PC (where my DAW of 
preference is properly configured) decided to stop working just when the 2020
pandemic mandatory quarantine was stablished in my city.

As any challenging time brings oporunities I dediced to develop this nice app
also having in mind that it may become handy in the future.

## Ok, let me look at the features ##

The Mighty Python Looper has:

- Configurable tempo and loop length
- Dynamic in/out latency adjustment
- Loop playback from existing WAV files
- Loop playback from any section of the recorded audio
- Possibility to stop individual playbacks (the output is rendered with the 
  remaining active loops)
- Complete session export to two separate files for recording and playback

## Sounds nice! How does it work? ##

When you start-up the app, you are in a session, which means that you have some
preconfigured settings for the song (such as BPM or loop duration) and some 
others to indicate when to start playing the different audio sections.

During runtime, the engine (I ALWAYS WANTED TO USE THAT WORD) calculates in 
which loop cycle you currently are, and mixes all audio sections that you 
indicated to be played at that loop cycle, to finally render the playback and
send it to your speakers.

Audio sections may be associated to either the audio recorded during the 
session or an existing WAV file, thus giving the possibility to play pre-mixed 
sections synchronized with the song.

# Configuring the session #

Sessions are configured in the file `looper_config.py`. That file is 
dinamycally loaded as a module where the following functions are expected to 
be defined:

- `get_looper_settings` returns general settings for the song and the looper 
  itself, such as BPMs or the total record time.

- `get_playback_definition_list` returns a list of playback definition objects
  which tells the looper which sections are active and where to find the audio
  sections to mix in the playback.

There is an example of the `looper_config.py` file in this repository.

## Looper Settings ##

The method `get_looper_settings` must return a `LooperSettings` object (in 
module `looper.settings`). It allows adjusting the following values:

- `loop_bpm` is the BPM of the song
- `loop_duration_beat` inidcates the duration *in beats* of each loop cycle
- `record_loop_count` specifies the total recording buffer, in loop cycles. 
  After that number of loop cycles, the recording is stopped but the playback
  continues with the already recorded audio.

## Playback Definition List ##

The method `get_playback_definition_list` must return a list of Playback 
Definition objects (in module `looper.playback_definitions`), which are described
below.

### FilePlaybackDefinition ###

Specifies playback of any section of an existing WAV file.

Initialization values:

- `file_name` specifies the WAV file (absolute or relative)
- `play_from` indicates the loop cycle *within the WAV file* from where the 
   audio section will be extracted
- `play_at` indicates the first session loop where the audio section is played
- `play_times` indicates how many times the audio section is played

### RecordPlaybackDefinition ###

Specifies playback of any section of the audio recorded during the session.

Initialization values:

- `play_from` indicates the loop cycle *within the session recorded audio* from
  where the audio section will be extracted
- `play_at` indicates the first session loop where the audio section is played
- `play_times` indicates how many times the audio section is played

# Running the application #

Just move to the root folder and type `python app.py`. Press *enter* to exit 
and store the session record and playback audio to the files "record.wav" and
"playback.wav" respectively.