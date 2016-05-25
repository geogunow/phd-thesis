import os
import re

import numpy as np
import matplotlib

# Force headless backend for plotting on clusters
matplotlib.use('Agg')

import matplotlib.pyplot as plt
import seaborn as sns

import openmc.mgxs
import openmc.opencg_compatible
import openmoc
import openmoc.opencg_compatible
from infermc.energy_groups import group_structures
import pyne.ace

# Force non-interactive mode for plotting on clusters
plt.ioff()

sns.set_style('ticks')


openmoc.log.set_log_level('NORMAL')
opts = openmoc.options.Options()

# Query the user for the number of energy groups
scatter = 'iso-in-lab'
mesh = 32
num_groups = 70

directory = '{}/{}x'.format(scatter, mesh)

# Create an OpenMOC Geometry from the OpenCG Geometry
mgxs_lib = openmc.mgxs.Library.load_from_file(directory=directory)
openmoc_geometry = \
    openmoc.opencg_compatible.get_openmoc_geometry(mgxs_lib.opencg_geometry)

coarse_groups = group_structures['CASMO']['{}-group'.format(num_groups)]
mgxs_lib = mgxs_lib.get_condensed_library(coarse_groups)
openmoc_materials = \
    openmoc.materialize.load_openmc_mgxs_lib(mgxs_lib, openmoc_geometry)

# Initialize an OpenMOC TrackGenerator and Solver
track_generator = openmoc.TrackGenerator(openmoc_geometry, 128, 0.05)
track_generator.setNumThreads(opts.num_omp_threads)
track_generator.generateTracks()

# Initialize an OpenMOC Solver
solver = openmoc.CPUSolver(track_generator)
solver.setConvergenceThreshold(1E-7)
solver.setNumThreads(opts.num_omp_threads)

# Run an eigenvalue calulation with the MGXS from OpenMC
solver.computeEigenvalue(opts.max_iters)
solver.printTimerReport()


###############################################################################
#                         Extracting Scalar Fluxes
###############################################################################

openmoc.log.py_printf('NORMAL', 'Plotting data...')

# Extract the OpenMOC scalar fluxes
openmoc_fluxes = openmoc.process.get_scalar_fluxes(solver)

# Extract the OpenMC scalar fluxes
num_fsrs = openmoc_geometry.getNumFSRs()
num_groups = openmoc_geometry.getNumEnergyGroups()
openmc_fluxes = np.zeros((num_fsrs, num_groups), dtype=np.float64)

# Get the OpenMC flux in each FSR
for fsr in range(num_fsrs):

    # Find the OpenMOC cell and volume for this FSR
    openmoc_cell = openmoc_geometry.findCellContainingFSR(fsr)
    if mgxs_lib.domain_type == 'cell':
        domain_id = openmoc_cell.getId()
    else:
        domain_id = openmoc_cell.getFillMaterial().getId()

    fsr_volume = track_generator.getFSRVolume(fsr)

    # Store the volume-averaged flux
    mgxs = mgxs_lib.get_mgxs(domain_id, 'nu-fission')
    flux = mgxs.tallies['flux'].mean.flatten()
    flux = np.flipud(flux) / fsr_volume
    openmc_fluxes[fsr, :] = flux

# Extract energy group edges
group_edges = mgxs_lib.energy_groups.group_edges
group_edges *= 1e6      # Convert to units of eV 
group_edges += 1e-5     # Adjust lower bound to 1e-3 eV (for loglog scaling)

# Compute difference in energy bounds for each group
group_deltas = np.ediff1d(group_edges)
group_edges = np.flipud(group_edges)
group_deltas = np.flipud(group_deltas)

# Normalize fluxes to the total integrated flux
openmc_fluxes /= np.sum(openmc_fluxes * group_deltas, axis=1)[:,np.newaxis]
openmoc_fluxes /= np.sum(openmoc_fluxes * group_deltas, axis=1)[:,np.newaxis]

# Extend the mgxs values array for matplotlib's step plot of fluxes
openmc_fluxes = np.insert(openmc_fluxes, 0, openmc_fluxes[:,0], axis=1)
openmoc_fluxes = np.insert(openmoc_fluxes, 0, openmoc_fluxes[:,0], axis=1)


###############################################################################
#                 Plot OpenMC-to-OpenMOC Scalar Flux Errors
###############################################################################

# Instantiate a PyNE ACE continuous-energy cross sections library
xs_dir = os.environ['OPENMC_CROSS_SECTIONS']
xs_dir = re.sub('cross_sections.xml$', '', xs_dir)
pyne_lib = pyne.ace.Library(xs_dir + '293.6K/U_238_293.6K.ace')
pyne_lib.read('92238.71c')

# Extract the U-235 data from the library
u238 = pyne_lib.tables['92238.71c']

# Extract the continuous-energy U-238 fission cross section data
capture = u238.reactions[102]

# Compute the percent relative error in the flux
rel_err = np.zeros(openmc_fluxes.shape)
for fsr in range(num_fsrs):
    delta_flux = openmoc_fluxes[fsr,:] - openmc_fluxes[fsr,:]
    rel_err[fsr,:] = delta_flux / openmc_fluxes[fsr,:] * 100.

# Plot OpenMOC relative flux errors in each FSR
for fsr in range(num_fsrs):

    # Get the OpenMOC cell and material for this FSR
    cell = openmoc_geometry.findCellContainingFSR(fsr)

    # Create a step plot for the MGXS
    fig, ax1 = plt.subplots()

    plt.plot(group_edges, rel_err[fsr,:],
             drawstyle='steps', color='r', linewidth=2)

    plt.xlabel('Energy [eV]', fontsize=12)
    plt.ylabel('Relative Error [%]', fontsize=12)
    plt.title('OpenMOC-to-OpenMC Flux Relative Error', fontsize=16)
    plt.grid()
    plt.xlim((min(group_edges), max(group_edges)))
    plt.xscale('log')

    # Create loglog plot of U-238 continuous-energy capture cross section 
    if 'fuel' in cell.getName():
        ax2 = ax1.twinx()
        ax2.loglog(u238.energy*1e6, capture.sigma, color='g', \
                   linewidth=1, zorder=1)
        ax2.set_ylabel('U-238 Capture XS [barns]', color='g', fontsize=12)
        ax2.set_yscale('log')

        ax1.set_zorder(ax2.get_zorder()+1) # put ax in front of ax2 
        ax1.patch.set_visible(False) # hide the 'canvas' 

    filename = 'rel-err-{0}.png'.format(fsr)
    plt.savefig(filename, bbox_inches='tight')
    plt.close()