'''-------------------------------
CONTENTS :
 separate_punctuation(text)
 left(s, amount)
 right(s, amount)
 mid(s, offset, amount)
-------------------------------'''

#-------------------------------
def separate_punctuation(text):
#-------------------------------
    punct =",;.?!%" 
    for sign in punct:
        text = text.replace(sign, " "+sign+" ")

    text=text.strip()
    while "  " in text:
        text = text.replace("  "," ")

    return text

def left(s, amount):
    return s[:amount]

def right(s, amount):
    return s[-amount:]

def mid(s, offset, amount):
    return s[offset:offset+amount]