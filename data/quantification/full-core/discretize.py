import openmoc


def discretize_geometry(self):
    """Discretize a 2x2 checkerboard of BEAVRS fuel assemblies surrounded by
    a water reflector into OpenMOC flat source regions.

     This method is intended to be attached directly to a Batchwise instance,
     as illustrated by the example below for a PerfectBatchwise object:

     > import types
     > import infermc
     > b = infermc.batchwise.PerfectBatchwise()
     > b._discretize_geometry = types.MethodType(discretize_geometry, b)

     This will allow the Batchwise instance to discretize the geometry for
     accurate OpenMOC simulations.

     """

    openmoc.log.py_printf('INFO', 'Discretizing the geometry...')

    openmc_geometry = self.mat_mgxslibs[0].openmc_geometry
    all_openmoc_cells = self.openmoc_geometry.getAllMaterialCells()

    # FIXME: Only do this for pin cells!!!
    # Add angular sectors to all material-filled cells
    for cell_id in all_openmoc_cells:
        all_openmoc_cells[cell_id].setNumSectors(8)

    ###########################################################################
    # Discretize the instrument and guide tubes and BPs
    ###########################################################################

    # Find the fuel clad outer radius zcylinder
    all_surfs = self.openmoc_geometry.getAllSurfaces()
    for surf_id in all_surfs:
        if all_surfs[surf_id].getName() == 'Fuel clad OR':
            fuel_or = openmoc.castSurfaceToZCylinder(all_surfs[surf_id])

    # Find cells by their string names in the BEAVRS benchmark
    instr_tube_name = 'Instrument tube thimble radial 0: air'
    gt_below_name = 'Empty GT below the dashpot radial 0: water'
    gt_above_name = 'Empty GT above the dashpot radial 0: water'
    burn_abs1_name = 'BPRA rod active poison radial 0: air'
    burn_abs2_name = 'BPRA rod active poison radial 3: borosilicate'
    instr_guide_bp_tube_mod_name = 'Intermediate grid pincell radial 0: water'
    instr_tube = openmc_geometry.get_cells_by_name(instr_tube_name)
    gt_below = openmc_geometry.get_cells_by_name(gt_below_name)
    gt_above = openmc_geometry.get_cells_by_name(gt_above_name)
    burn_abs1 = openmc_geometry.get_cells_by_name(burn_abs1_name)
    burn_abs2 = openmc_geometry.get_cells_by_name(burn_abs2_name)
    mod = openmc_geometry.get_cells_by_name(instr_guide_bp_tube_mod_name)

    # Discretize each cell into radial rings
    for cell in instr_tube:
        all_openmoc_cells[cell.id].setNumRings(10)
    for cell in gt_below:
        all_openmoc_cells[cell.id].setNumRings(10)
    for cell in gt_above:
        all_openmoc_cells[cell.id].setNumRings(10)
    for cell in burn_abs1:
        all_openmoc_cells[cell.id].setNumRings(5)
    for cell in burn_abs2:
        all_openmoc_cells[cell.id].setNumRings(5)
    for cell in mod:
        all_openmoc_cells[cell.id].setNumRings(5)
        all_openmoc_cells[cell.id].addSurface(surface=fuel_or, halfspace=+1)

    ###########################################################################
    # Discretize the fuel pin cells in all assemblies
    ###########################################################################

    # Find all pin cell universes - universes containing a cell filled with fuel
    all_univs = self.openmoc_geometry.getAllUniverses()
    pin_univs = set()
    for univ_id in all_univs:
        all_cells = all_univs[univ_id].getAllCells()
        for cell_id in all_cells:
            if all_cells[cell_id].getType() == openmoc.MATERIAL:
                if 'fuel' in all_cells[cell_id].getFillMaterial().getName().lower():
                    pin_univs.add(all_univs[univ_id])

    # Discretize all fuel cells within each pin cell universe into rings
    for pin_univ in pin_univs:
        all_cells = pin_univ.getCells()
        for cell_id in all_cells:
            if all_cells[cell_id].getType() == openmoc.MATERIAL:
                if 'fuel' in all_cells[cell_id].getFillMaterial().getName().lower():
                    all_cells[cell_id].setNumRings(5)

    ###########################################################################
    # Discretize the reflector cells using a lattice
    ###########################################################################

    # Store the names of each of the reflector cells in the BEAVRS benchmark
    cell_names = ['Water', 'North Baffle Outer Water',
                  'Baffle South radial outer: water',
                  'Baffle East radial outer: water',
                  'Baffle West radial outer: water',
                  'Baffle North East Tip radial outer: water',
                  'Baffle South East Tip radial outer: water',
                  'Tip Baffle Outer Water W',
                  'Tip Baffle Outer Water N',
                  'Tip Baffle Outer Water SE',
                  'Baffle South West Tip radial outer: water',
                  'Baffle South West Corner radial outer: water',
                  'Baffle South East Corner radial outer: water',
                  'Baffle North East Corner radial outer: water',
                  'Corner Baffle Water Gap N',
                  'Corner Baffle Water Gap W',
                  'Corner Baffle Outer Water']

    # Find all of the water-filled cells which comprise the reflector
    refl_cells = []
    for cell_name in cell_names:
        cells = openmc_geometry.get_cells_by_name(cell_name, matching=True)
        refl_cells.extend(cells)

    # Create a water-filled reflector cell/universe to put in a lattice
    all_materials = self.openmoc_geometry.getAllMaterials()
    h2o = all_openmoc_cells[mod[0].id].getFillMaterial()
    reflector_cell = openmoc.Cell(name='Refined Reflector Cell')
    reflector_cell.setFill(all_materials[h2o.getId()])
    reflector = openmoc.Universe(name='Refined Reflector Universe')
    reflector.addCell(reflector_cell)

    # Sliced up water cells with a lattice
    mesh_per_pin = 4
    lattice = openmoc.Lattice(name='{} x {} Spaced Reflector'.format(mesh_per_pin, mesh_per_pin))
    lattice.setWidth(width_x=1.26492 / mesh_per_pin, width_y=1.26492 / mesh_per_pin)
    template = [[reflector] * 17 * mesh_per_pin] * 17 * mesh_per_pin
    lattice.setUniverses([template])

    # Put the lattice in each of the water-filled reflector cells
    for refl_cell in refl_cells:
        all_openmoc_cells[refl_cell.id].setFill(lattice)
        all_openmoc_cells[refl_cell.id].setNumSectors(0)

    ###########################################################################
    # Remove sectors from some outer cells (barrel, baffle, etc.)
    ###########################################################################

    # Remove sector discretization from the shield panels
    shield_panels = openmc_geometry.get_cells_by_name('NE Shield Panel', matching=True)
    shield_panels.extend(openmc_geometry.get_cells_by_name('NW Shield Panel', matching=True))
    shield_panels.extend(openmc_geometry.get_cells_by_name('SE Shield Panel', matching=True))
    shield_panels.extend(openmc_geometry.get_cells_by_name('SW Shield Panel', matching=True))
    for shield_panel in shield_panels:
        all_openmoc_cells[shield_panel.id].setNumSectors(0)

    # Remove sector discretization from outermost cells
    barrel = openmc_geometry.get_cells_by_name('Core Barrel', matching=True)[0]
    vessel = openmc_geometry.get_cells_by_name('RPV', matching=True)[0]
    vessel_liner = openmc_geometry.get_cells_by_name('RPV Liner', matching=True)[0]
    downcomer = openmc_geometry.get_cells_by_name('Downcomer', matching=True)[0]
    outer_cell = openmc_geometry.get_cells_by_name('outer borosilicate', matching=True)[0]
    all_openmoc_cells[barrel.id].setNumSectors(0)
    all_openmoc_cells[vessel.id].setNumSectors(0)
    all_openmoc_cells[vessel_liner.id].setNumSectors(0)
    all_openmoc_cells[downcomer.id].setNumSectors(0)
    all_openmoc_cells[outer_cell.id].setNumSectors(0)

