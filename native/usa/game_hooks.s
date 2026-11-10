#include "game_region.h"
/* Long-range ARM trampolines: preserve the game's complete call frame. */
.cpu mpcore
.arm
.text
.align 2
.global native_mount_hook, native_open_hook, native_save_hook
native_mount_hook:
    cmp r3, #3
    bne mount_continue
    push {r0-r12,lr}
    bl native_mount_sd
    pop {r0-r12,lr}
mount_continue:
    ldr pc, =direct_trampoline
native_open_hook:
    push {r0-r12,lr}
    bl native_redirect_open
    cmp r0, #1
    pop {r0-r12,lr}
    moveq r0, #0
    bxeq lr
    ldr pc, =open_trampoline
native_save_hook:
    push {r0-r12,lr}
    mov r0, r7
    mov r1, r8
    bl native_prune_books
    pop {r0-r12,lr}
    ldr pc, =PP_SAVE_CONTINUE

/* At the final bounds call, the live QPP pointer is in the caller's frame.
 * The game copies its ID into the state later, so read it from the QPP. */
.global native_slicer_bounds_hook
native_slicer_bounds_hook:
    ldr r1,[sp,#12]
    ldr r1,[r1,#4]
    b native_slicer_grid_bounds

.global native_save_write_hook
native_save_write_hook:
    push {r0-r12,lr}
    bl native_store_progress
    cmp r0,#0
    pop {r0-r12,lr}
    moveq r0,#0
    bxeq lr
    ldr pc,=save_write_trampoline

.global native_save_dirty_hook
native_save_dirty_hook:
 push {r0-r12,lr}
 bl native_progress_dirty
 pop {r0-r12,lr}
 ldr pc,=save_dirty_trampoline

.cpu mpcore
.fpu vfp
.arm
.text
.align 2
.global deferred_startup_hook
deferred_startup_hook:
 /* Execute the original native graphics initializer with the original r0. */
 push {r4,lr}
 ldr r12,=PP_GRAPHICS_INIT
 blx r12
 pop {r4,lr}
 push {r0-r12,lr}
 mrs r0,cpsr
 vmrs r1,fpscr
 push {r0,r1}
 vpush {d0-d15}
 mov r4,sp
 ldr r0,=deferred_stack
 ldr sp,[r0]
 /* The plugin's private stack is retained until this one-shot callback. */
 push {r4,lr}
 bl deferred_prepare_books
 pop {r4,lr}
 mov sp,r4
 vpop {d0-d15}
 pop {r0,r1}
 vmsr fpscr,r1
 msr cpsr_f,r0
 pop {r0-r12,lr}
 bx lr
.bss
.align 2
.global deferred_stack
deferred_stack: .space 4
