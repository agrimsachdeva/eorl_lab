from eorl_lab.patches.v1_seed_initial_constructs import execute as seed_initial_constructs
from eorl_lab.patches.v2_construct_registry_measures import execute as update_construct_registry
from eorl_lab.routines import seed_routine_templates


def after_install():
	# bench install-app marks every entry in patches.txt as already run, so a
	# fresh site never gets the seeds from the patches; run them here.
	seed_initial_constructs()
	update_construct_registry()
	seed_routine_templates()