#    return

    ###########################################################################
    # Discretize the baffle steel cells using a lattice
    ###########################################################################

    # Discretize the baffle steel cells
    baffle_cells = openmc_geometry.get_cells_by_name('Baffle Steel', matching=False)

    # Create a SS304-filled reflector cell/universe to put in a lattice
    all_materials = self.openmoc_geometry.getAllMaterials()
    ss304 = openmc_geometry.get_materials_by_name('SS304', matching=True)[0]
    ss304 = all_materials[ss304.id]
    ss304_cell = openmoc.Cell(name='Refined Baffle Steel Cell')
    ss304_cell.setFill(all_materials[ss304.getId()])
    baffle = openmoc.Universe(name='Refined Baffle Steel Universe')
    baffle.addCell(ss304_cell)

    # Sliced up baffle steel cells with a lattice
    mesh_per_pin = 5
    lattice = openmoc.Lattice(name='{} x {} Spaced Baffle Steel'.format(mesh_per_pin, mesh_per_pin))
    lattice.setWidth(width_x=1.26492 / mesh_per_pin, width_y=1.26492 / mesh_per_pin)
    template = [[baffle] * 17 * mesh_per_pin] * 17 * mesh_per_pin
    lattice.setUniverses([template])

    # Put the lattice in each of the SS304-filled baffle steel cells
    for baffle_cell in baffle_cells:
        all_openmoc_cells[baffle_cell.id].setFill(lattice)
        all_openmoc_cells[baffle_cell.id].setNumSectors(0)

    ###########################################################################
    # Discretize the baffle water gap cells using a lattice
    ###########################################################################

    # Discretize the baffle water gap cells
    baffle_cells = openmc_geometry.get_cells_by_name('Baffle Water', matching=False)

    # Create a water-filled reflector cell/universe to put in a lattice
    all_materials = self.openmoc_geometry.getAllMaterials()
    h2o = openmc_geometry.get_materials_by_name('SS304', matching=True)[0]
    h2o = all_materials[h2o.id]
    h2o_cell = openmoc.Cell(name='Refined Baffle Water Gap Cell')
    h2o_cell.setFill(all_materials[h2o.getId()])
    baffle = openmoc.Universe(name='Refined Baffle Water Gap Universe')
    baffle.addCell(h2o_cell)

    # Sliced up baffle water gap cells with a lattice
    mesh_per_pin = 5
    lattice = openmoc.Lattice(name='{} x {} Spaced Baffle Water Gap'.format(mesh_per_pin, mesh_per_pin))
    lattice.setWidth(width_x=1.26492 / mesh_per_pin, width_y=1.26492 / mesh_per_pin)
    template = [[baffle] * 17 * mesh_per_pin] * 17 * mesh_per_pin
    lattice.setUniverses([template])

    # Put the lattice in each of the water-filled baffle water gap cells
    for baffle_cell in baffle_cells:
        if 'water' in baffle_cell.name:
            all_openmoc_cells[baffle_cell.id].setFill(lattice)
            all_openmoc_cells[baffle_cell.id].setNumSectors(0)

    ###########################################################################
    # Discretize the inter-assembly grid sleeve cells using lattices
    ###########################################################################

    # Discretize the inter-assembly grid sleeves and water gaps
    grid_sleeve_cells = openmc_geometry.get_cells_by_name('Grid sleeve axial universe axial', matching=False)

    # Create a water-filled reflector cell/universe to put in a lattice
    all_materials = self.openmoc_geometry.getAllMaterials()
    h2o = openmc_geometry.get_materials_by_name('water', matching=True)[0]
    h2o = all_materials[h2o.id]
    h2o_cell = openmoc.Cell(name='Refined Grid Sleeve Water Cell')
    h2o_cell.setFill(all_materials[h2o.getId()])
    grid_sleeve = openmoc.Universe(name='Refined Grid Sleeve Water Universe')
    grid_sleeve.addCell(h2o_cell)

    # Sliced up baffle cells with a lattice
    mesh_per_pin = 1
    lattice = openmoc.Lattice(name='{} x {} Spaced Grid Sleeve'.format(mesh_per_pin, mesh_per_pin))
    lattice.setWidth(width_x=1.26492 / mesh_per_pin, width_y=1.26492 / mesh_per_pin)
    template = [[grid_sleeve] * 17 * mesh_per_pin] * 17 * mesh_per_pin
    lattice.setUniverses([template])

    # Put the lattice in each of the water-filled grid sleeve cells
    for grid_sleeve_cell in grid_sleeve_cells:
        if 'water' in grid_sleeve_cell.name:
            all_openmoc_cells[grid_sleeve_cell.id].setFill(lattice)
            all_openmoc_cells[grid_sleeve_cell.id].setNumSectors(0)

    # Discretize the inter-assembly grid sleeves and water gaps
    grid_sleeve_cells = openmc_geometry.get_cells_by_name('Intermediate grid sleeve pincell radial outer: water box', matching=True)

    # Create a water-filled reflector cell/universe to put in a lattice
    all_materials = self.openmoc_geometry.getAllMaterials()
    h2o = openmc_geometry.get_materials_by_name('water', matching=True)[0]
    h2o = all_materials[h2o.id]
    h2o_cell = openmoc.Cell(name='Refined Grid Sleeve Outer Water Cell')
    h2o_cell.setFill(all_materials[h2o.getId()])
    grid_sleeve = openmoc.Universe(name='Refined Grid Sleeve Outer Water Universe')
    grid_sleeve.addCell(h2o_cell)

    # Sliced up baffle cells with a lattice
    mesh_per_pin = 1
    lattice = openmoc.Lattice(name='{} x {} Spaced Grid Outer Sleeve'.format(mesh_per_pin, mesh_per_pin))
    lattice.setWidth(width_x=1.26492 / mesh_per_pin, width_y=1.26492 / mesh_per_pin)
    template = [[grid_sleeve] * 17 * mesh_per_pin] * 17 * mesh_per_pin
    lattice.setUniverses([template])

    # Put the lattice in each of the water-filled grid sleeve cells
    for grid_sleeve_cell in grid_sleeve_cells:
        if 'water' in grid_sleeve_cell.name:
            all_openmoc_cells[grid_sleeve_cell.id].setFill(lattice)
            all_openmoc_cells[grid_sleeve_cell.id].setNumSectors(0)

    # Discretize the inter-assembly grid sleeves and water gaps
    grid_sleeve_cells = openmc_geometry.get_cells_by_name('Intermediate grid sleeve pincell radial 0: zirc', matching=True)

    # Create a zircaloy-filled reflector cell/universe to put in a lattice
    all_materials = self.openmoc_geometry.getAllMaterials()
    zirc = openmc_geometry.get_materials_by_name('zirc', matching=True)[0]
    zirc = all_materials[zirc.id]
    zirc_cell = openmoc.Cell(name='Refined Grid Sleeve Zirc Cell')
    zirc_cell.setFill(all_materials[zirc.getId()])
    grid_sleeve = openmoc.Universe(name='Refined Grid Sleeve Zirc Universe')
    grid_sleeve.addCell(zirc_cell)

    # Sliced up baffle cells with a lattice
    mesh_per_pin = 1
    lattice = openmoc.Lattice(name='{} x {} Spaced Grid Zirc Sleeve'.format(mesh_per_pin, mesh_per_pin))
    lattice.setWidth(width_x=1.26492 / mesh_per_pin, width_y=1.26492 / mesh_per_pin)
    template = [[grid_sleeve] * 17 * mesh_per_pin] * 17 * mesh_per_pin
    lattice.setUniverses([template])

    # Put the lattice in each of the zircaloy-filled grid sleeve cells
    for grid_sleeve_cell in grid_sleeve_cells:
        all_openmoc_cells[grid_sleeve_cell.id].setFill(lattice)
        all_openmoc_cells[grid_sleeve_cell.id].setNumSectors(0)


