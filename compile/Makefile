# AVR 8-bit Toolchain Makefile
# Copyright (C) 2016- All-Line Equipment Company/Steven Hidy
# shidy@all-lineequipment.com
#
# vim:noet:ft=make:sw=8 ts=8
#
# Targets:
#
#	<none>/all	Build all
#	clean		Cleans all build files
#	program		Program target device
#	fuses		Program target device fuses
#	final		Program target device fuses, memory and bootloader
#	gccversion	Display avr-gcc version


# Microcontroller selection and fuse settings
MCU = atmega640
MCU_LFUSE = 0xFF
MCU_HFUSE = 0xD0
MCU_EFUSE = 0xFC

# CPU frequency
F_CPU = 8000000

# Project configuration
FORMAT = ihex
TARGET = main
OBJDIR = obj
SRC = $(TARGET).c $(sort $(wildcard *.c))
CPPSRC = $(wildcard *.cpp)
ASRC =
OPT = s
DEBUG = dwarf-2
EXTRAINCDIRS = inc
CSTANDARD = -std=gnu11
CDEFS = -DF_CPU=$(F_CPU)UL
ADEFS = -DF_CPU=$(F_CPU)
CPPDEFS = -DF_CPU=$(F_CPU)UL

# C flags
CFLAGS = -g$(DEBUG)
CFLAGS += $(CDEFS)
CFLAGS += -O$(OPT)
CFLAGS += -funsigned-char
CFLAGS += -funsigned-bitfields
CFLAGS += -fpack-struct
CFLAGS += -fshort-enums
CFLAGS += -ffunction-sections
CFLAGS += -fdata-sections
CFLAGS += -Wall
CFLAGS += -Werror
CFLAGS += -Wno-unknown-pragmas
CFLAGS += -Wno-unused-variable
CFLAGS += -Wno-unused-but-set-variable
CFLAGS += -Wno-unused-function
CFLAGS += -Wno-strict-prototypes
CFLAGS += -Wa,-adhlns=$(<:%.c=$(OBJDIR)/%.lst)
CFLAGS += $(patsubst %,-I%,$(EXTRAINCDIRS))
CFLAGS += $(CSTANDARD)


# C++ flags
CPPFLAGS = -g$(DEBUG)
CPPFLAGS += $(CPPDEFS)
CPPFLAGS += -O$(OPT)
CPPFLAGS += -funsigned-char
CPPFLAGS += -funsigned-bitfields
CPPFLAGS += -fpack-struct
CPPFLAGS += -fshort-enums
CPPFLAGS += -fno-exceptions
CPPFLAGS += -Wall
CPPFLAGS += -Wstrict-prototypes
CPPFLAGS += -Werror
CPPFLAGS += -Wundef
CPPFLAGS += -Wa,-adhlns=$(<:%.cpp=$(OBJDIR)/%.lst)
CPPFLAGS += $(patsubst %,-I%,$(EXTRAINCDIRS))
CPPFLAGS += $(CSTANDARD)

# Assembler flags
ASFLAGS = $(ADEFS) -Wa,-adhlns=$(<:%.S=$(OBJDIR)/%.lst),-gstabs,--listing-cont-lines=100

# Library configuration
MATH_LIB = -lm
EXTRALIBDIRS =

# External memory configuration
EXTMEMOPTS =

# Linker options
LDFLAGS = -Wl,-Map=$(TARGET).map,--cref,--relax,--gc-sections
LDFLAGS += $(EXTMEMOPTS)
LDFLAGS += $(patsubst %,-L%,$(EXTRALIBDIRS))
LDFLAGS += $(PRINTF_LIB) $(SCANF_LIB) $(MATH_LIB)

# AVRdude options
AVRDUDE_PROGRAMMER = stk500v2
AVRDUDE_PORT = com11
AVRDUDE_WRITE_FLASH = -U flash:w:$(TARGET).hex
#AVRDUDE_WRITE_EEPROM = -U eeprom:w:$(TARGET).eep
#AVRDUDE_ERASE_COUNTER = -y
#AVRDUDE_NO_VERIFY = -V
#AVRDUDE_VERBOSE = -v -v
AVRDUDE_SPEED = -B 1
AVRDUDE_FLAGS = -p $(MCU) -P $(AVRDUDE_PORT) -c $(AVRDUDE_PROGRAMMER)
AVRDUDE_FLAGS += $(AVRDUDE_NO_VERIFY)
AVRDUDE_FLAGS += $(AVRDUDE_SPEED)
AVRDUDE_FLAGS += $(AVRDUDE_VERBOSE)
AVRDUDE_FLAGS += $(AVRDUDE_ERASE_COUNTER)

