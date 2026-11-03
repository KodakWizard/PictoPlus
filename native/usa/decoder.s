.syntax unified
.arm
.text
.global decoder_entry
decoder_entry:

        ldr r3,[lr,#4]
        mov r12,#0xe5000000
        orr r12,r12,#0x00910000
        orr r12,r12,#0x1000
        cmp r3,r12
        bne done
        ldr r3,[lr,#8]
        mov r12,#0xe1000000
        orr r12,r12,#0x00500000
        orr r12,r12,#1
        cmp r3,r12
        bne done
        ldr r3,[r2,#-4]
        cmp r3,#0x00100000
        bne done
        ldr r3,[r2,#32]
        mov r12,#0x07000000
        add r12,r12,#0x100
        cmp r3,r12
        bne done
        ldr r3,[r2,#36]
        cmp r3,#1
        movls r3,#1
        strbls r3,[r2,#36]
    done:
        mov r0,#0
        bx lr
    