@echo off
REM ============================================================
REM  run_update.bat - Mise a jour de NewsMood (articles, prix, sentiment)
REM  Lance par le Planificateur de taches Windows, 2 fois par jour.
REM  Tout ce qui s'affiche est ajoute au fichier logs\update.log
REM ============================================================

REM Se placer dans le dossier du projet (%~dp0 = dossier de ce fichier .bat)
cd /d "%~dp0"

REM Creer le dossier logs s'il n'existe pas encore
if not exist logs mkdir logs

REM Ecrire les sorties en UTF-8 (evite les erreurs avec les caracteres speciaux)
set PYTHONIOENCODING=utf-8

echo ============================================================ >> logs\update.log
echo Lancement : %date% %time% >> logs\update.log

REM On utilise directement le Python du venv : pas besoin de l'activer
REM 2>&1 : les messages d'erreur vont aussi dans le journal
"%~dp0venv\Scripts\python.exe" -m src.update >> logs\update.log 2>&1

echo Code de sortie : %errorlevel% >> logs\update.log