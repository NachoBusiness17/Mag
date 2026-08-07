@echo off
REM Pull all public gstdcoin org repos into reference\gstdcoin\
setlocal
cd /d "%~dp0.."
if not exist "reference\gstdcoin" mkdir "reference\gstdcoin"
cd reference\gstdcoin

for %%R in (ai web A2A gstd-bridge gstdbot contracts) do (
  if exist "%%R\.git" (
    echo ==^> pull %%R
    git -C "%%R" pull --ff-only
  ) else (
    echo ==^> clone %%R
    git clone --depth 1 https://github.com/gstdcoin/%%R.git "%%R"
  )
)

echo Done. Index: docs\ref\GSTDCOIN_REPOS_INDEX.md
