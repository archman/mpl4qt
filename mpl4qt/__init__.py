# -*- coding: utf-8 -*-

import platform
import matplotlib

d, v, _ = platform.linux_distribution()
if d == 'debian':
    matplotlib.rcParams['agg.path.chunksize'] = 2000

# always use Qt5Agg for mpl < 2.0
if matplotlib.__version__ <= "2.0.0":
    matplotlib.use("Qt5Agg")
#

__authors__ = "Tong Zhang"
__copyright__ = "(c) 2018-2019, Facility for Rare Isotope beams," \
                " Michigan State University"
__contact__ = "Tong Zhang <zhangt@frib.msu.edu>"
__version__ = "2.4.0"
