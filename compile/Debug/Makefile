################################################################################
# Automatically-generated file. Do not edit!
################################################################################

SHELL := cmd.exe
RM := rm -rf

USER_OBJS :=

LIBS := 
PROJ := 

O_SRCS := 
C_SRCS := 
S_SRCS := 
S_UPPER_SRCS := 
OBJ_SRCS := 
ASM_SRCS := 
PREPROCESSING_SRCS := 
OBJS := 
OBJS_AS_ARGS := 
C_DEPS := 
C_DEPS_AS_ARGS := 
EXECUTABLES := 
OUTPUT_FILE_PATH :=
OUTPUT_FILE_PATH_AS_ARGS :=
AVR_APP_PATH :=$$$AVR_APP_PATH$$$
QUOTE := "
ADDITIONAL_DEPENDENCIES:=
OUTPUT_FILE_DEP:=
LIB_DEP:=
LINKER_SCRIPT_DEP:=

# Every subdirectory with source files must be described here
SUBDIRS :=  \
../inc


# Add inputs and outputs from these tool invocations to the build variables 
C_SRCS +=  \
../cmd.c \
../counters.c \
../dfmadapter.c \
../diag.c \
../display.c \
../hidcard.c \
../inputs.c \
../keypad.c \
../log.c \
../brushreader.c \
../magtekreader.c \
../main.c \
../outputs.c \
../speaker.c \
../time.c \
../uart.c


PREPROCESSING_SRCS += 


ASM_SRCS += 


OBJS +=  \
cmd.o \
counters.o \
dfmadapter.o \
diag.o \
display.o \
hidcard.o \
inputs.o \
keypad.o \
log.o \
brushreader.o \
magtekreader.o \
main.o \
outputs.o \
speaker.o \
time.o \
uart.o

OBJS_AS_ARGS +=  \
cmd.o \
counters.o \
dfmadapter.o \
diag.o \
display.o \
hidcard.o \
inputs.o \
keypad.o \
log.o \
brushreader.o \
magtekreader.o \
main.o \
outputs.o \
speaker.o \
time.o \
uart.o

C_DEPS +=  \
cmd.d \
counters.d \
dfmadapter.d \
diag.d \
display.d \
hidcard.d \
inputs.d \
keypad.d \
log.d \
brushreader.d \
magtekreader.d \
main.d \
outputs.d \
speaker.d \
time.d \
uart.d

C_DEPS_AS_ARGS +=  \
cmd.d \
counters.d \
dfmadapter.d \
diag.d \
display.d \
hidcard.d \
inputs.d \
keypad.d \
log.d \
brushreader.d \
magtekreader.d \
main.d \
outputs.d \
speaker.d \
time.d \
uart.d

OUTPUT_FILE_PATH +=new_fb_io_controller.elf

OUTPUT_FILE_PATH_AS_ARGS +=new_fb_io_controller.elf

ADDITIONAL_DEPENDENCIES:=

OUTPUT_FILE_DEP:= ./makedep.mk

LIB_DEP+= 

LINKER_SCRIPT_DEP+= 


# AVR32/GNU C Compiler

































./%.o: .././%.c
	@echo Building file: $<
	@echo Invoking: AVR/GNU C Compiler : 5.4.0
	$(QUOTE)C:\Program Files (x86)\Atmel\Studio\7.0\toolchain\avr8\avr8-gnu-toolchain\bin\avr-gcc.exe$(QUOTE)  -x c -funsigned-char -funsigned-bitfields -DDEBUG -DF_CPU=8000000  -I"C:\Program Files (x86)\Atmel\Studio\7.0\Packs\atmel\ATmega_DFP\1.2.132\include" -I"../inc"  -O1 -ffunction-sections -fdata-sections -fpack-struct -fshort-enums -g2 -Wall -mmcu=atmega640 -B "C:\Program Files (x86)\Atmel\Studio\7.0\Packs\atmel\ATmega_DFP\1.2.132\gcc\dev\atmega640" -c -std=gnu99 -Wno-unknown-pragmas -Werror-implicit-function-declaration -MD -MP -MF "$(@:%.o=%.d)" -MT"$(@:%.o=%.d)" -MT"$(@:%.o=%.o)"   -o "$@" "$<" 
	@echo Finished building: $<
	



# AVR32/GNU Preprocessing Assembler



# AVR32/GNU Assembler




ifneq ($(MAKECMDGOALS),clean)
ifneq ($(strip $(C_DEPS)),)
-include $(C_DEPS)
endif
endif

# Add inputs and outputs from these tool invocations to the build variables 

# All Target
all: $(OUTPUT_FILE_PATH) $(ADDITIONAL_DEPENDENCIES)

$(OUTPUT_FILE_PATH): $(OBJS) $(USER_OBJS) $(OUTPUT_FILE_DEP) $(LIB_DEP) $(LINKER_SCRIPT_DEP)
	@echo Building target: $@
	@echo Invoking: AVR/GNU Linker : 5.4.0
	$(QUOTE)C:\Program Files (x86)\Atmel\Studio\7.0\toolchain\avr8\avr8-gnu-toolchain\bin\avr-gcc.exe$(QUOTE) -o$(OUTPUT_FILE_PATH_AS_ARGS) $(OBJS_AS_ARGS) $(USER_OBJS) $(LIBS) -Wl,-Map="new_fb_io_controller.map" -Wl,--start-group -Wl,-lm  -Wl,--end-group -Wl,--gc-sections -mmcu=atmega640 -B "C:\Program Files (x86)\Atmel\Studio\7.0\Packs\atmel\ATmega_DFP\1.2.132\gcc\dev\atmega640"  
	@echo Finished building target: $@
	"C:\Program Files (x86)\Atmel\Studio\7.0\toolchain\avr8\avr8-gnu-toolchain\bin\avr-objcopy.exe" -O ihex -R .eeprom -R .fuse -R .lock -R .signature -R .user_signatures  "new_fb_io_controller.elf" "new_fb_io_controller.hex"
	"C:\Program Files (x86)\Atmel\Studio\7.0\toolchain\avr8\avr8-gnu-toolchain\bin\avr-objcopy.exe" -j .eeprom  --set-section-flags=.eeprom=alloc,load --change-section-lma .eeprom=0  --no-change-warnings -O ihex "new_fb_io_controller.elf" "new_fb_io_controller.eep" || exit 0
	"C:\Program Files (x86)\Atmel\Studio\7.0\toolchain\avr8\avr8-gnu-toolchain\bin\avr-objdump.exe" -h -S "new_fb_io_controller.elf" > "new_fb_io_controller.lss"
	"C:\Program Files (x86)\Atmel\Studio\7.0\toolchain\avr8\avr8-gnu-toolchain\bin\avr-objcopy.exe" -O srec -R .eeprom -R .fuse -R .lock -R .signature -R .user_signatures "new_fb_io_controller.elf" "new_fb_io_controller.srec"
	"C:\Program Files (x86)\Atmel\Studio\7.0\toolchain\avr8\avr8-gnu-toolchain\bin\avr-size.exe" "new_fb_io_controller.elf"
	
	





# Other Targets
clean:
	-$(RM) $(OBJS_AS_ARGS) $(EXECUTABLES)  
	-$(RM) $(C_DEPS_AS_ARGS)   
	rm -rf "new_fb_io_controller.elf" "new_fb_io_controller.a" "new_fb_io_controller.hex" "new_fb_io_controller.lss" "new_fb_io_controller.eep" "new_fb_io_controller.map" "new_fb_io_controller.srec" "new_fb_io_controller.usersignatures"
	