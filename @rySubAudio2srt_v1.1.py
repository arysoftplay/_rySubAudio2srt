'''####################################
###         RUNS ON PYTHON 3.9      ###
#######################################'''

import subprocess
import whisper
import wave
import contextlib
import datetime
from pydub import AudioSegment, silence
from datetime import datetime
import os
from sklearn.cluster import AgglomerativeClustering
from pyannote.audio import Audio
from pyannote.core import Segment
import torch
import numpy as np
from tls_text import left
import tls_audio as ta
import argparse
import shutil
import tls_check_version as cv
from numba import cuda

dialogs=[]

cv.py("3.9")

'''******************************************************** FUNCTION DECLARATIONS **************************************************'''

#treats parameters from command line and return the values
'''---------------------------'''
def getParams():
    '''---------------------------'''   
    models=["tiny", "base", "small", "medium", "large", "tiny.en", "base.en", "small.en", "medium.en"]

    # construct the argument parser and parse the arguments
    ap = argparse.ArgumentParser()

    ap.add_argument("-lg", "--language", default="en", help="audio language iso 2 chars - default: en")
    ap.add_argument("-mo", "--model", default="medium.en", help="accepted values tiny, base, small, medium, large (all but large can have .en suffix for english audio  - default: medium.en)")
    ap.add_argument("-ms", "--min_silence_length", default="500", help="minimun silence length in milliseconds - default: 500")
    ap.add_argument("-rl", "--remove_laughter", default="N", help="remove laughter (Y/N) - default: N")
    ap.add_argument("-rn", "--remove_noise", default="N", help="remove noise (Y/N) - default: N")
    ap.add_argument("-lt", "--logprob_threshold", default="-0.8", help="logprob_threshold (see whisper documentation) - default : -0.8")
    ap.add_argument("-nt", "--no_speech_threshold", default="0.6", help="no_speech_threshold (see whisper documentation) - default : 0.6")    
    ap.add_argument("-in", "--input_file", help="source audio/video file")

    args = vars(ap.parse_args())
    if args.get("input_file", None) is None:
        print("Input file is mandatory. Use -h option for help")
        exit()
    else:
        video_file=args["input_file"]
        
    language = args.get("language", None).lower()

    min_silence_length = int(args.get("min_silence_length", None))

    if args.get("remove_laughter", None).lower()!="y":
        rl = False
    else:
        rl = True

    if args.get("remove_noise", None).lower()!="y":
        rn = False
    else:
        rn = True

    logprob_threshold=float(args.get("logprob_threshold", None))
    no_speech_threshold=float(args.get("logprob_threshold", None))

    model = args.get("model", None).lower()
    if not model in models:	
        print("Incorrect model. Use -h option for help")
        exit()

    return video_file, language, model, min_silence_length, rl, rn, logprob_threshold, no_speech_threshold

#converts milliseconds to srt time format
'''---------------------------'''
def mill2time(milli):
    '''---------------------------'''    
    seconds=int((milli/1000)%60)
    minutes=int((milli/(1000*60))%60)
    hours=int((milli/(1000*60*60))%24)
    mill=milli-(seconds*1000)-(minutes*60*1000)-(hours*60*60*1000)

    all = "%s:%s:%s.%s" % (f"{hours:0>2}",f"{minutes:0>2}",f"{seconds:0>2}",f"{mill:0>3}")

    return all

#---------------------------------
def resetGPU():
#---------------------------------    
    if cuda.is_available():
        device = cuda.get_current_device()
        device.reset()    

#separates music and instruments from the original audio band
'''---------------------------'''
def removeMusic(video_file, fold):    
    '''---------------------------'''

    subprocess.run("mkdir tmp\\" + fold, shell=True)

    sound_file = AudioSegment.from_file(video_file)
    fileDuration = int(sound_file.duration_seconds * 1000)
    print("processing" + video_file)
    print("Total file duration: ", fileDuration, " : " , mill2time(fileDuration), "\n")

    fname = "tmp\\" + fold + "\\audio.mp3"
    sound_file.export(fname, format="mp3")

    print("\n----------------------------- remove background music ",fname, "-----------------------------\n")
    subprocess.run("spleeter separate -o .\\tmp\\" + fold + " -c mp3 " + fname)

    return fname


