# CalculiX Runner
This software is meant to be used in addition with PrePoMax, but can also be used to monitor Calculix processes.

## Features
- Monitor the CalculiX solution status and plot residuals in real time
- run a complex frequency analysis by parametrizing the revolution speed of a coriolis bc and plotting the results as a campbell plot

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
- General
    - [ ] Handle Unit Conversions
- Solution Monitor
    - [x] Static Analysis parsing
    - [ ] Frequency Anlysis parsing
    - [x] Dynamic Analysis parsing
    - [x] stop a running analysis inside a different thread
- Complex Analysis
    - [x] Automatically insert `*COMPLEX FREQUENCY, CORIOLIS` Step for Complex Frequency Analysis if needed
    - [x] save project data in temporary directory that automatically deletes itself afterwards
    - [x] Figure out a way to correctly identify modes between seperate runs
    - [ ] Implement an output window that shows the current status
