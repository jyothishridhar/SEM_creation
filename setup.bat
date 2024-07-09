@echo off

echo [general]> "%userprofile%\.streamlit\credentials.toml"
echo email = "jyothishridhar0625@gmail.com">> "%userprofile%\.streamlit\credentials.toml"

echo [server]> "%userprofile%\.streamlit\config.toml"
echo headless = true>> "%userprofile%\.streamlit\config.toml"
<<<<<<< HEAD
echo port = %PORT%>> "%userprofile%\.streamlit\config.toml"
=======
echo port = %PORT%>> "%userprofile%\.streamlit\config.toml"
>>>>>>> 7ef3263bf8ad3edda12247249d99ea6f271604bd
