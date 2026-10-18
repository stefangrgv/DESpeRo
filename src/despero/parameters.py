################################################################################
#   GENERAL PARAMETERS
################################################################################
APERTURE_HEIGHT = 6  # actual window is 2*(APERTURE_HEIGHT - 1) - 1
NUMBER_OF_ECHELLE_ORDERS = 67
CUTOFF = 20  # number of columns to cut off from the left and right end

################################################################################
#   COMPARISON SPECTRA CALIBRATION
################################################################################
COMP_MATCHING_LINE_DISTANCE_TOLERANCE = 0.5  # in px
COMP_MATCHING_LINE_COLUMN_TOLERANCE = 0.25  # in px
COMP_MATCHING_MAX_ADJACENT_ORDERS = 25  # only compare this number of neighboring orders on each side
# discard the end N orders (usually the end orders have low SNR and few lines, so they add noise)
COMP_MATCHING_DISCARD_EDGE_N_ORDERS = 10
# limit the number of automatically identified lines (otherwise it can grow up to a few hundred)
COMP_MATCHING_KEEP_STRONGEST_N_LINES_IN_COMP = 6
COMP_SHIFT_OUTLIER_TOLERANCE = 5  # in px; order shifts this far from the median shift are replaced by it
COMP_LINE_IDENTIFICATION_FIT_WINDOW_HW = 30  # half-width in px
COMP_LINE_IDENTIFICATION_FIT_WINDOW_HW_STRICT = 6  # half-width in px (~3 sigma of a ThAr line)
# 2D wavelength solution (wavelength * m = P(column, m)); degrees chosen by cross-validation on ThAr lines
ECHELLE_FIT_DEGREE_COLUMN = 4
ECHELLE_FIT_DEGREE_ORDER = 3
ECHELLE_FIT_CLIP_SIGMA = 4.0  # lines with residuals above this many robust sigmas are iteratively rejected
ECHELLE_FIT_MIN_CLIP = 0.5  # in km/s; never reject lines with residuals below this