# normalizes an audio chunk to a target amplitude.
'''---------------------------'''
def apply_audio_gain(aChunk, target_dBFS):    
    '''---------------------------'''

    ''' Normalize given audio chunk '''
    change_in_dBFS = target_dBFS - aChunk.dBFS
    return aChunk.apply_gain(change_in_dBFS)

# splits audio into non silenced chunks and saves each chunk as an audio file
'''---------------------------'''
def SplitAudio(audio_file, fold, min_silence_length):    
    '''---------------------------'''

    print("\n----------------------------- Split audio by silences -----------------------------\n")

    #myaudio = AudioSegment.from_file(audio_file, "mp4")
    myaudio = AudioSegment.from_mp3(audio_file)
    fileDuration = int(myaudio.duration_seconds * 1000)    

    dBFS=myaudio.dBFS   #get audio amplitude

    silence_threshold = dBFS-16 # Consider a chunk silent if it's quieter than "silence_threshold" dBFS. Défault -16

    silences = silence.detect_silence(myaudio, min_silence_len=min_silence_length, silence_thresh=silence_threshold)

    silences = [((start),(stop)) for start,stop in silences] #in milliseconds

    #applies audio gain so the spoken parts are better transcripted
    myaudio = apply_audio_gain(myaudio, dBFS+2.0)

    voices = []
    prevEnd=0

    print("silances=", silences)

    for item in silences:        
        if item[0]!=0:
            voices = voices + [(prevEnd, item[0])]
        prevEnd=item[1]
    
    if prevEnd<fileDuration:
        voices = voices + [(prevEnd, fileDuration)]

    print("voices=", voices)

    files=[]

    for item in voices:
        x=item[0]
        y=item[1]           
        new_file = myaudio [x : y]

        fname = "tmp\\" + fold + "\\" + str(x) + "-" + str(y) +".mp3"
        new_file.export(fname, format="mp3")
        files = files + [(fname)]

    return files

# identifies speaker for each transcription segment
'''---------------------------'''
def segment_by_speaker(model, path, segments, duration, mono, num_speakers=2):    
    '''---------------------------'''

    from pyannote.audio.pipelines.speaker_verification import PretrainedSpeakerEmbedding
    if torch.cuda.is_available():
        embedding_model = PretrainedSpeakerEmbedding( 
            "speechbrain/spkrec-ecapa-voxceleb",
            device=torch.device("cuda"))
    else:
        embedding_model = PretrainedSpeakerEmbedding( 
                "speechbrain/spkrec-ecapa-voxceleb")

    audio = Audio()

    embeddings = np.zeros(shape=(len(segments), 192))
    for i, segment in enumerate(segments):
      embeddings[i] = segment_embedding(embedding_model, segment, audio, duration, mono)
    embeddings = np.nan_to_num(embeddings)
    
    clustering = AgglomerativeClustering(num_speakers).fit(embeddings)
    labels = clustering.labels_
    for i in range(len(segments)):
      segments[i]["speaker"] = 'SPEAKER ' + str(labels[i] + 1)

    return segments    

'''---------------------------'''
def segment_embedding(embedding_model, segment, audio, duration, mono):
    '''---------------------------'''
    start = segment["start"]
    # Whisper overshoots the end timestamp in the last segment
    end = min(duration, segment["end"])
    clip = Segment(start, end)
    waveform, sample_rate = audio.crop(mono, clip)
    return embedding_model(waveform[None])


