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

# Extract fuel assembly of interest from BEAVRS model
fuel_assembly = infermc.beavrs.find_assembly('Fuel 3.1% enr instr no BAs')
openmc_geometry = opencg_compatible.get_openmc_geometry(fuel_assembly)
openmc_geometry.export_to_xml()


##################   Exporting to OpenMC settings.xml File  ###################

# Construct uniform initial source distribution over fissionable zones
lower_left = fuel_assembly.bounds[:3]
upper_right = fuel_assembly.bounds[3:]
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

settings_file.entropy_dimension = [17,17,1]
settings_file.entropy_upper_right = upper_right
settings_file.entropy_lower_left = lower_left

settings_file.export_to_xml()


##################   Exporting to OpenMC plots.xml File  ######################

# Initialize the BEAVRS color mapping scheme
b = infermc.beavrs.beavrs
b.write_openmc_plots()

# Complete assembly
plot1 = openmc.Plot(plot_id=1)
bounds = fuel_assembly.bounds
plot1.width = [fuel_assembly.max_x-fuel_assembly.min_x,
              fuel_assembly.max_y-fuel_assembly.min_y]
plot1.origin = [bounds[0] + (bounds[3] - bounds[0]) / 2.,
                bounds[1] + (bounds[4] - bounds[1]) / 2.,
                bounds[2] + (bounds[5] - bounds[2]) / 2.]
plot1.color = 'mat'
plot1.filename = 'assembly'
plot1.col_spec = b.plots.colspec_mat
plot1.pixels = [2000, 2000]

# Zoom in of fuel pin
plot2 = openmc.Plot(plot_id=2)
bounds = fuel_assembly.bounds
plot2.width = [(fuel_assembly.max_x-fuel_assembly.min_x) / 17.,
               (fuel_assembly.max_y-fuel_assembly.min_y) / 17.]
plot2.origin = [bounds[0] + (bounds[3] - bounds[0]) / 2. + (bounds[3] - bounds[0]) / 17. * 8.,
                bounds[1] + (bounds[4] - bounds[1]) / 2. + (bounds[4] - bounds[1]) / 17. * 8.,
                bounds[2] + (bounds[5] - bounds[2]) / 2.]
plot2.color = 'mat'
plot2.filename = 'fuel-pin'
plot2.col_spec = b.plots.colspec_mat

# Zoom in of instrument tube
plot3 = openmc.Plot(plot_id=3)
bounds = fuel_assembly.bounds
plot3.width = [(fuel_assembly.max_x-fuel_assembly.min_x) / 17.,
               (fuel_assembly.max_y-fuel_assembly.min_y) / 17.]
plot3.origin = [bounds[0] + (bounds[3] - bounds[0]) / 2.,
                bounds[1] + (bounds[4] - bounds[1]) / 2.,
                bounds[2] + (bounds[5] - bounds[2]) / 2.]
plot3.color = 'mat'
plot3.filename = 'instr-tube'
plot3.col_spec = b.plots.colspec_mat

# Zoom in of guide tube
plot4 = openmc.Plot(plot_id=4)
bounds = fuel_assembly.bounds
plot4.width = [(fuel_assembly.max_x-fuel_assembly.min_x) / 17.,
               (fuel_assembly.max_y-fuel_assembly.min_y) / 17.]
plot4.origin = [bounds[0] + (bounds[3] - bounds[0]) / 2. + (bounds[3] - bounds[0]) / 17. * 5.,
                bounds[1] + (bounds[4] - bounds[1]) / 2. + (bounds[4] - bounds[1]) / 17. * 5.,
                bounds[2] + (bounds[5] - bounds[2]) / 2.]
plot4.color = 'mat'
plot4.filename = 'guide-tube'
plot4.col_spec = b.plots.colspec_mat

plot_file = openmc.Plots([plot1, plot2, plot3, plot4])
plot_file.export_to_xml()


###################  Create Mesh Tallies for Verification  ####################

# Instantiate a tally Mesh
mesh = openmc.Mesh(name='assembly mesh')
mesh.type = 'regular'
mesh.dimension = [17, 17, 1]
mesh.lower_left = lower_left
mesh.width = (np.array(upper_right) - np.array(lower_left))
mesh.width[:2] /= 17

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