def discretize_geometry_standalone(mat_mgxslib, openmoc_geometry):
    """Discretize the full core BEAVRS benchmark."""

    openmoc.log.py_printf('INFO', 'Discretizing the geometry...')

    openmc_geometry = mat_mgxslib.openmc_geometry
    all_openmoc_cells = openmoc_geometry.getAllMaterialCells()

    # Add angular sectors to all material-filled cells
    # FIXME: Only do this for pin cells!!!
    for cell_id in all_openmoc_cells:
        all_openmoc_cells[cell_id].setNumSectors(8)

    ###########################################################################
    # Discretize the instrument and guide tubes and BPs
    ###########################################################################

    # Find the fuel clad outer radius zcylinder
    all_surfs = openmoc_geometry.getAllSurfaces()
    for surf_id in all_surfs:
        if all_surfs[surf_id].getName() == 'Fuel clad OR':
            fuel_or = openmoc.castSurfaceToZCylinder(all_surfs[surf_id])

    # Find cells by their string names in the BEAVRS benchmark
    instr_tube_name = 'Instrument tube thimble radial 0: air'
    gt_below_name = 'Empty GT below the dashpot radial 0: water'
    gt_above_name = 'Empty GT above the dashpot radial 0: water'
    burn_abs1_name = 'BPRA rod active poison radial 0: air'
    burn_abs2_name = 'BPRA rod active poison radial 3: borosilicate'
    instr_guide_bp_tube_mod_name = 'Intermediate grid pincell radial 0: water'
    instr_tube = openmc_geometry.get_cells_by_name(instr_tube_name)
    gt_below = openmc_geometry.get_cells_by_name(gt_below_name)
    gt_above = openmc_geometry.get_cells_by_name(gt_above_name)
    burn_abs1 = openmc_geometry.get_cells_by_name(burn_abs1_name)
    burn_abs2 = openmc_geometry.get_cells_by_name(burn_abs2_name)
    mod = openmc_geometry.get_cells_by_name(instr_guide_bp_tube_mod_name)

    # Discretize each cell into radial rings
    for cell in instr_tube:
        all_openmoc_cells[cell.id].setNumRings(10)
    for cell in gt_below:
        all_openmoc_cells[cell.id].setNumRings(10)
    for cell in gt_above:
        all_openmoc_cells[cell.id].setNumRings(10)
    for cell in burn_abs1:
        all_openmoc_cells[cell.id].setNumRings(5)
    for cell in burn_abs2:
        all_openmoc_cells[cell.id].setNumRings(5)
    for cell in mod:
        all_openmoc_cells[cell.id].setNumRings(5)
        all_openmoc_cells[cell.id].addSurface(surface=fuel_or, halfspace=+1)

    ###########################################################################
    # Discretize the fuel pin cells in all assemblies
    ###########################################################################

    # Find all pin cell universes - universes containing a cell filled with fuel
    all_univs = openmoc_geometry.getAllUniverses()
    pin_univs = set()
    for univ_id in all_univs:
        all_cells = all_univs[univ_id].getAllCells()
        for cell_id in all_cells:
            if all_cells[cell_id].getType() == openmoc.MATERIAL:
                if 'fuel' in all_cells[cell_id].getFillMaterial().getName().lower():
                    pin_univs.add(all_univs[univ_id])

    # Discretize all fuel cells within each pin cell universe into rings
    for pin_univ in pin_univs:
        all_cells = pin_univ.getCells()
        for cell_id in all_cells:
            if all_cells[cell_id].getType() == openmoc.MATERIAL:
                if 'fuel' in all_cells[cell_id].getFillMaterial().getName().lower():
                    all_cells[cell_id].setNumRings(5)

    ###########################################################################
    # Discretize the reflector cells using a lattice
    ###########################################################################

    # Store the names of each of the reflector cells in the BEAVRS benchmark
    cell_names = ['Water', 'North Baffle Outer Water',
                  'Baffle South radial outer: water',
                  'Baffle East radial outer: water',
                  'Baffle West radial outer: water',
                  'Baffle North East Tip radial outer: water',
                  'Baffle South East Tip radial outer: water',
                  'Tip Baffle Outer Water W',
                  'Tip Baffle Outer Water N',
                  'Baffle South West Tip radial outer: water',
                  'Baffle South West Corner radial outer: water',
                  'Baffle South East Corner radial outer: water',
                  'Baffle North East Corner radial outer: water',
                  'Corner Baffle Water Gap N',
                  'Corner Baffle Water Gap W',
                  'Corner Baffle Outer Water']

    # Find all of the water-filled cells which comprise the reflector
    refl_cells = []
    for cell_name in cell_names:
        cells = openmc_geometry.get_cells_by_name(cell_name, matching=True)
        refl_cells.extend(cells)

    # Create a water-filled reflector cell/universe to put in a lattice
    all_materials = openmoc_geometry.getAllMaterials()
    h2o = all_openmoc_cells[mod[0].id].getFillMaterial()
    reflector_cell = openmoc.Cell(name='Refined Reflector Cell')
    reflector_cell.setFill(all_materials[h2o.getId()])
    reflector = openmoc.Universe(name='Refined Reflector Universe')
    reflector.addCell(reflector_cell)

    # Sliced up water cells with a lattice
    mesh_per_pin = 2
    lattice = openmoc.Lattice(name='{} x {} Spaced Reflector'.format(mesh_per_pin))
    lattice.setWidth(width_x=1.26492 / mesh_per_pin, width_y=1.26492 / mesh_per_pin)
    template = [[reflector] * 17 * mesh_per_pin] * 17 * mesh_per_pin
    lattice.setUniverses([template])

    # Put the lattice in each of the water-filled reflector cells
    for refl_cell in refl_cells:
        all_openmoc_cells[refl_cell.id].setFill(lattice)
        all_openmoc_cells[refl_cell.id].setNumSectors(0)

