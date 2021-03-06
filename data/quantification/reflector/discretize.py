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
    guide_tube_name = 'Empty GT above the dashpot radial 0: water'
    burn_abs1_name = 'BPRA rod active poison radial 0: air'
    burn_abs2_name = 'BPRA rod active poison radial 3: borosilicate'
    instr_guide_bp_tube_mod_name = 'Intermediate grid pincell radial 0: water'
    instr_tube = openmc_geometry.get_cells_by_name(instr_tube_name)
    guide_tube = openmc_geometry.get_cells_by_name(guide_tube_name)
    burn_abs1 = openmc_geometry.get_cells_by_name(burn_abs1_name)
    burn_abs2 = openmc_geometry.get_cells_by_name(burn_abs2_name)
    mod = openmc_geometry.get_cells_by_name(instr_guide_bp_tube_mod_name)

    # Discretize each cell into radial rings
    for cell in instr_tube:
        all_openmoc_cells[cell.id].setNumRings(10)
    for cell in guide_tube:
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
    # Discretize the moderator around each pin
    ###########################################################################

    mod_name = 'Grids axial universe axial 8: water'
    mod = openmc_geometry.get_cells_by_name(mod_name)

    for cell in mod:
        all_openmoc_cells[cell.id].addSurface(surface=fuel_or, halfspace=+1)
        all_openmoc_cells[cell.id].setNumRings(5)

    ###########################################################################
    # Discretize the reflector cells using same methodology as for C5G7
    ###########################################################################

    all_materials = self.openmoc_geometry.getAllMaterials()

    # Reflector
    water = all_openmoc_cells[mod[0].id].getFillMaterial()
    reflector_cell = openmoc.Cell(name='moderator')
    reflector_cell.setFill(all_materials[water.getId()])

    reflector = openmoc.Universe(name='Reflector')
    reflector.addCell(reflector_cell)

    # Cells
    refined_reflector_cell = openmoc.Cell(name='Semi-Finely Spaced Reflector')
    right_reflector_cell = openmoc.Cell(name='Right Reflector')
    corner_reflector_cell = openmoc.Cell(name='Bottom Corner Reflector')
    bottom_reflector_cell = openmoc.Cell(name='Bottom Reflector')

    refined_reflector = openmoc.Universe(name='Semi-Finely Spaced Moderator')
    right_reflector = openmoc.Universe(name='Right Reflector')
    corner_reflector = openmoc.Universe(name='Bottom Corner Reflector')
    bottom_reflector = openmoc.Universe(name='Bottom Reflector')

    refined_reflector.addCell(refined_reflector_cell)
    right_reflector.addCell(right_reflector_cell)
    corner_reflector.addCell(corner_reflector_cell)
    bottom_reflector.addCell(bottom_reflector_cell)

    # Initialize a list of reflector lattices
    lattices = list()

    # Sliced up water cells - semi finely spaced
    lattices.append(openmoc.Lattice(name='Semi-Finely Spaced Reflector'))
    lattices[-1].setWidth(width_x=1.25984/10., width_y=1.25984/10.)
    template = [[reflector] * 10] * 10
    lattices[-1].setUniverses([template])
    refined_reflector_cell.setFill(lattices[-1])

    # Sliced up water cells - right side of geometry
    lattices.append(openmoc.Lattice(name='Right Reflector'))
    lattices[-1].setWidth(width_x=1.25984, width_y=1.25984)
    template = [[refined_reflector] * 11 + [reflector] * 6] * 17
    lattices[-1].setUniverses([template])
    right_reflector_cell.setFill(lattices[-1])

    # Sliced up water cells for bottom corner of geometry
    lattices.append(openmoc.Lattice(name='Bottom Corner Reflector'))
    lattices[-1].setWidth(width_x=1.25984, width_y=1.25984)
    template = [[refined_reflector] * 11 + [reflector] * 6] * 11
    template += [[reflector] * 17] * 6
    lattices[-1].setUniverses([template])
    corner_reflector_cell.setFill(lattices[-1])

    # Sliced up water cells for bottom of geometry
    lattices.append(openmoc.Lattice(name='Bottom Reflector'))
    lattices[-1].setWidth(width_x=1.25984, width_y=1.25984)
    template = [[refined_reflector] * 17] * 11
    template += [[reflector] * 17] * 6
    lattices[-1].setUniverses([template])
    bottom_reflector_cell.setFill(lattices[-1])

    # Find the root cell
    all_cells = self.openmoc_geometry.getAllCells()
    for cell_id in all_cells:
        if all_cells[cell_id].getName() == 'root cell':
            root_cell = all_cells[cell_id]

    # Extract core lattice
    core_lattice = root_cell.getFillUniverse()
    core_lattice = openmoc.castUniverseToLattice(core_lattice)

    # Assign reflector universes to core lattice
    core_lattice.updateUniverse(0, 0, 0, bottom_reflector)
    core_lattice.updateUniverse(1, 0, 0, bottom_reflector)
    core_lattice.updateUniverse(2, 0, 0, corner_reflector)
    core_lattice.updateUniverse(2, 1, 0, right_reflector)
    core_lattice.updateUniverse(2, 2, 0, right_reflector)


