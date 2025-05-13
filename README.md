## DESpeRo

**DESpeRo** (Data reduction software for the Echelle Spectrograph Rozhen) is a fully automated data reduction software for the high-resolution echelle spectrograph ESpeRo that operates on the 2m-telescope of the Rozhen National Astronomical Observatory, Bulgarian Academy of Sciences. The pipeline applies the standard preprocessing corrections to the observational data, including cosmic ray removal, bias subtraction, and flat-field correction. It further identifies  and extracts the echelle orders and calibrates the extracted spectra for wavelength.  In addition, it provides the option to normalize the obtained spectra of the individual echelle orders by intensity and to merge them into a continuous one-dimensional spectrum spanning the full spectral range of the instrument.

## Installation

1. Download the latest version from [this link](https://github.com/stefangrgv/DESpeRo/archive/refs/heads/main.zip). Extract the archive in a directory of your choosing.
2. DEspeRo requires python 3.11. You can download it from [the official python website](https://www.python.org/downloads/release/python-3110/) or use the following command in terminal (ubuntu only):
`sudo apt install python3.11`

3. Create a python virtual environment for the project. In a terminal, open the directory where you extracted DESpeRo and run:
`python3.11 -m venv venv`

3. Activate the virtual environment:
`source venv/bin/activate`

**The virtual environment must be active every time you attempt to start the program.**

4. Install the software by running
`pip install .`

## Running DESpeRo

1. Make sure the virtual environment is active
2. Start the program by running
`python despero.py`


## Feedback

For any feedback, contact me via email: sgeorgiev@astro.bas.bg
## DESpeRo

**DESpeRo** (Data reduction software for the Echelle Spectrograph Rozhen) is a fully automated data reduction software for the high-resolution echelle spectrograph ESpeRo that operates on the 2m-telescope of the Rozhen National Astronomical Observatory, Bulgarian Academy of Sciences. The pipeline applies the standard preprocessing corrections to the observational data, including cosmic ray removal, bias subtraction, and flat-field correction. It further identifies  and extracts the echelle orders and calibrates the extracted spectra for wavelength.  In addition, it provides the option to normalize the obtained spectra of the individual echelle orders by intensity and to merge them into a continuous one-dimensional spectrum spanning the full spectral range of the instrument.

## Installation

1. Download the latest version from [this link](https://github.com/stefangrgv/DESpeRo/archive/refs/heads/main.zip). Extract the archive in a directory of your choosing.
2. DEspeRo requires python 3.11. You can download it from [the official python website](https://www.python.org/downloads/release/python-3110/) or use the following command in terminal (ubuntu only):
`sudo apt install python3.11`

3. Create a python virtual environment for the project. In a terminal, open the directory where you extracted DESpeRo and run:
`python3.11 -m venv venv`

4. Activate the virtual environment (it must be active every time you attempt to start the program):
`source venv/bin/activate`

5. Install the software by running
`pip install .`

## Running DESpeRo

1. Make sure the virtual environment is active
2. Start the program by running
`python despero.py`


## Feedback

For any feedback, contact me via email: sgeorgiev@astro.bas.bg

