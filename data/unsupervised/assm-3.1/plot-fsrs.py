import glob
import openmc.mgxs
import openmoc
import openmoc.plotter
from openmoc.opencg_compatible import get_openmoc_geometry
from infermc.energy_groups import group_structures
from discretize import discretize_geometry_standalone


openmoc.log.set_log_level('NORMAL')
opts = openmoc.options.Options()
num_groups = 2

# Initialize a fine (70-)group MGXS Library from OpenMC statepoint data
sp = openmc.StatePoint(glob.glob('statepoint.*.h5')[-1])
cell_mgxs_lib = openmc.mgxs.Library.load_from_file(filename='distribcell')
mat_mgxs_lib = openmc.mgxs.Library.load_from_file(filename='material')
cell_mgxs_lib.load_from_statepoint(sp)
mat_mgxs_lib.load_from_statepoint(sp)

cell_mgxs_lib = cell_mgxs_lib.get_subdomain_avg_library()

# Build a coarse group Library from the fine (70-)group Library
coarse_groups = group_structures['CASMO']['{}-group'.format(num_groups)]
cell_mgxs_lib = cell_mgxs_lib.get_condensed_library(coarse_groups)
mat_mgxs_lib = mat_mgxs_lib.get_condensed_library(coarse_groups)

# Create an OpenMOC Geometry from the OpenCG Geometry
openmoc_geometry = get_openmoc_geometry(cell_mgxs_lib.opencg_geometry)
openmoc.materialize.load_openmc_mgxs_lib(mat_mgxs_lib, openmoc_geometry)
openmoc.materialize.load_openmc_mgxs_lib(cell_mgxs_lib, openmoc_geometry)

# FIXME: Rev your engines for a little discretization....
discretize_geometry_standalone(mat_mgxs_lib, openmoc_geometry)

# Initialize CMFD
cmfd = openmoc.Cmfd()
cmfd.setSORRelaxationFactor(1.5)
cmfd.setLatticeStructure(17,17)
cmfd.setKNearest(3)
openmoc_geometry.setCmfd(cmfd)

# Generate tracks
track_generator = openmoc.TrackGenerator(openmoc_geometry, 32, 0.01)
track_generator.setZCoord(195.)
track_generator.setNumThreads(opts.num_omp_threads)
track_generator.generateTracks()

# Setup plot for discretized fuel pin
max_x = openmoc_geometry.getMaxX()
max_y = openmoc_geometry.getMaxY()
xlim = (max_x-1.25984, max_x)
ylim = (max_y-1.25984, max_y)
openmoc.plotter.plot_cells(openmoc_geometry, zcoord=195., gridsize=2000,
                           xlim=xlim, ylim=ylim, library='pil')

# Setup plot for discretized instrument tube
xlim = (-1.25984/2., +1.25984/2.)
ylim = (-1.25984/2., +1.25984/2.)
openmoc.plotter.plot_cells(openmoc_geometry, zcoord=195., gridsize=2000,
                           xlim=xlim, ylim=ylim, library='pil')

# Setup plot for discretized burnable poison
xlim = (6.2992-1.25984/2., 6.2992+1.25984/2.)
ylim = (6.2992-1.25984/2., 6.2992+1.25984/2.)
openmoc.plotter.plot_cells(openmoc_geometry, zcoord=195., gridsize=2000,
                           xlim=xlim, ylim=ylim, library='pil')

# Plot all FSRs in the geometry
openmoc.plotter.plot_flat_source_regions(openmoc_geometry, gridsize=2000, library='pil')
