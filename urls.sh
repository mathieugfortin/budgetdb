#!/usr/bin/env bash
python manage.py show_urls >> budgetdb/notes/urls.txt
code-server budgetdb/notes/urls.txt

