/* Diagnostic only: no libc, log writes, sync, or init property dependencies.
 * With no arguments, request restart2("bootloader") after 20 seconds.
 * The sole accepted argument "check" sleeps one second and exits without reboot.
 * Use only with the before-late-fs pause, while userdata remains unmounted.
 */
.global _start
.text
_start:
    mov x19, #0
    mov x20, #20
    ldr x0, [sp]
    cmp x0, #1
    b.eq sleep_start
    cmp x0, #2
    b.ne bad_args
    ldr x1, [sp, #16]
    ldr w2, [x1]
    movz w3, #0x6863
    movk w3, #0x6365, lsl #16  // "chec", little endian
    cmp w2, w3
    b.ne bad_args
    ldrb w2, [x1, #4]
    cmp w2, #107              // k
    b.ne bad_args
    ldrb w2, [x1, #5]
    cbnz w2, bad_args
    mov x19, #1
    mov x20, #1
sleep_start:
    sub sp, sp, #16
    stp x20, xzr, [sp]
sleep_again:
    mov x0, sp
    mov x1, sp                // retain remaining interval if interrupted
    mov x8, #101              // nanosleep
    svc #0
    cmn x0, #4               // EINTR
    b.eq sleep_again
    cbnz x0, sleep_failed
    cbnz x19, check_ok
    movz w0, #0xdead
    movk w0, #0xfee1, lsl #16 // LINUX_REBOOT_MAGIC1
    movz w1, #0x1969
    movk w1, #0x2812, lsl #16 // LINUX_REBOOT_MAGIC2
    movz w2, #0xc3d4
    movk w2, #0xa1b2, lsl #16 // LINUX_REBOOT_CMD_RESTART2
    adrp x3, bootloader
    add x3, x3, :lo12:bootloader
    mov x8, #142              // reboot; deliberately no filesystem sync
    svc #0
    neg x0, x0               // surface syscall errno as process exit status
    b exit
bad_args:
    mov x0, #64
    b exit
sleep_failed:
    mov x0, #70
    b exit
check_ok:
    mov x0, #0
exit:
    mov x8, #93
    svc #0
.section .rodata
bootloader:
    .asciz "bootloader"
.section .note.GNU-stack,"",@progbits