def discretize_geometry_standalone(mat_mgxslib, openmoc_geometry):
    """Discretize a 2x2 checkerboard of BEAVRS fuel assemblies surrounded by
    a water reflector into OpenMOC flat source regions."""

    openmoc.log.py_printf('INFO', 'Discretizing the geometry...')

    openmc_geometry = mat_mgxslib.openmc_geometry
    all_openmoc_cells = openmoc_geometry.getAllMaterialCells()

    # FIXME: Only do this for pin cells!!!
    # Add angular sectors to all material-filled cells
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
    guide_tube_name = 'Empty GT above the dashpot radial 0: water'
    burn_abs1_name = 'BPRA rod active poison radial 0: air'
    burn_abs2_name = 'BPRA rod active poison radial 3: borosilicate'
    instr_guide_bp_tube_mod_name = 'Intermediate grid pincell radial 0: water'
    instr_tube = openmc_geometry.get_cells_by_name(instr_tube_name)
    guide_tube = openmc_geometry.get_cells_by_name(guide_tube_name)
    burn_abs1 = openmc_geometry.get_cells_by_name(burn_abs1_name)
    burn_abs2 = openmc_geometry.get_cells_by_name(burn_abs2_name)
    mod = openmc_geometry.get_cells_by_name(instr_guide_bp_tube_mod_name)

    # Discretize each cell into radial rings
    for cell in instr_tube:
        all_openmoc_cells[cell.id].setNumRings(10)
    for cell in guide_tube:
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
    # Discretize the reflector cells using same methodology as for C5G7
    ###########################################################################

    all_materials = openmoc_geometry.getAllMaterials()

    # Reflector
    water = all_openmoc_cells[mod[0].id].getFillMaterial()
    reflector_cell = openmoc.Cell(name='moderator')
    reflector_cell.setFill(all_materials[water.getId()])

    reflector = openmoc.Universe(name='Reflector')
    reflector.addCell(reflector_cell)

    # Cells
    refined_reflector_cell = openmoc.Cell(name='Semi-Finely Spaced Reflector')
    right_reflector_cell = openmoc.Cell(name='Right Reflector')
    corner_reflector_cell = openmoc.Cell(name='Bottom Corner Reflector')
    bottom_reflector_cell = openmoc.Cell(name='Bottom Reflector')

    refined_reflector = openmoc.Universe(name='Semi-Finely Spaced Moderator')
    right_reflector = openmoc.Universe(name='Right Reflector')
    corner_reflector = openmoc.Universe(name='Bottom Corner Reflector')
    bottom_reflector = openmoc.Universe(name='Bottom Reflector')

    refined_reflector.addCell(refined_reflector_cell)
    right_reflector.addCell(right_reflector_cell)
    corner_reflector.addCell(corner_reflector_cell)
    bottom_reflector.addCell(bottom_reflector_cell)

    # Initialize a list of reflector lattices
    lattices = list()

    # Sliced up water cells - semi finely spaced
    lattices.append(openmoc.Lattice(name='Semi-Finely Spaced Reflector'))
    lattices[-1].setWidth(width_x=1.25984/10., width_y=1.25984/10.)
    template = [[reflector] * 10] * 10
    lattices[-1].setUniverses([template])
    refined_reflector_cell.setFill(lattices[-1])

    # Sliced up water cells - right side of geometry
    lattices.append(openmoc.Lattice(name='Right Reflector'))
    lattices[-1].setWidth(width_x=1.25984, width_y=1.25984)
    template = [[refined_reflector] * 11 + [reflector] * 6] * 17
    lattices[-1].setUniverses([template])
    right_reflector_cell.setFill(lattices[-1])

    # Sliced up water cells for bottom corner of geometry
    lattices.append(openmoc.Lattice(name='Bottom Corner Reflector'))
    lattices[-1].setWidth(width_x=1.25984, width_y=1.25984)
    template = [[refined_reflector] * 11 + [reflector] * 6] * 11
    template += [[reflector] * 17] * 6
    lattices[-1].setUniverses([template])
    corner_reflector_cell.setFill(lattices[-1])

    # Sliced up water cells for bottom of geometry
    lattices.append(openmoc.Lattice(name='Bottom Reflector'))
    lattices[-1].setWidth(width_x=1.25984, width_y=1.25984)
    template = [[refined_reflector] * 17] * 11
    template += [[reflector] * 17] * 6
    lattices[-1].setUniverses([template])
    bottom_reflector_cell.setFill(lattices[-1])

    # Find the root cell
    all_cells = openmoc_geometry.getAllCells()
    for cell_id in all_cells:
        if all_cells[cell_id].getName() == 'root cell':
            root_cell = all_cells[cell_id]

    # Extract core lattice
    core_lattice = root_cell.getFillUniverse()
    core_lattice = openmoc.castUniverseToLattice(core_lattice)

    # Assign reflector universes to core lattice
    core_lattice.updateUniverse(0, 0, 0, bottom_reflector)
    core_lattice.updateUniverse(1, 0, 0, bottom_reflector)
    core_lattice.updateUniverse(2, 0, 0, corner_reflector)
    core_lattice.updateUniverse(2, 1, 0, right_reflector)
    core_lattice.updateUniverse(2, 2, 0, right_reflector)
