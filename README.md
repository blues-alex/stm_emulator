### STM device emulator for True Spectrum

#### For use:
``` sh
git clone {this_repository}
pip3 install poetry
cd stm_emulator
poetry env use python3.7 # or ^3.7
poetry shell
poetry install
python3 ./emulatorStart.py ${/dev/tnt[X]}
```