# These are aliases to allow this makefile to move between platforms
# with minimal changes
SHELL = sh
QUIET = @
CC = $(QUIET)avr-gcc
OBJCOPY = $(QUIET)avr-objcopy
OBJDUMP = $(QUIET)avr-objdump
SIZE = avr-size
AR = $(QUIET)avr-ar rcs
NM = $(QUIET)avr-nm
AVRDUDE = avrdude
REMOVE = rm -f
REMOVEDIR = rm -rf
COPY = cp
WINSHELL = cmd

# English text messages
ESC=`printf "\x1b"`
WHITE_TEXT = "$(ESC)[37;1m"
GRAY_TEXT = "$(ESC)[37;0m"
MSG_ERRORS_NONE = Errors: none
MSG_BEGIN = Beginning compilation...
MSG_END = Compilation is complete.
MSG_SIZE_BEFORE = Size before:
MSG_SIZE_AFTER = Size after:
MSG_COFF = Converting to AVR COFF:
MSG_EXTENDED_COFF = Converting to AVR Extended COFF:
MSG_FLASH = Creating load file for Flash: $(WHITE_TEXT)
MSG_FLASH_END = $(GRAY_TEXT)
MSG_EEPROM = Creating load file for EEPROM: $(WHITE_TEXT)
MSG_EEPROM_END = $(GRAY_TEXT)
MSG_EXTENDED_LISTING = Creating Extended Listing:
MSG_SYMBOL_TABLE = Creating Symbol Table:
MSG_LINKING = Linking: $(WHITE_TEXT)
MSG_LINKING_END = $(GRAY_TEXT)
MSG_COMPILING = Compiling C: $(WHITE_TEXT)
MSG_COMPILING_CPP = Compiling C++:
MSG_COMPILING_END = $(GRAY_TEXT)
MSG_ASSEMBLING = Assembling:
MSG_DOCUMENTING = Documenting:
MSG_CLEANING = Cleaning project:
MSG_CREATING_LIBRARY = Creating library:

# Define all object files, listing files, dependency stuff
OBJ = $(SRC:%.c=$(OBJDIR)/%.o) $(CPPSRC:%.cpp=$(OBJDIR)/%.o) $(ASRC:%.S=$(OBJDIR)/%.o)
LST = $(SRC:%.c=$(OBJDIR)/%.lst) $(CPPSRC:%.cpp=$(OBJDIR)/%.lst) $(ASRC:%.S=$(OBJDIR)/%.lst)
GENDEPFLAGS = -MMD -MP -MF .dep/$(@F).d

# All flags
ALL_CFLAGS = -mmcu=$(MCU) -I. $(CFLAGS) $(GENDEPFLAGS)
ALL_CPPFLAGS = -mmcu=$(MCU) -I. -x c++ $(CPPFLAGS) $(GENDEPFLAGS)
ALL_ASFLAGS = -mmcu=$(MCU) -I. -x assembler-with-cpp $(ASFLAGS)

# Default target and other targets
all: begin gccversion sizebefore build sizeafter end
build: hex eep
elf: $(TARGET).elf
hex: $(TARGET).hex
eep: $(TARGET).eep
lss: $(TARGET).lss
sym: $(TARGET).sym
LIBNAME=lib$(TARGET).a
lib: $(LIBNAME)

# Beginning and ending banner
begin:
	@echo
	@echo $(MSG_BEGIN)

end:
	@echo $(MSG_END)
	@echo

# Show the the size of the output file before and after compilation
HEXSIZE = $(SIZE) --target=$(FORMAT) $(TARGET).hex
ELFSIZE = $(SIZE) --mcu=$(MCU) --format=avr $(TARGET).elf

sizebefore:
	@if test -f $(TARGET).elf; then echo; echo $(MSG_SIZE_BEFORE); $(ELFSIZE); \
	2>/dev/null; echo; fi

sizeafter:
	@if test -f $(TARGET).elf; then echo; echo $(MSG_SIZE_AFTER); $(ELFSIZE); \
	2>/dev/null; echo; fi

# Compiler version
gccversion :
	@$(CC) --version

