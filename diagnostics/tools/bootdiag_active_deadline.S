/* Diagnostic only: keep one task active and observe CLOCK_MONOTONIC directly.
 * No libc, nanosleep, fsync, metadata writes, or Android property dependencies.
 * Every elapsed second writes a timestamped heartbeat to nonblocking /dev/kmsg.
 * No args: restart2("bootloader") at 20 s. "check": exit normally after 1 s.
 * Busy polling changes CPU activity; a successful run does not identify a cause.
 * Use only in the before-late-fs configuration with userdata unmounted.
 */
.data
heartbeat:
    .ascii "<4>BOOTDIAG_ACTIVE: elapsed="
    .equ heartbeat_digits, 28
    .ascii "00\n"
    .equ heartbeat_length, 31
.global _start
.text
_start:
    mov x19, #0               // check mode
    mov x23, #20              // duration
    ldr x0, [sp]
    cmp x0, #1
    b.eq prepare
    cmp x0, #2
    b.ne bad_args
    ldr x1, [sp, #16]
    ldr w2, [x1]
    movz w3, #0x6863
    movk w3, #0x6365, lsl #16
    cmp w2, w3
    b.ne bad_args
    ldrb w2, [x1, #4]
    cmp w2, #107
    b.ne bad_args
    ldrb w2, [x1, #5]
    cbnz w2, bad_args
    mov x19, #1
    mov x23, #1
prepare:
    sub sp, sp, #32
    mov x0, #-100
    adrp x1, kmsg_path
    add x1, x1, :lo12:kmsg_path
    mov x2, #2049             // O_WRONLY | O_NONBLOCK
    mov x3, #0
    mov x8, #56              // openat
    svc #0
    tbnz x0, #63, io_failed
    mov x20, x0
    bl read_clock
    ldp x21, x26, [sp]       // start seconds/nanoseconds
    mov x22, #-1             // last whole elapsed second
poll_clock:
    bl read_clock
    ldp x25, x27, [sp]
    sub x24, x25, x21
    cmp x27, x26
    b.ge elapsed_ready
    sub x24, x24, #1
elapsed_ready:
    tbnz x24, #63, clock_failed
    cmp x24, x22
    b.eq poll_clock
    mov x22, x24
    adrp x1, heartbeat
    add x1, x1, :lo12:heartbeat
    mov x9, #10
    udiv x10, x24, x9
    msub x11, x10, x9, x24
    add x10, x10, #48
    add x11, x11, #48
    strb w10, [x1, #heartbeat_digits]
    strb w11, [x1, #heartbeat_digits + 1]
    mov x0, x20
    mov x2, #heartbeat_length
    mov x8, #64              // write
    svc #0
    cmp x0, #heartbeat_length
    b.ne io_failed
    cmp x24, x23
    b.lt poll_clock
    cbnz x19, check_ok
    movz w0, #0xdead
    movk w0, #0xfee1, lsl #16
    movz w1, #0x1969
    movk w1, #0x2812, lsl #16
    movz w2, #0xc3d4
    movk w2, #0xa1b2, lsl #16
    adrp x3, bootloader
    add x3, x3, :lo12:bootloader
    mov x8, #142
    svc #0
    neg x0, x0
    b exit
read_clock:
    mov x0, #1               // CLOCK_MONOTONIC
    mov x1, sp
    mov x8, #113             // clock_gettime
    svc #0
    cbnz x0, clock_failed
    ret
bad_args:
    mov x0, #64
    b exit
io_failed:
    mov x0, #74
    b exit
clock_failed:
    mov x0, #70
    b exit
check_ok:
    mov x0, #0
exit:
    mov x8, #93
    svc #0
.section .rodata
kmsg_path:
    .asciz "/dev/kmsg"
bootloader:
    .asciz "bootloader"
.section .note.GNU-stack,"",@progbits
