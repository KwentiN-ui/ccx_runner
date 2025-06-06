# CalculiX Runner
This software is meant to be used in addition with PrePoMax, but can also be used to monitor Calculix processes.

## Features
- Monitor the Solution Status and Plot residuals
## Installation
### Option 1: Using `pipx` (recommended)
1. Install [pipx](https://pipx.pypa.io/stable/)
2. Run
```bash
pipx install git+https://github.com/KwentiN-ui/ccx_runner.git
```

### Option 2: Build using `pyinstaller`
1. Clone the repository
2. Setup a virtual environment and install the dependencies in `requirement.txt`
3. Run `buildscript.py`
4. The binary executable should appear in `./dist`

## Todo
- Solution Monitor
    - [x] Static Analysis parsing
    - [ ] Frequency Anlysis parsing
    - [x] Dynamic Analysis parsing
- Complex Analysis
    - [ ] Automatically insert `*COMPLEX FREQUENCY, CORIOLIS` Step for Complex Frequency Analysis if needed
    - [ ] save project data in temporary directory that automatically deletes itself afterwards
    - [ ] Figure out a way to correctly identify modes between seperate runs
