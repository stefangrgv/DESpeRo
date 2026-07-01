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
COMP_LINE_IDENTIFICATION_FIT_WINDOW_HW = 30  # half-width in px
