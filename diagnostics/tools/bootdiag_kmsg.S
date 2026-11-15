/* Static AArch64 Linux kmsg collector. argv[1] must name a mounted filesystem.
 * No libc or later path lookups: keeps both descriptors across init's switch-root.
 * Every output write uses O_DSYNC. Only EPIPE (overrun) and EINTR are retried.
 */
.global _start
.text
_start:
    ldr x0, [sp]
    cmp x0, #2
    b.ne bad_args
    ldr x1, [sp, #16]
    mov x0, #-100
    mov x2, #5185             // O_WRONLY | O_CREAT | O_APPEND | O_DSYNC
    mov x3, #384              // 0600
    mov x8, #56               // openat
    svc #0
    tbnz x0, #63, bad_output
    mov x20, x0
    mov x0, #-100
    adrp x1, kmsg_path
    add x1, x1, :lo12:kmsg_path
    mov x2, #0
    mov x3, #0
    mov x8, #56
    svc #0
    tbnz x0, #63, bad_input
    mov x19, x0
    adrp x21, opened
    add x21, x21, :lo12:opened
    mov x22, #opened_length
    bl write_all
read_loop:
    mov x0, x19
    adrp x1, buffer
    add x1, x1, :lo12:buffer
    mov x2, #65536
    mov x8, #63               // read
    svc #0
    cmn x0, #32              // EPIPE: kernel ring overrun
    b.eq read_loop
    cmn x0, #4               // EINTR
    b.eq read_loop
    cmp x0, #0
    b.le bad_read
    mov x22, x0
    adrp x21, buffer
    add x21, x21, :lo12:buffer
    bl write_all
    b read_loop
write_all:
    mov x0, x20
    mov x1, x21
    mov x2, x22
    mov x8, #64               // write; O_DSYNC persists each record
    svc #0
    cmn x0, #4
    b.eq write_all
    cmp x0, #0
    b.le bad_write
    add x21, x21, x0
    sub x22, x22, x0
    cbnz x22, write_all
    ret
bad_args:
    mov x0, #2
    b exit
bad_output:
    mov x0, #3
    b exit
bad_input:
    mov x0, #4
    b exit
bad_read:
    mov x0, #5
    b exit
bad_write:
    mov x0, #6
exit:
    mov x8, #93
    svc #0
.section .rodata
kmsg_path: .asciz "/dev/kmsg"
opened: .ascii "BOOTDIAG: input and output opened with O_DSYNC\n"
.equ opened_length, . - opened
.bss
.balign 16
buffer: .skip 65536
