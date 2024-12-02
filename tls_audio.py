'''*******************************************************************
LIST OF FUNCTIONS:
audio_cut(sound, time_from, time_to)                                        # gets chunk from audiosement (times in milliseconds)
audio_append(sound1, sound2, crossf=0)                                      # appends two audio bands
audio_list_append(sounds, crossf=0)                                         # appends a list of audio bands
file_list_append(file_list, crossf=0)                                       # appends a list of audio files
audio_load(source_file)                                                     # import audio from file
audio_save(sound, file_to, audio_format)                                    # export audio to file
filter_noise(source_file, output_file)                                      # remove noise from audio 
audio_split (sound, chunkDuration)                                          # splits audio in chunks of "chunkDuration" length in milliseconds
filter_laugh(file_in, file_out)                                             # removes laughter from audio file
remove_music(fname, fold)                                                   #separates music and instruments from the original audio band 
get_clean_audio(video_file, fold, remove_laughter, remove_noise)            # cleans audio of music, laughter and noise
*******************************************************************'''

from pydub import AudioSegment
from df.enhance import enhance, init_df, load_audio, save_audio
import laughr_embed as laf
import subprocess
from tls_text import right

#gets chunk from audiosement (times in milliseconds)
'''----------------------'''
def audio_cut(sound, time_from, time_to):
    '''----------------------'''
    chunk = sound[time_from:time_to]
    return chunk

# appends two audio bands
'''----------------------'''
def audio_append(sound1, sound2, crossf=0):
    '''----------------------'''
    if crossf==0:
        merged = sound1 + sound2 
    else: 
        merged = sound1.append(sound2,crossfade=crossf)

    return merged

# appends a list of audio bands
'''----------------------'''
def audio_list_append(sounds, crossf=0):
    '''----------------------'''
    merged = AudioSegment.empty()

    for chunk in sounds:
        if crossf==0:
            merged = merged + chunk
        else: 
            merged = merged.append(chunk,crossfade=crossf)

    return merged

# appends a list of audio files
'''----------------------'''
def file_list_append(file_list, crossf=0):
    '''----------------------'''
    merged = AudioSegment.empty()

    for file in file_list:
        if crossf==0:
            merged = merged + audio_load(file)
        else: 
            merged = merged.append(audio_load(file),crossfade=crossf)

    return merged


# import audio from file
'''----------------------'''
def audio_load(source_file):
    '''----------------------'''
    if source_file[-4:]==".mp3":
        sound = AudioSegment.from_mp3(source_file)        
    else:
        sound = AudioSegment.from_file(source_file)
    
    return sound

# export audio to file
'''----------------------'''
def audio_save(sound, file_to, audio_format):
    '''----------------------'''
    sound.export(file_to, format=audio_format)

# remove noise from audio 
'''----------------------'''
def filter_noise(source_file, output_file):
    '''----------------------'''
    '''
    Note: for DeepFilterNet to work ensure that on 
    <your_python_installation_folder>\lib\subprocess.py

    This definition has shell=True
    def __init__(self, args, bufsize=-1, executable=None,
                stdin=None, stdout=None, stderr=None,
                preexec_fn=None, close_fds=True,
                shell=True, cwd=None, env=None, universal_newlines=None,
                startupinfo=None, creationflags=0,
                restore_signals=True, start_new_session=False,
                pass_fds=(), *, user=None, group=None, extra_groups=None,
                encoding=None, errors=None, text=None, umask=-1, pipesize=-1):
    '''
    df_model, df_state, _ = init_df()  # Load default model

    audio, _ = load_audio(source_file, sr=df_state.sr())
    enhanced_audio = enhance(df_model, df_state, audio)
    save_audio(output_file, enhanced_audio, df_state.sr())  #in wav format

# splits audio in chunks of "chunkDuration" length in milliseconds
'''----------------------'''
def audio_split (sound, chunkDuration):
    '''----------------------'''
    ranges=[]
    chunks=[]

    fileDuration = int(sound.duration_seconds * 1000)

    #print("Total file duration: ", fileDuration, " : " , mill2time(fileDuration), "\n")

    #print("calculating ranges\n")
    for i in range (0, int(fileDuration/chunkDuration)+1):
        if (i+1)*chunkDuration-1<fileDuration:
            ranges = ranges + [(i*chunkDuration,(i+1)*chunkDuration-1)]    
            #print(i*chunkDuration,"-",(i+1)*chunkDuration-1)
        else:
            ranges = ranges + [(i*chunkDuration,fileDuration)]    
            #print(i*chunkDuration,"-",fileDuration,"\n")

    for x, y in ranges:
        chunks = chunks + [sound[x : y]]

    return chunks

# removes laughter from audio file
'''----------------------'''
def filter_laugh(file_in, file_out):
    '''----------------------'''
    laf.audio_remove_laugh("pretrained_models/laughter-trained-model.h5", file_in, file_out)

#separates music and instruments from the original audio band 
'''---------------------------'''
def remove_music(fname, fold):    
    '''---------------------------'''  
    # spleeter supports a maximum of 10 minutes of audio
    subprocess.run("spleeter separate -o .\\tmp\\" + fold + " -c mp3 " + fname)

# cleans audio of music, laughter and noise
'''---------------------------'''
def get_clean_audio(video_file, fold, remove_laughter, remove_noise):
    '''---------------------------'''

    subprocess.run("mkdir tmp\\" + fold, shell=True)   

    sound_file = audio_load(video_file)

    #splits audio in files of 9 minutes (max supported by spleeter is 10 mins)
    chunks = audio_split (sound_file, 540000)

    cnt=0

    clean_list=[]

    # cleans each audio chunk 
    for chunk in chunks:
        cnt=cnt+1
        faudio = "tmp\\" + fold + "\\audio" + str(cnt) + ".mp3"
        fvocals = "tmp\\" + fold + "\\audio" + str(cnt) + "\\vocals.mp3"
        flaughter = "tmp\\" + fold + "\\audio" + str(cnt) + "\\vocals_laugh.mp3"
        fnoise = "tmp\\" + fold + "\\audio" + str(cnt) + "\\vocals_noise.wav" 
        fout = "tmp\\" + fold + "\\out.mp3"

        chunk.export(faudio, format="mp3")

        print("------------------------- remove music from ", faudio, " -----------------------")
        remove_music(faudio, fold)

        if remove_laughter:
            print("------------------------- remove laughter from ", fvocals, " -----------------------")       
            filter_laugh(fvocals, flaughter)

        if remove_noise:
            if remove_laughter:
                print("------------------------- remove noise from ", flaughter, " -----------------------")            
                filter_noise(flaughter, fnoise)
            else:
                print("------------------------- remove noise from ", fvocals, " -----------------------")            
                filter_noise(fvocals, fnoise)

        if remove_noise:
            clean_list = clean_list + [fnoise]
        else:
            if remove_laughter:
                clean_list = clean_list + [flaughter]
            else:
                clean_list = clean_list + [fvocals]

    # merges all clean chunks 
    clean_sound = file_list_append(clean_list)
    print("------------------------- saving ", fout, " -----------------------")         
    audio_save(clean_sound, fout, right(fout, 3))

    return fout