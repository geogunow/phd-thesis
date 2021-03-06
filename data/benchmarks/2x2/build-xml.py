import numpy as np

import openmc
import openmc.opencg_compatible as opencg_compatible
import infermc.beavrs


####################   User-specified Simulation Parameters  ###################

batches = 1000
inactive = 100
particles = 10000000


#########   Exporting to OpenMC geometry.xml and materials.xml Files  ##########

# Write all BEAVRS materials to materials.xml file
infermc.beavrs.make_iso_in_lab()
infermc.beavrs.write_materials_file()

# Extract reflected geometry from InferMC's pre-built assembly Geometries
two_by_two = infermc.beavrs.build_two_by_two('Fuel 1.6% enr instr no BAs',
                                             'Fuel 3.1% enr instr 20')
openmc_geometry = opencg_compatible.get_openmc_geometry(two_by_two)
openmc_geometry.export_to_xml()

##################   Exporting to OpenMC settings.xml File  ###################

# Construct uniform initial source distribution over fissionable zones
lower_left = two_by_two.bounds[:3]
upper_right = two_by_two.bounds[3:]
source = openmc.source.Source(space=openmc.stats.Box(lower_left, upper_right))
source.space.only_fissionable = True

settings_file = openmc.Settings()
settings_file.batches = batches
settings_file.inactive = inactive
settings_file.particles = particles
settings_file.ptables = True
settings_file.output = {'tallies': False}
settings_file.source = source
settings_file.sourcepoint_write = False

settings_file.entropy_dimension = [34,34,1]
settings_file.entropy_upper_right = upper_right
settings_file.entropy_lower_left = lower_left

settings_file.export_to_xml()


##################   Exporting to OpenMC plots.xml File  ######################

# Initialize the BEAVRS color mapping scheme
b = infermc.beavrs.beavrs
b.write_openmc_plots()

# Complete assembly
plot = openmc.Plot(plot_id=1)
bounds = two_by_two.bounds
plot.width = [two_by_two.max_x-two_by_two.min_x,
              two_by_two.max_y-two_by_two.min_y]
plot.origin = [bounds[0] + (bounds[3] - bounds[0]) / 2.,
                bounds[1] + (bounds[4] - bounds[1]) / 2.,
                bounds[2] + (bounds[5] - bounds[2]) / 2.]
plot.color = 'mat'
plot.filename = '2x2'
plot.col_spec = b.plots.colspec_mat
plot.pixels = [2000, 2000]

plot_file = openmc.Plots([plot])
plot_file.export_to_xml()


###################  Create Mesh Tallies for Verification  ####################

# Instantiate a tally Mesh
mesh = openmc.Mesh(name='assembly mesh')
mesh.type = 'regular'
mesh.dimension = [34, 34, 1]
mesh.lower_left = lower_left
mesh.width = (np.array(upper_right) - np.array(lower_left))
mesh.width[:2] /= 34

# Instantiate tally Filter
mesh_filter = openmc.Filter()
mesh_filter.mesh = mesh

# Instantiate energy-integrated fission rate mesh Tally
fission_rates = openmc.Tally(name='fission rates')
fission_rates.filters = [mesh_filter]
fission_rates.scores = ['fission']

# Instantiate energy-wise U-238 capture rate mesh Tally
capture_rates = openmc.Tally(name='u-238 capture')
capture_rates.filters = [mesh_filter]
capture_rates.nuclides = ['U238']
capture_rates.scores = ['absorption', 'fission']

# Create a "tallies.xml" file for the mesh tallies
tallies_file = openmc.Tallies([fission_rates, capture_rates])
tallies_file.export_to_xml()
