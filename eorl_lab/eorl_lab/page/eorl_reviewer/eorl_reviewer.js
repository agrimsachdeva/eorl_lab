frappe.pages['eorl-reviewer'].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: 'EORL Reviewer Walkthrough', single_column: true });
	page.add_label('Approximate time: 5 minutes');

	const $body = $(
		`<div style="padding: 15px; max-width: 1000px;">
			<p>
				<b>EORL</b> (Executable Organizational Routine Laboratory) is research infrastructure: a
				laboratory in which an organizational theory is written down as an executable
				organization (roles, authority, memory, communication and a routine on a real ERP
				system), run by computational actors, branched into counterfactual histories,
				recorded as an append-only process trace, and analyzed with design-aware inference.
			</p>
			<p class="text-muted">
				<b>Demonstration 1: Agentic Routinization and Adaptive Repertoire</b> is the first use
				of the instrument. Its runs are labeled as demonstrations or validation, not as tests of
				the theory. Each step below opens one real record on this site. Your account is
				<span class="eorl-ro"></span>.
			</p>
			<div class="eorl-artifact text-muted" style="font-size: 12px; margin-bottom: 15px;"></div>
			<div class="eorl-steps"></div>
			<p style="margin-top: 20px;"><a href="/app/eorl-evaluation-matrix">Special-issue evaluation matrix</a> ·
				<a href="/app/eorl-lab">All EORL pages</a></p>
		</div>`
	).appendTo(page.body);

	frappe.call({
		method: 'eorl_lab.api.reviewer.get_reviewer_walkthrough',
		callback(r) {
			const d = r.message;
			$body.find('.eorl-ro').text(d.user_is_read_only ? 'read-only: you can open and compute everything, and nothing you do is saved' : 'able to write records');
			const a = d.artifact || {};
			if (a.commit) {
				$body.find('.eorl-artifact').html(`Artifact ${frappe.utils.escape_html(a.version || '')}, release ${frappe.utils.escape_html(a.release_tag || '')}, commit <code>${frappe.utils.escape_html((a.commit || '').slice(0, 12))}</code>, ${a.tests ? `${a.tests.count} automated tests` : ''}.`);
			}
			const $steps = $body.find('.eorl-steps');
			d.steps.forEach((s) => {
				const button = s.available
					? `<button class="btn btn-primary btn-sm eorl-go" data-n="${s.n}">Open${s.record ? ` ${frappe.utils.escape_html(s.record)}` : ''}</button>`
					: '<span class="text-muted">Not available on this site.</span>';
				const children = s.children && s.children.length ? `<div class="text-muted" style="font-size:12px;">Children: ${s.children.map((c) => `<a href="/app/eorl-run/${c}">${c}</a>`).join(', ')}</div>` : '';
				$(`<div class="frappe-card" style="padding: 12px; margin-bottom: 10px;">
						<div style="display:flex; justify-content:space-between; align-items:center;">
							<h5 style="margin:0;">${s.n}. ${frappe.utils.escape_html(s.title)}</h5>${button}
						</div>
						<div style="margin-top:6px;">${frappe.utils.escape_html(s.what)}</div>
						<div class="text-muted" style="font-size:12px; margin-top:4px;"><b>Look for:</b> ${frappe.utils.escape_html(s.look_for)}</div>
						${children}
					</div>`).appendTo($steps);
			});
			$steps.on('click', '.eorl-go', function () {
				const s = d.steps.find((x) => x.n === $(this).data('n'));
				if (s.route_options) frappe.route_options = s.route_options;
				frappe.set_route(s.route.replace(/^\/app\//, '').split('/'));
			});
		},
	});
};
