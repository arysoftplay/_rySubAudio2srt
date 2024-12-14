# _rySubAudio2srt
Transcribes audio/video files into srt subtitles - specially designed for movies and tv series

Python program based on OpenAi Whisper library

<b>Command line to be executed with Python</b> : 
   - i.e. python @rySubAudio2srt_v1.py -mo "medium.en" -ms 500 -in "Your_Movie" 
   - use python @rySubAudio2srt_v1.py -h for help

<b>Requirements</b> (between parenthesis the versions I tested it with)
   - This program runs on Python 3.9 (3.9.13 64bit)
   - The following libraries need to be installed in python (use command pip install library_name):
       * spleeter (2.4.0)
       * openai-whisper (20240930)
       * pydub (0.25.1)
       * scikit-learn (1.5.2)
       * pyannote.audio (3.3.2)
       * torch (2.5.1+cu124)
       * DeepFilterNet  (0.5.6)

<b>Whisper models: </b>
-  multilanguage: tiny, base, small, medium, large
-  english: tiny.en, base.en, small.en, medium.en

   As a reference the treatment time for an episode of 22 minutes in english:
   *   On an average PC with medium.en => 1:10 hours
   *   On a good gamer PC with medium.en on CPU => 10 minutes
   *   On a good gamer PC with medium.en on GPU => 3 minutes
   *   On a good gamer PC with large on GPU => 20 minutes

   On the tests I didn't find a big difference between medium and large model results for english language.

<b>Whisper library supported languages:</b>

Afrikaans, Arabic, Armenian, Azerbaijani, Belarusian, Bosnian, Bulgarian, Catalan, Chinese, Croatian, Czech, Danish, Dutch, English, Estonian, Finnish, French, Galician, German, Greek, Hebrew, Hindi, Hungarian, Icelandic, Indonesian, Italian, Japanese, Kannada, Kazakh, Korean, Latvian, Lithuanian, Macedonian, Malay, Marathi, Maori, Nepali, Norwegian, Persian, Polish, Portuguese, Romanian, Russian, Serbian, Slovak, Slovenian, Spanish, Swahili, Swedish, Tagalog, Tamil, Thai, Turkish, Ukrainian, Urdu, Vietnamese, and Welsh.

For more information on whisper visit https://platform.openai.com/docs/guides/speech-to-text

Keywords: audio sound video movie shows episodes subtitle subtitles sub subs subtitulos sous-titres srt .srt automatic AI artificial intelligence openai capture read convert transcribe transcriber transcriptor transcription transcript speech to text
