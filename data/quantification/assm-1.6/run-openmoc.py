import glob
import types
import infermc
from discretize import discretize_geometry


statepoints = glob.glob('statepoint.*.h5')

# Initialize a Batchwise for the final statepoint
batchwise = infermc.batchwise.PerfectBatchwise()
batchwise.type = '{}-groups'.format(batchwise.num_fine_groups)
batchwise.sp_start = len(statepoints) - 1
batchwise.cell_mgxslib_filename = 'distribcell'
batchwise.mat_mgxslib_filename = 'material'
batchwise.zcoord = 205.
batchwise.log_level = 'INFO'
batchwise.with_cmfd = True

# Attach a method to discretize this geometry to the Batchwise instance
batchwise._discretize_geometry = types.MethodType(discretize_geometry, batchwise)

# Assign a clusterizer to the Batchwise
if batchwise.options.clusterizer_type == 'infinite':
    batchwise.clusterizer = infermc.clusterizer.NullClusterizer()
    batchwise.clusterizer._type = 'infinite'
    batchwise.mat_mgxslib_directories.append('../pin-1.6/')
elif batchwise.options.clusterizer_type == 'null':
    batchwise.clusterizer = infermc.clusterizer.NullClusterizer()
elif batchwise.options.clusterizer_type == 'degenerate':
    batchwise.clusterizer = infermc.clusterizer.DegenerateClusterizer()

# FIXME
import sklearn.cluster

# Initialize a scikit-learn clustering estimator
estimator = sklearn.cluster.AgglomerativeClustering()
estimator.n_clusters = batchwise.options.num_clusters

# If a basic clusterizer type ('null', 'degenerate', 'lns') was not specified
# as a command line argument initialize a clusterizer with scikit-learn
if batchwise.options.clusterizer_type == 'combined':
    clusterizer = infermc.clusterizer.CombinedClusterizer()
    batchwise.clusterizer = clusterizer
    batchwise.clusterizer.estimator = estimator
elif batchwise.options.clusterizer_type == 'pinch':
    clusterizer = infermc.clusterizer.PinchClusterizer(6e-6, 'U238', 'capture')
    batchwise.clusterizer = clusterizer
    batchwise.clusterizer.estimator = estimator

# Turn off MGXS plotting for speed
batchwise.clusterizer.plot_mgxs = False
batchwise.plot_materials = True
batchwise.plot_cells = True

# Execute OpenMOC simulations over all batches of clustered MGXS libraries
batchwise.execute()
