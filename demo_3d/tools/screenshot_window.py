"""Capture a mapped Gazebo GUI window with X11, including under WSLg."""
import ctypes as C
import re
import subprocess
from PIL import Image, ImageStat

class XImage(C.Structure):
    _fields_=[('width',C.c_int),('height',C.c_int),('xoffset',C.c_int),('format',C.c_int),
              ('data',C.c_void_p),('byte_order',C.c_int),('bitmap_unit',C.c_int),
              ('bitmap_bit_order',C.c_int),('bitmap_pad',C.c_int),('depth',C.c_int),
              ('bytes_per_line',C.c_int),('bits_per_pixel',C.c_int),
              ('red_mask',C.c_ulong),('green_mask',C.c_ulong),('blue_mask',C.c_ulong)]


def capture(path, gui_pid=None):
    tree=subprocess.check_output(['xwininfo','-root','-tree'],text=True,timeout=3)
    windows=re.findall(r'(0x[0-9a-f]+) "([^"]*Gazebo[^"]*)".*?(\d+)x(\d+)\+',tree,re.I)
    if gui_pid is not None:
        windows=[row for row in windows if re.search(r'=\s*'+str(gui_pid)+r'\b',
                 subprocess.check_output(['xprop','-id',row[0],'_NET_WM_PID'],text=True,timeout=2))]
    if not windows:raise RuntimeError('No mapped X11 window owned by attached Gazebo GUI')
    win,title,w,h=max(windows,key=lambda row:int(row[2])*int(row[3]))
    x=C.CDLL('libX11.so.6')
    x.XOpenDisplay.argtypes=[C.c_char_p];x.XOpenDisplay.restype=C.c_void_p
    x.XGetImage.argtypes=[C.c_void_p,C.c_ulong,C.c_int,C.c_int,C.c_uint,C.c_uint,C.c_ulong,C.c_int]
    x.XGetImage.restype=C.POINTER(XImage)
    x.XDestroyImage.argtypes=[C.POINTER(XImage)]
    x.XCloseDisplay.argtypes=[C.c_void_p]
    d=x.XOpenDisplay(None)
    if not d:raise RuntimeError('XOpenDisplay failed')
    img=None
    try:
        img=x.XGetImage(d,int(win,16),0,0,int(w),int(h),C.c_ulong(-1).value,2)
        if not img:raise RuntimeError('XGetImage failed')
        v=img.contents
        if v.bits_per_pixel!=32 or v.byte_order!=0:raise RuntimeError('Unsupported X11 pixel format')
        raw=C.string_at(v.data,v.bytes_per_line*v.height)
        picture=Image.frombytes('RGB',(v.width,v.height),raw,'raw','BGRX',v.bytes_per_line)
        picture.save(path)
        viewport=picture.crop((10,160,int(v.width*.55),v.height-110))
        variation=max(ImageStat.Stat(viewport).stddev)
        return {'path':str(path),'window_id':win,'title':title,'width':v.width,'height':v.height,
                'gui_pid':gui_pid,'viewport_stddev':variation,'rendered_content':variation>15}
    finally:
        if img:x.XDestroyImage(img)
        x.XCloseDisplay(d)
