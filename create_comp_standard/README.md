# Creating a new comparison standard

In order to create a new comparison standard, you first need an extracted 2D comparison spectrum (intensity vs pixel number for each echelle order). This spectrum must be a `src.store.observation.Observation` object, which the script expects is to be stored in a file named `raw_comp_standard.npy`. To extract the spectrum in such a format, you need to simply run DESpeRo on the raw comparison spectrum and save the result obtained with the `src.apall.extract_2d_spectra` method.

The line positions must be described in the `lines.py` file in the same format as the one used for ESpeRo: each key in the `lines` dict corresponds to the order number, and its value is a ND list containing 2D lists, where the 0-th item is the pixel number and the 1-st item is the wavelength, e.g.

```
3: [
    [386, 8264.511],
    [1151, 8320.8546],
    [1288, 8330.4476],
    [1758, 8358.7242],
],
```

You can use the script `create_comp_standard.py` to then create the final comparison standard, as well as to check your solution using the plots provided for each echelle order.