# Device programming
program: $(TARGET).hex $(TARGET).eep
	$(AVRDUDE) $(AVRDUDE_FLAGS) $(AVRDUDE_WRITE_FLASH) $(AVRDUDE_WRITE_EEPROM)

buildfinal: $(TARGET).hex
	srec_cat boot/bootloader.hex -I main.hex -I -o application.hex -I

final: fuses buildfinal
	sleep 2
	$(AVRDUDE) $(AVRDUDE_FLAGS) -U flash:w:application.hex $(AVRDUDE_WRITE_EEPROM)

fuses:
	$(AVRDUDE) $(AVRDUDE_FLAGS) -B 32 -U lfuse:w:$(MCU_LFUSE):m -U hfuse:w:$(MCU_HFUSE):m -U efuse:w:$(MCU_EFUSE):m

# Final output files
%.hex: %.elf
	@echo
	@echo $(MSG_FLASH) $@ $(MSG_FLASH_END)
	$(OBJCOPY) -O $(FORMAT) -R .eeprom -R .fuse -R .lock $< $@

%.eep: %.elf
	@echo
	@echo $(MSG_EEPROM) $@ $(MSG_EEPROM_END)
	-$(OBJCOPY) -j .eeprom --set-section-flags=.eeprom="alloc,load" \
	--change-section-lma .eeprom=0 --no-change-warnings -O $(FORMAT) $< $@ || exit 0

# Extended listing
%.lss: %.elf
	@echo
	@echo $(MSG_EXTENDED_LISTING) $@
	$(OBJDUMP) -h -S -z $< > $@

# Symbol table
%.sym: %.elf
	@echo
	@echo $(MSG_SYMBOL_TABLE) $@
	$(NM) -n $< > $@



# Create library from object files.
.SECONDARY : $(TARGET).a
.PRECIOUS : $(OBJ)
%.a: $(OBJ)
	@echo
	@echo $(MSG_CREATING_LIBRARY) $@
	$(AR) $@ $(OBJ)


# Link: create ELF output file from object files.
.SECONDARY : $(TARGET).elf
.PRECIOUS : $(OBJ)
%.elf: $(OBJ)
	@echo $(MSG_LINKING) $@ $(MSG_LINKING_END)
	$(CC) $(ALL_CFLAGS) $^ --output $@ $(LDFLAGS)


# Compile: create object files from C source files.
$(OBJDIR)/%.o : %.c
	@echo $(MSG_COMPILING) $< $(MSG_COMPILING_END)
	$(CC) -c $(ALL_CFLAGS) $< -o $@


# Compile: create object files from C++ source files.
$(OBJDIR)/%.o : %.cpp
	@echo $(MSG_COMPILING_CPP) $< $(MSG_COMPILING_END)
	$(CC) -c $(ALL_CPPFLAGS) $< -o $@


# Compile: create assembler files from C source files.
%.s : %.c
	$(CC) -S $(ALL_CFLAGS) $< -o $@


# Compile: create assembler files from C++ source files.
%.s : %.cpp
	$(CC) -S $(ALL_CPPFLAGS) $< -o $@


# Assemble: create object files from assembler source files.
$(OBJDIR)/%.o : %.S
	@echo $(MSG_ASSEMBLING) $<
	$(CC) -c $(ALL_ASFLAGS) $< -o $@


# Create preprocessed source for use in sending a bug report.
%.i : %.c
	$(CC) -E -mmcu=$(MCU) -I. $(CFLAGS) $< -o $@

# Target: clean project.
clean: begin clean_list end

clean_list :
	@echo
	@echo $(MSG_CLEANING)
	$(REMOVE) $(TARGET).hex
	$(REMOVE) $(TARGET).eep
	$(REMOVE) $(TARGET).cof
	$(REMOVE) $(TARGET).elf
	$(REMOVE) $(TARGET).map
	$(REMOVE) $(TARGET).sym
	$(REMOVE) $(TARGET).lss
	$(REMOVE) $(OBJDIR)/*.*
	$(REMOVEDIR) .dep


# Create object files directory
$(shell mkdir $(OBJDIR) 2>/dev/null)


# Include the dependency files.
-include $(shell mkdir .dep 2>/dev/null) $(wildcard .dep/*)


# Listing of phony targets.
.PHONY : all begin finish end sizebefore sizeafter gccversion fuses \
build elf hex eep lss sym \
clean clean_list program debug gdb-config \


