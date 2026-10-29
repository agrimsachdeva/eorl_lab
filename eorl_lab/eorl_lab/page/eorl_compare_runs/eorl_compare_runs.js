frappe.pages['eorl-compare-runs'].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'EORL Compare Runs',
		single_column: true,
	});

	const $body = $(
		`<div style="padding: 15px;">
			<p class="text-muted">
				Raw aggregates only (episode/event counts, success rate, distinct actor
				count) -- process-path and theory metrics (coherence, repertoire,
				entropy) are a later milestone.
			</p>
			<div class="row" style="margin-bottom: 10px;">
				<div class="col-sm-8">
					<select multiple class="form-control eorl-run-multiselect" style="height: 120px;"></select>
				</div>
				<div class="col-sm-4">
					<button class="btn btn-primary eorl-compare-btn">Compare</button>
				</div>
			</div>
			<table class="table table-bordered" style="background: var(--card-bg);">
				<thead>
					<tr>
						<th>Run</th><th>Status</th><th>Seed</th><th>Episodes</th>
						<th>Success Rate</th><th>Distinct Actors</th><th>Events</th>
					</tr>
				</thead>
				<tbody class="eorl-compare-rows"></tbody>
			</table>
		</div>`
	).appendTo(page.body);

	const $select = $body.find('.eorl-run-multiselect');
	const $rows = $body.find('.eorl-compare-rows');

	frappe.call({
		method: 'eorl_lab.api.runs.list_runs',
		args: { limit: 100 },
		callback(r) {
			(r.message || []).forEach((run) => {
				$select.append(`<option value="${run.name}">${run.name} (${run.status})</option>`);
			});
		},
	});

	$body.find('.eorl-compare-btn').on('click', () => {
		const selected = $select.val() || [];
		if (!selected.length) {
			frappe.msgprint('Select at least one run.');
			return;
		}
		frappe.call({
			method: 'eorl_lab.api.metrics.compare_runs',
			args: { runs: selected },
			callback(r) {
				const rows = r.message || [];
				$rows.empty();
				rows.forEach((row) => {
					$rows.append(
						`<tr>
							<td>${row.run}</td>
							<td>${row.status}</td>
							<td>${row.run_seed ?? ''}</td>
							<td>${row.episode_count}</td>
							<td>${row.success_rate === null ? '' : (row.success_rate * 100).toFixed(0) + '%'}</td>
							<td title="${row.actor_slots.join(', ')}">${row.distinct_actor_count}</td>
							<td>${row.event_count ?? ''}</td>
						</tr>`
					);
				});
			},
		});
	});
};
