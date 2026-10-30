frappe.pages['eorl-lab'].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'EORL Lab',
		single_column: true,
	});

	page.add_label('Executable Organizational Routine Laboratory');

	const studio_pages = [
		{ title: 'Experiment Studio', route: 'eorl-experiment-studio' },
		{ title: 'Run Monitor', route: 'eorl-run-monitor' },
		{ title: 'Trace Explorer', route: 'eorl-trace-explorer' },
		{ title: 'Compare Runs', route: 'eorl-compare-runs' },
		{ title: 'Scientific Cockpit', route: 'eorl-scientific-cockpit' },
		{ title: 'Process Explorer', route: 'eorl-process-explorer' },
		{ title: 'Network Explorer', route: 'eorl-network-explorer' },
		{ title: 'Adaptation / Event-Study View', route: 'eorl-adaptation-view' },
		{ title: 'Robustness & Replication Diagnostics', route: 'eorl-robustness-diagnostics' },
		{ title: 'Power / Precision Planner', route: 'eorl-power-planner' },
		{ title: 'Survival Analysis', route: 'eorl-survival-analysis' },
		{ title: 'Reproducibility / Export', route: 'eorl-reproducibility' },
	];

	const config_doctypes = [
		'EORL Settings',
		'EORL Model Profile',
		'EORL Memory Profile',
		'EORL Tool Policy',
		'EORL Agent Template',
		'EORL Architecture',
		'EORL Regime Shift',
		'EORL Experiment',
		'EORL Construct',
		'EORL Analysis Plan',
	];

	const $body = $(
		`<div class="eorl-lab-home" style="padding: 15px;">
			<p class="text-muted">
				Agent Studio, Architecture Designer (graphical), and Scenario Studio
				are not built yet -- architectures and agents are composed via their
				DocType forms (linked below) for now.
			</p>
			<h5>Studio &amp; Monitoring</h5>
			<div class="row eorl-studio-links" style="margin-bottom: 20px;"></div>
			<h5>Configuration</h5>
			<div class="row eorl-config-links"></div>
		</div>`
	).appendTo(page.body);

	const $studioRow = $body.find('.eorl-studio-links');
	const $configRow = $body.find('.eorl-config-links');

	studio_pages.forEach((p) => {
		$(
			`<div class="col-sm-4" style="margin-bottom: 15px;">
				<div class="frappe-card" style="padding: 12px;">
					<a href="/app/${p.route}">${p.title}</a>
				</div>
			</div>`
		).appendTo($studioRow);
	});

	config_doctypes.forEach((doctype) => {
		$(
			`<div class="col-sm-4" style="margin-bottom: 15px;">
				<div class="frappe-card" style="padding: 12px;">
					<a href="/app/${frappe.router.slug(doctype)}">${doctype}</a>
				</div>
			</div>`
		).appendTo($configRow);
	});
};
