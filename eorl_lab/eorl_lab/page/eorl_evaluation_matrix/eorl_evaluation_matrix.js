frappe.pages['eorl-evaluation-matrix'].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: 'EORL Evaluation Matrix', single_column: true });
	const $body = $(
		`<div style="padding: 15px;">
			<p class="text-muted">
				Each special-issue criterion, the EORL capability that answers it, the concrete evidence on
				this site, how a reviewer can check it, and its known limitation. Counts are read live from
				this site.
			</p>
			<div class="table-responsive"><table class="table table-bordered" style="background: var(--card-bg);">
				<thead><tr><th style="width:11%;">Criterion</th><th>EORL capability</th><th>Concrete evidence</th><th>Reviewer verification path</th><th>Known limitation</th></tr></thead>
				<tbody class="eorl-matrix-rows"></tbody></table></div>
			<p><a href="/app/eorl-reviewer">Back to the reviewer walkthrough</a></p>
		</div>`
	).appendTo(page.body);
	let current = null;
	eorl_lab.export.buttons(page, () => current && {
		name: 'eorl_evaluation_matrix', columns: ['criterion', 'capability', 'evidence', 'verify', 'limitation'], rows: current.rows,
		data: current, metadata: { view: 'evaluation_matrix', counts: current.counts },
	});
	frappe.call({
		method: 'eorl_lab.api.reviewer.get_evaluation_matrix',
		callback(r) {
			current = r.message;
			const esc = frappe.utils.escape_html;
			$body.find('.eorl-matrix-rows').html(current.rows.map((x) =>
				`<tr><th>${esc(x.criterion)}</th><td>${esc(x.capability)}</td><td>${esc(x.evidence)}</td><td>${esc(x.verify)}</td><td>${esc(x.limitation)}</td></tr>`).join(''));
		},
	});
};
