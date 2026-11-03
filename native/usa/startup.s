/* Derived from ArticBaseServer's 3gx_crt0.s (MPL-2.0).
 * https://mozilla.org/MPL/2.0/
 * Restore the plugin-loader frame, use a private runtime heap, then resume
 * the game's original entry point. Never call libc exit/svcExitProcess.
 */
.cpu mpcore
.section .crt0,"ax"
.arm
.align 2
.global _start, __service_ptr, __apt_appid, __ctru_heap_size
.global __ctru_linear_heap_size, __system_arglist, __system_runflags
_start:
    b startup
    .ascii "_prm"
__service_ptr: .word 0
__apt_appid: .word 0x300
__ctru_heap_size: .word 0
__ctru_linear_heap_size: .word 0
__system_arglist: .word 0
__system_runflags: .word 0
startup:
    add sp, sp, #4
    ldmfd sp!, {r0}
    msr cpsr_f, r0
    ldmfd sp!, {r0-r12}
    stmfd sp!, {r0-r12}
    mrs r0, cpsr
    stmfd sp!, {r0}
    mov r4, sp
    ldr r0, =__bss_start__
    ldr r1, =__bss_end__
    mov r2, #0
clear:
    cmp r0, r1
    strlo r2, [r0], #4
    blo clear
    ldr r0, =game_stack
    str r4, [r0]
    mov r0, #0
    bl initSystem
    mov r0, #0
    mov r1, #0
    ldr r2, =deferred_stack
    str sp, [r2]
    bl main
    nop
    ldr r0, =game_stack
    ldr sp, [r0]
    ldmfd sp!, {r0}
    msr cpsr_f, r0
    ldmfd sp!, {r0-r12}
    ldr pc, =0x00100000
.section .bss.game_stack,"aw",%nobits
.align 2
game_stack: .space 4
