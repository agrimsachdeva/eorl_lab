from eorl_lab.patches.v1_seed_initial_constructs import execute as seed_initial_constructs


def after_install():
	# bench install-app marks every entry in patches.txt as already run, so a
	# fresh site never gets the construct seed from the patch; run it here.
	seed_initial_constructs()
