"""Secure Memory Zeroing."""
import ctypes

def secure_zero(byte_arr: bytearray):
    length = len(byte_arr)
    ptr = (ctypes.c_char * length).from_buffer(byte_arr)
    ctypes.memset(ptr, 0, length)
