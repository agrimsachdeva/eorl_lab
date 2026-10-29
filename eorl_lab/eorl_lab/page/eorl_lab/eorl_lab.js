frappe.pages['eorl-lab'].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'EORL Lab',
		single_column: true,
	});

	page.add_label('Executable Organizational Routine Laboratory');

	const config_doctypes = [
		'EORL Settings',
		'EORL Model Profile',
		'EORL Memory Profile',
		'EORL Tool Policy',
		'EORL Agent Template',
	];

	const $body = $(
		`<div class="eorl-lab-home" style="padding: 15px;">
			<p class="text-muted">
				Milestone 1: app skeleton and configuration. Experiment Studio, Agent Studio,
				Architecture Designer, Scenario Studio, Run Monitor, Trace Explorer, Compare Runs,
				and Export are not implemented yet (later milestones).
			</p>
			<div class="row eorl-config-links"></div>
		</div>`
	).appendTo(page.body);

	const $row = $body.find('.eorl-config-links');

	config_doctypes.forEach((doctype) => {
		$(
			`<div class="col-sm-4" style="margin-bottom: 15px;">
				<div class="frappe-card" style="padding: 12px;">
					<a href="/app/${frappe.router.slug(doctype)}">${doctype}</a>
				</div>
			</div>`
		).appendTo($row);
	});
};
