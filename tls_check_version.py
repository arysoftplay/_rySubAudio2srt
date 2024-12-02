'''-------------------------------
CONTENTS :
def py (version):
def tf (version):
-------------------------------'''

#import os
import sys
from tensorflow import __version__ as vs

#-------------------------------
def py (version):
#-------------------------------
    ver = str(sys.version_info[0]) + "." +str(sys.version_info[1])

    if ver != version:
        print("\n\n------COMPATIBILITY ISSUE ------------")
        print("\n\nThis program needs PYTHON %s and current version is %s" % (version, ver))        
        #os.abort()    
        exit()

#-------------------------------
def tf (version):
#-------------------------------
    if vs[:len(version)]!=version:
        print("\n\n------COMPATIBILITY ISSUE ------------")
        print("\n\nThis program needs tensorflow %s and current version is %s" % (version, vs))        
        #os.abort()
        exit()