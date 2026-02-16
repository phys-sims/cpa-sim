# map Config.kind -> implementation
# this lets cfgs pick the back end for the stage they are responsible for
# eg:
# FIBER_BACKENDS = {
#  "gnlse": GNLSEFiber,
#  "gnlse_sim": GNLSESimFiber,  # preferred v2 key (old alias: "fiber_sim")
# }

# Note: v1 uses WUST-FOG `gnlse` package; v2 `gnlse_sim` targets the phys-sims `gnlse-sim` repo.