# transcribes audio speech into timed text segments
'''---------------------------'''
def extract_dialogs(model, path, fold, lang, by_speaker, lp_thres, np_thres):
    '''---------------------------'''
   
    print("\n----------------------------- extract dialogs from file ", path, "----------------------------------\n")

    mono = "tmp\\" + fold + "\\mono.wav"
    cmd = 'ffmpeg -i {} -y -ac 1 {}'.format(path, mono)

    print("--- convert audio to mono ---\n")

    #if chunk doesn't open (some very small chunks can cause error on fmpeg) => skip chunk treatment
    try:
        subprocess.check_output(cmd, shell=True)    

        '''
        # defaults at the time of writing: 
            logprob_threshold: -1.0
                If the average log probability over sampled tokens is below this value, treat as failed

            no_speech_threshold: 0.6
                If the no_speech probability is higher than this value AND the average log probability
                over sampled tokens is below `logprob_threshold`, consider the segment as silent
        '''

        print("--- transcribe audio ---\n")

        result = model.transcribe(mono, language=lang, logprob_threshold=lp_thres, no_speech_threshold=np_thres)
        segments = result["segments"]

        with contextlib.closing(wave.open(mono,'r')) as f:
            frames = f.getnframes()
            rate = f.getframerate()
            duration = frames / float(rate)

        if (by_speaker=="Y"):
            segments = segment_by_speaker(model, path, segments, duration, mono, 8)

        # fix whisper first and last segments 
        cnt=0
        for segment in segments:
            cnt=cnt+1
            if cnt==1:

                ''' DEPRECATED - not usefull with silence splits '''
                ''' 
                print("fist segment in ", path, " starts at ", segment["start"])

                #whisper usually starts first segment at 0
                if segment["start"]==0:
                    print("\nstart=0")
                    #calculate 1 second every 10 chars (average 2 words per second at 5 chars per word)
                    segLen = len(segment["text"])/10
                    print("segment len, end=", segLen, ", ", segment["end"], "\n")

                    if segment["end"]-segLen>0:
                        print("correcting segment start from 0 to: ", segment["end"]-segLen)
                        segment["start"]=segment["end"]-segLen
                '''

        if cnt!=0:  #if at least one segment on chunk
            #Whisper overshoots the end timestamp in the last segment
            if segment["end"]>duration:
                segment["end"]=duration
                print("correcting segment end from ", segment["end"], " to ", duration)

        #if segments are too long, splits them in smaller segments
        segments = split_text(segments, 14, 5)

    except subprocess.CalledProcessError as e:
        print("error opening chunk: ", mono)

        file = os.path.basename(path)[:-4]
        times = file.split("-")
        segments=[{"start": int(times[0])/1000, "end": int(times[1])/1000, "text": "@rySubAudio2srt : ERROR OPENING SEGMENT"}]

    return segments 

# splits long text segments into smaller sub-segments
'''---------------------------'''
def split_text(transcript, max_words=14, min_words = 5):
    '''---------------------------'''
    segments2 = []

    for segment in transcript:
        # Extract start and end times from the transcript
        start_time = segment["start"]
        end_time = segment["end"]
        
        if end_time>start_time: # test times because whisper can generate errors
            # Extract the words from the transcript
            sentence = segment["text"]
            words = sentence.split()
            num_words = len(words)

            max_words2 = max_words

            if num_words<=max_words:
                #current segment is already OK
                segments2 = segments2 + [{"start": start_time, "end": end_time, "text": segment["text"]}]
            else:
                #current segment is too long and has to be subdivided
                print("\nSubdividing segment: ",  segment["text"], "\n")

                #calculates the average words per chunk
                max_words_new = int(num_words/(int(num_words/max_words)+1))+1
                max_words2 = max_words_new
                print("max_words_new=", max_words_new)

                #recalculates words per chunk in order to have at least min_words in the last chunk
                if (num_words % max_words_new < min_words):
                    for i in range (1, max_words_new-min_words):                
                        if (num_words % (max_words_new-i) >= min_words):
                            max_words2 = max_words_new-i
                            print("split with max_words=", max_words2)
                            break

                # Calculate the total time and time per word
                total_time = end_time - start_time
                time_per_word = total_time / num_words
                
                # Split the words into chunks
                chunks = [words[i:i+max_words2] for i in range(0, len(words), max_words2)]
                    
                # Construct the output
                start2 = start_time

                for chunk in chunks:
                    text=""
                    for word in chunk:
                        text=text + " " + word
                    
                    segments2 = segments2 + [{"start": start2, "end": start2 + len(chunk)*time_per_word, "text": text.strip()}]
                    start2 = start2 + len(chunk)*time_per_word
    
    return segments2

