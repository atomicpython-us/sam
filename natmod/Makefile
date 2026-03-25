# SAM renderer native module for RP2040
MPY_DIR = /Users/kev/MicroPython/micropython

MOD = sam_render
SRC = sam_render.c
ARCH = armv6m

# Need libgcc for integer division on Cortex-M0 (no hardware divider)
LINK_RUNTIME = 1

include $(MPY_DIR)/py/dynruntime.mk
