frappe.pages['eorl-lab'].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'EORL Lab',
		single_column: true,
	});

	page.add_label('Executable Organizational Routine Laboratory');

	const studio_pages = [
		{ title: 'Reviewer: Start Here', route: 'eorl-reviewer' },
		{ title: 'Evaluation Matrix', route: 'eorl-evaluation-matrix' },
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
		{ title: 'Paired-Branch Inference', route: 'eorl-paired-branch-inference' },
		{ title: 'Theory Compiler', route: 'eorl-theory-compiler' },
		{ title: 'Reproducibility / Export', route: 'eorl-reproducibility' },
	];

	// Submission-day plan section 1.1: the platform and its demonstrations
	// are separate concepts. These are the platform's building blocks.
	const config_doctypes = [
		['Constructs', 'EORL Construct'],
		['Actors (Agent Templates)', 'EORL Agent Template'],
		['Architectures', 'EORL Architecture'],
		['Routine Templates', 'EORL Routine Template'],
		['Process Grammars', 'EORL Process Grammar'],
		['Scenarios (Regime Shifts)', 'EORL Regime Shift'],
		['Memory', 'EORL Memory Profile'],
		['Authority (Tool Policies)', 'EORL Tool Policy'],
		['Communication', 'EORL Communication Policy'],
		['Actor Engines (Model Profiles)', 'EORL Model Profile'],
		['Experiments', 'EORL Experiment'],
		['Runs', 'EORL Run'],
		['Analysis Plans', 'EORL Analysis Plan'],
		['Analysis Results', 'EORL Analysis Result'],
		['Settings', 'EORL Settings'],
	];

	const $body = $(
		`<div class="eorl-lab-home" style="padding: 15px;">
			<div class="frappe-card" style="padding: 12px; margin-bottom: 20px;">
				<b>Reviewers:</b> <a href="/app/eorl-reviewer">start here</a> for a five-minute guided walkthrough,
				or see the <a href="/app/eorl-evaluation-matrix">evaluation matrix</a>.
			</div>
			<h4>EORL Lab</h4>
			<p class="text-muted">Reusable infrastructure for executable organizational theory. Agents and architectures are composed in the forms below.</p>
			<h5>Building blocks</h5>
			<div class="row eorl-config-links" style="margin-bottom: 20px;"></div>
			<h5>Studio, analysis and reproducibility</h5>
			<div class="row eorl-studio-links" style="margin-bottom: 20px;"></div>
			<h4>Demonstrations</h4>
			<p class="text-muted">Uses of the instrument. Each experiment is typed as infrastructure validation, theory demonstration or empirical study.</p>
			<div class="row eorl-demo-links"></div>
		</div>`
	).appendTo(page.body);

	const demos = [
		{ title: 'Demonstration 1: Agentic Routinization and Adaptive Repertoire', filter: { demonstration: 'Demonstration 1: Agentic Routinization and Adaptive Repertoire' } },
		{ title: 'Infrastructure validation experiments', filter: { experiment_type: 'infrastructure_validation' } },
		{ title: 'Theory demonstrations', filter: { experiment_type: 'theory_demonstration' } },
		{ title: 'Empirical studies', filter: { experiment_type: 'empirical_study' } },
	];
	demos.forEach((d) => {
		const $card = $(`<div class="col-sm-6" style="margin-bottom: 15px;"><div class="frappe-card" style="padding: 12px;"><a href="#">${d.title}</a></div></div>`)
			.appendTo($body.find('.eorl-demo-links'));
		$card.find('a').on('click', (e) => { e.preventDefault(); frappe.route_options = d.filter; frappe.set_route('List', 'EORL Experiment'); });
	});

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

	config_doctypes.forEach(([label, doctype]) => {
		$(
			`<div class="col-sm-4" style="margin-bottom: 15px;">
				<div class="frappe-card" style="padding: 12px;">
					<a href="/app/${frappe.router.slug(doctype)}">${label}</a>
				</div>
			</div>`
		).appendTo($configRow);
	});
};
