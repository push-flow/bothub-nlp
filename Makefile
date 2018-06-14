ENVIRONMENT_VARS_FILE := .env
DJANGO_SETTINGS_MODULE := bothub.settings
EXTRA_LANGUAGE_MODELS_REPOSITORY := https://github.com/push-flow/spacy-lang-models.git
EXTRA_LANGUAGE_MODELS_REPOSITORY_DIR := ./extra-models/
EXTRA_LANGUAGE_MODELS_DIR := "${EXTRA_LANGUAGE_MODELS_REPOSITORY_DIR}models/"
IS_PRODUCTION ?= false
CHECK_ENVIRONMENT := true


# Commands

help:
	@cat Makefile-help.txt
	@exit 0

check_environment:
	@if [[ ${CHECK_ENVIRONMENT} = true ]]; then make _check_environment; fi

install_requirements:
	@if [[ ${IS_PRODUCTION} = true ]]; \
		then make install_production_requirements; \
		else make install_development_requirements; fi

lint:
	@make development_mode_guard
	@make check_environment
	@pipenv run flake8
	@echo "${SUCCESS}✔${NC} The code is following the PEP8"

test:
	@make development_mode_guard
	@make check_environment
	@make migrate CHECK_ENVIRONMENT=false
	@pipenv run coverage run -m unittest && pipenv run coverage report -m

migrate:
	@make check_environment
	@if [[ ${IS_PRODUCTION} = true ]]; \
		then DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE}" django-admin migrate; \
		else DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE}" pipenv run django-admin migrate; fi

clone_extra_language_models_repository:
	@echo "${INFO}Cloning extra language models repository:${NC}"
	@echo "  From: ${EXTRA_LANGUAGE_MODELS_REPOSITORY}"
	@git clone --depth 1 --single-branch "${EXTRA_LANGUAGE_MODELS_REPOSITORY}" "${EXTRA_LANGUAGE_MODELS_REPOSITORY_DIR}" \
		&& echo "${SUCCESS}✔${NC} Repository cloned"

import_languages:
	@make check_environment
	@if [[ ${IS_PRODUCTION} = true ]]; \
		then python -m bothub-nlp import_supported_languages -e="${EXTRA_LANGUAGE_MODELS_DIR}"; \
		else pipenv run python -m bothub-nlp import_supported_languages -e="${EXTRA_LANGUAGE_MODELS_DIR}"; fi

start:
	@make check_environment
	@make migrate CHECK_ENVIRONMENT=false
	@@if [[ ${IS_PRODUCTION} = true ]]; \
		then python -m bothub-nlp start; \
		else pipenv run python -m tornado.autoreload -m bothub-nlp.cli.start; fi


# Utils

## Colors
SUCCESS = \033[0;32m
INFO = \033[0;36m
WARNING = \033[0;33m
DANGER = \033[0;31m
NC = \033[0m

create_environment_vars_file:
	@echo "SECRET_KEY=SK" > "${ENVIRONMENT_VARS_FILE}"
	@echo "DEBUG=true" >> "${ENVIRONMENT_VARS_FILE}"
	@echo "SUPPORTED_LANGUAGES=en de es pt fr it nl" >> "${ENVIRONMENT_VARS_FILE}"
	@echo "${SUCCESS}✔${NC} Settings file created"

install_development_requirements:
	@echo "${INFO}Installing development requirements...${NC}"
	@pipenv install --dev &> /dev/null
	@echo "${SUCCESS}✔${NC} Development requirements installed"

install_production_requirements:
	@echo "${INFO}Installing production requirements...${NC}"
	@pipenv install --system
	@echo "${SUCCESS}✔${NC} Requirements installed"

development_mode_guard:
	@(${IS_PRODUCTION} && echo "${DANGER}Just run this command in development mode${NC}" && exit 1) || exit 0


# Checkers

_check_environment:
	@type pipenv &> /dev/null || (echo "${DANGER}☓${NC} Install pipenv to continue..." && exit 1)
	@echo "${SUCCESS}✔${NC} pipenv installed"
	@if [[ ! -f "${ENVIRONMENT_VARS_FILE}" && ${IS_PRODUCTION} = false ]]; then make create_environment_vars_file; fi
	@make install_requirements
	@echo "${SUCCESS}✔${NC} Environment checked"