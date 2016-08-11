import openmoc


def discretize_geometry(mat_mgxslib, openmoc_geometry):
    """Discretize a 2x2 checkerboard of BEAVRS fuel assemblies surrounded by
    a water reflector into OpenMOC flat source regions."""

    openmoc.log.py_printf('INFO', 'Discretizing the geometry...')

    opencg_geometry = mat_mgxslib.opencg_geometry
    all_cells = openmoc_geometry.getAllMaterialCells()

    # Add angular sectors to all material-filled cells
    for cell_id in all_cells:
        all_cells[cell_id].setNumSectors(8)

    # Get the bounding box from the OpenCG geometry
    min_x = opencg_geometry.min_x
    min_y = opencg_geometry.min_y
    min_z = opencg_geometry.min_z
    max_x = opencg_geometry.max_x
    max_y = opencg_geometry.max_y
    max_z = opencg_geometry.max_z
    mid_x = (max_x + min_x) / 2.
    mid_y = (max_y + min_y) / 2.
    mid_z = (max_z + min_z) / 2.

    ###########################################################################
    # Discretize the instr. and guide tubes in assemblies along diagonal
    ###########################################################################

    # Get the middle of the top left fuel assembly
    assm_x = mid_x - 1.25984 * 17.
    assm_y = mid_y + 1.25984 * 17.

    # Discretize the guide and instrument tubes
    instr_tube = opencg_geometry.find_cell(x=assm_x, y=assm_y, z=mid_z)
    guide_tube = opencg_geometry.find_cell(x=assm_x, y=assm_y+3.77952, z=mid_z)
    instr_tube = all_cells[instr_tube.id]
    guide_tube = all_cells[guide_tube.id]
    instr_tube.setNumRings(10)
    guide_tube.setNumRings(10)

    # Discretize the guide and instrument tubes
    instr_tube_moderator = opencg_geometry.find_cell(x=assm_x+0.6, y=assm_y+0.6, z=mid_z)
    guide_tube_moderator = opencg_geometry.find_cell(x=assm_x+0.6, y=assm_y+3.77952+0.6, z=mid_z)
    instr_tube_moderator = all_cells[instr_tube_moderator.id]
    guide_tube_moderator = all_cells[guide_tube_moderator.id]
    instr_tube_moderator.setNumRings(5)
    guide_tube_moderator.setNumRings(5)

    ###########################################################################
    # Discretize the instr., guide tubes and BAs in assemblies off diagonal
    ###########################################################################

    # Get the middle of the top right fuel assembly
    assm_x = mid_x
    assm_y = mid_y + 1.25984 * 17.

    # Discretize the guide and instrument tubes
    instr_tube = opencg_geometry.find_cell(x=assm_x, y=assm_y, z=mid_z)
    guide_tube = opencg_geometry.find_cell(x=assm_x, y=assm_y+3.77952, z=mid_z)
    burn_abs1 = opencg_geometry.find_cell(x=assm_x, y=assm_y+7.55904, z=mid_z)
    burn_abs2 = opencg_geometry.find_cell(x=assm_x, y=assm_y+7.55904+0.3, z=mid_z)
    instr_tube = all_cells[instr_tube.id]
    guide_tube = all_cells[guide_tube.id]
    burn_abs1 = all_cells[burn_abs1.id]
    burn_abs2 = all_cells[burn_abs2.id]
    instr_tube.setNumRings(10)
    guide_tube.setNumRings(10)
    burn_abs1.setNumRings(5)
    burn_abs2.setNumRings(5)

    # Discretize the guide and instrument tubes and burnable absorber moderator
    instr_tube_moderator = opencg_geometry.find_cell(x=assm_x+0.6, y=assm_y+0.6, z=mid_z)
    guide_tube_moderator = opencg_geometry.find_cell(x=assm_x+0.6, y=assm_y+3.77952+0.6, z=mid_z)
    burn_abs_moderator = opencg_geometry.find_cell(x=assm_x+0.6, y=assm_y+7.55904+0.6, z=mid_z)
    instr_tube_moderator = all_cells[instr_tube_moderator.id]
    guide_tube_moderator = all_cells[guide_tube_moderator.id]
    burn_abs_moderator = all_cells[burn_abs_moderator.id]
    instr_tube_moderator.setNumRings(5)
    guide_tube_moderator.setNumRings(5)
    burn_abs_moderator.setNumRings(5)

    ###########################################################################
    # Discretize the moderator cells around the fuel pins in both assemblies
    ###########################################################################

    # Find the fuel clad outer radius zcylinder
    all_surfs = openmoc_geometry.getAllSurfaces()
    for surf_id in all_surfs:
        if all_surfs[surf_id].getName() == 'Fuel clad OR':
            fuel_or = openmoc.castSurfaceToZCylinder(all_surfs[surf_id])

    # Discretize the moderator cell. First, add the fuel clad outer radius to each
    # cell since this is not done by the BEAVRS builder but is needed for ringify
    top_left = opencg_geometry.find_cell(x=min_x+0.1, y=max_y-0.1, z=mid_z)
    top_right = opencg_geometry.find_cell(x=min_x+1.25984*17, y=max_y-0.1, z=mid_z)
    top_left = all_cells[top_left.id]
    top_right = all_cells[top_right.id]
    top_left.addSurface(surface=fuel_or, halfspace=+1)
    top_right.addSurface(surface=fuel_or, halfspace=+1)
    top_left.setNumRings(10)
    top_right.setNumRings(10)

    ###########################################################################
    # Discretize the fuel pin cells in both assemblies
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

    # Discretize all cells within each pin cell universe into rings and sectors
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
    water = top_left.getFillMaterial()
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