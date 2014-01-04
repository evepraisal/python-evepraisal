all: compile_translations

compile_translations:
	@pybabel compile -d evepraisal/translations

extract_translations:
	@pybabel compile -d evepraisal/translations

.PHONY: all extract_translations compile_translations