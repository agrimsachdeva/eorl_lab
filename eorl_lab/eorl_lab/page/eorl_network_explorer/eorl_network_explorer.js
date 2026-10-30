frappe.pages['eorl-network-explorer'].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'EORL Network Explorer',
		single_column: true,
	});

	const $body = $(
		`<div style="padding: 15px;">
			<p class="text-muted">
				SOTA Milestone 7 (spec section 42, scoped to the edge-weighted
				agent-message network Milestone 7's own
				<code>communication_network</code> metric already computes).
				Line thickness is proportional to message count.
			</p>
			<div class="row" style="margin-bottom: 15px;">
				<div class="col-sm-4">
					<label class="text-muted">Run</label>
					<select class="form-control eorl-run-select"><option value="">Select a run...</option></select>
				</div>
			</div>
			<svg class="eorl-network-svg" width="600" height="400" style="border: 1px solid var(--border-color); background: var(--card-bg);"></svg>
			<div class="table-responsive" style="margin-top: 15px;">
				<table class="table table-bordered" style="background: var(--card-bg);">
					<thead><tr><th>From</th><th>To</th><th>Message Count</th></tr></thead>
					<tbody class="eorl-network-rows"></tbody>
				</table>
			</div>
		</div>`
	).appendTo(page.body);

	const $runSelect = $body.find('.eorl-run-select');
	const $svg = $body.find('.eorl-network-svg');
	const $rows = $body.find('.eorl-network-rows');

	frappe.call({
		method: 'eorl_lab.api.runs.list_runs',
		args: { limit: 200 },
		callback(r) {
			(r.message || []).forEach((run) => {
				$runSelect.append(`<option value="${run.name}">${run.name} (${run.status})</option>`);
			});
		},
	});

	function render_svg(actors, edges) {
		const cx = 300, cy = 200, radius = 140;
		const positions = {};
		actors.forEach((actor, i) => {
			const angle = (2 * Math.PI * i) / Math.max(actors.length, 1) - Math.PI / 2;
			positions[actor] = { x: cx + radius * Math.cos(angle), y: cy + radius * Math.sin(angle) };
		});

		const maxCount = Math.max(1, ...edges.map((e) => e.count));
		let svgHtml = '';
		edges.forEach((edge) => {
			const from = positions[edge.from], to = positions[edge.to];
			if (!from || !to) return;
			const width = 1 + 6 * (edge.count / maxCount);
			svgHtml += `<line x1="${from.x}" y1="${from.y}" x2="${to.x}" y2="${to.y}"
				stroke="var(--text-muted, #888)" stroke-width="${width}" opacity="0.6" marker-end="url(#arrow)" />`;
		});
		actors.forEach((actor) => {
			const pos = positions[actor];
			svgHtml += `<circle cx="${pos.x}" cy="${pos.y}" r="26" fill="var(--bg-color, #fff)" stroke="var(--dark-border-color, #333)" stroke-width="2" />`;
			svgHtml += `<text x="${pos.x}" y="${pos.y}" text-anchor="middle" dominant-baseline="middle" font-size="10">${frappe.utils.escape_html(actor.slice(0, 12))}</text>`;
		});
		svgHtml =
			`<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
				<path d="M0,0 L6,3 L0,6 Z" fill="var(--text-muted, #888)" />
			</marker></defs>` + svgHtml;
		$svg.html(svgHtml);
	}

	$runSelect.on('change', () => {
		const run = $runSelect.val();
		if (!run) return;
		frappe.call({
			method: 'eorl_lab.api.process.get_network_explorer_data',
			args: { run },
			callback(r) {
				const data = r.message;
				render_svg(data.actors, data.edges);

				$rows.empty();
				data.edges.forEach((edge) => {
					$rows.append(`<tr><td>${edge.from}</td><td>${edge.to}</td><td>${edge.count}</td></tr>`);
				});
				if (!data.edges.length) {
					$rows.append('<tr><td colspan="3" class="text-muted">No agent-chosen messages in this run.</td></tr>');
				}
			},
		});
	});
};
