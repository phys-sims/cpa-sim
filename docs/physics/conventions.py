# this doc specifies units and conventions (backend and API) for cpa-sim

# internal units
# time: fs (s*10**-15) - allows for accurate description of fs-ps pulsed lasers
# space: um (m*10**-6) - enables beam waist and wavelength to be numerically stable
# angle: rad
# everything else is derived from here (eg: w: rad/fs, c=0.299792458, )

# fiber
# GDD > 0: stretching, GDD < 0: compression


# amp


# free space
# spot radius at beam waist: 1/(e**2) of max value; this complies with abcdef-sim
# (martinez formalism)
# ***review termonlogy (beam waist vs beam waist radius vs beam waist radius min vs spot size etc)
# gratings: **** review plymouth vs newport conventions for grating orders and equation*****
