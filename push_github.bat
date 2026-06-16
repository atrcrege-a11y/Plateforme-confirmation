@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================================
echo  Envoi du projet vers GitHub
echo ============================================================
echo.

rem --- nettoyer un eventuel verrou git laisse par un essai precedent ---
if exist ".git\config.lock" (
  echo Suppression d'un verrou git residuel...
  del /f /q ".git\config.lock"
)

git --version >nul 2>&1
if errorlevel 1 (
  echo [ERREUR] Git introuvable. Installe Git puis relance ce script.
  pause
  exit /b 1
)

rem --- identite git locale si absente ---
git config user.email >nul 2>&1 || git config user.email "atrcrege@gmail.com"
git config user.name  >nul 2>&1 || git config user.name  "Clement"

rem --- init si besoin ---
if not exist ".git" (
  echo Initialisation du depot local...
  git init
  git branch -M main
)

echo Ajout des fichiers (secrets et *.db exclus par .gitignore)...
git add .
git commit -m "Plateforme confirmation - phases 1 a 3 + bundle prod PythonAnywhere"

echo.
echo === CONTROLE SECRETS : la liste suivante doit etre VIDE ===
git ls-files | findstr /i "prod_settings.py .db"
echo === (si rien n'apparait ci-dessus, aucun secret n'est suivi : OK) ===
echo.

rem --- remote fixe vers ton depot ---
git remote remove origin >nul 2>&1
git remote add origin https://github.com/atrcrege-a11y/Plateforme-confirmation.git

echo Envoi vers GitHub (une fenetre de connexion GitHub va s'ouvrir : connecte-toi)...
git push -u origin main

echo.
echo ============================================================
echo  Termine. Verifie sur GitHub que prod_settings.py et les .db
echo  N'Y SONT PAS (seul prod_settings_example.py doit apparaitre).
echo ============================================================
pause