# writes text dialogs into an srt file
'''---------------------------'''
def write_dialogs(segments, audio_file, cont, last_end, fold, video_file, last):
    '''---------------------------'''

    print("\n---------------------- write subtitles for file ", audio_file, "------------------------------------\n")

    end = 0

    #get initial file time
    audio_file = audio_file.replace("tmp\\"+fold+"\\","")
    initTime=int(left(audio_file, audio_file.find("-")))

    #open srt file with utf-8 encoding to avoid encoding errors that crash the program
    f = open("tmp\\" + fold + "\\" + os.path.basename(video_file)[:-4] + ".srt", "a", encoding="utf-8")

    for segment in segments:

        #convert start & end seconds to milliseconds
        start = initTime + int(segment["start"]*1000)
        end = initTime + int(segment["end"]*1000)
        txt = segment["text"].strip()

        #write subtitle
        cont=cont+1
        f.write("%d%s" % (cont,"\n"))
        f.write("%s%s%s%s" % (mill2time(start), " --> ", mill2time(end),"\n"))
        f.write(txt + "\n")    
        f.write("\n")

    if last:

        if end==0:
            #if chunk is emtpy then take the previous chunk end
            end=last_end

        #write @rysoft subtitle        
        f.write("%d%s" % (cont+1,"\n"))
        f.write("%s%s%s%s" % (mill2time(end + 1000), " --> ", mill2time(end+5000),"\n"))
        f.write("Transcribed with @rySubAudio2srt v1.1\n")    
        f.write("https://github.com/arysoftplay/_rySubAudio2srt\n")
        f.write("\n")

    f.close()    

    return cont, end

'''**************************************************** MAIN PROGRAM ***************************************************'''
'''mod="medium.en"
video_file ="D:\\NewsLeecher\\downloads\\_Temp\\The Naked Truth\\Season 2\\The Naked Truth - S02E01 - We're At NBC Now vostEN.mkv"
vocals_file = "tmp\\test\\out.mp3"
min_silence_length=500
lang="en"'''

video_file, lang, mod, min_silence_length, rem_laugh, rem_noise, lp_thres, np_thres = getParams()

startTime = datetime.now()
fold = "%s%s%s" % (str(datetime.now().hour).zfill(2),str(datetime.now().minute).zfill(2),str(datetime.now().second).zfill(2))
srt = os.path.basename(video_file)[:-4] + ".srt"

resetGPU()

model = whisper.load_model(mod)

subprocess.run("mkdir tmp\\" + fold, shell=True)

print("\n\n**************************** ", video_file, " **********************\n\n")
print("------------------ start Time: ", startTime, "-------------------------\n")

#vocals_file = removeMusic(video_file, fold)

vocals_file = ta.get_clean_audio(video_file, fold, remove_laughter=rem_laugh, remove_noise=rem_noise)

currTime = datetime.now()
elapsed = currTime - startTime
print("------------------ Current Time: ", currTime, "-------------------------\n")
print("------------------- elapsed: ", elapsed, "-------------------------\n")

chunks = SplitAudio(vocals_file, fold, min_silence_length)

currTime = datetime.now()
elapsed = currTime - startTime
print("------------------ Current Time: ", currTime, "-------------------------\n")
print("------------------- elapsed: ", elapsed, "-------------------------\n")

cont=0
end=0

for audio_file in chunks:
    if (audio_file == chunks[-1]):
        last=True
    else:
        last=False

    seg = extract_dialogs(model, audio_file, fold, lang, "N", lp_thres, np_thres)
    cont, end = write_dialogs(seg,audio_file, cont, end, fold, video_file, last)
    lastTime = currTime
    currTime = datetime.now()    
    elapsed = currTime - startTime
    print("------------------ Current Time: ", currTime, "-------------------------\n")
    print("------------------- Elapsed chunk: ", currTime-lastTime, "-------------------------\n")    
    print("------------------- Elapsed total: ", elapsed, "-------------------------\n")

# moves the srt to the tmp folder and removes the working files
os.replace("tmp\\" + fold + "\\" + srt, "tmp\\" + srt)
shutil.rmtree("tmp\\" + fold)

print("------------------- Total processing time: ", elapsed, "-------------------------\n")    

resetGPU()
