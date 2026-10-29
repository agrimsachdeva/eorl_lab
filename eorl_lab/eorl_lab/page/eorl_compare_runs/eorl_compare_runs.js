frappe.pages['eorl-compare-runs'].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'EORL Compare Runs',
		single_column: true,
	});

	const $body = $(
		`<div style="padding: 15px;">
			<p class="text-muted">
				Raw aggregates plus real coherence/variety metrics (Milestone 7).
				Process-path extraction and these metrics' full definitions live in
				<code>eorl_lab.analysis</code>; adaptation metrics (post-shock
				recovery) show up per-run via "Compute &amp; Persist Metrics" below,
				not in this side-by-side table.
			</p>
			<div class="row" style="margin-bottom: 10px;">
				<div class="col-sm-8">
					<select multiple class="form-control eorl-run-multiselect" style="height: 120px;"></select>
				</div>
				<div class="col-sm-4">
					<button class="btn btn-primary eorl-compare-btn">Compare</button>
				</div>
			</div>
			<div class="table-responsive">
				<table class="table table-bordered" style="background: var(--card-bg);">
					<thead>
						<tr>
							<th>Run</th><th>Status</th><th>Seed</th><th>Episodes</th>
							<th>Success Rate</th><th>Distinct Actors</th><th>Events</th>
							<th>Unique Paths</th><th>Sequence Entropy</th>
							<th>Actor Continuity</th><th>Avg Actor Run Length</th>
						</tr>
					</thead>
					<tbody class="eorl-compare-rows"></tbody>
				</table>
			</div>
			<hr>
			<h5>Compute &amp; Persist Full Metric Set (one run)</h5>
			<div class="row">
				<div class="col-sm-6">
					<select class="form-control eorl-metrics-run-select"></select>
				</div>
				<div class="col-sm-3">
					<button class="btn btn-default eorl-compute-metrics-btn">Compute &amp; Persist</button>
				</div>
			</div>
			<pre class="eorl-metrics-output" style="margin-top: 10px; max-height: 400px; overflow:auto;"></pre>
		</div>`
	).appendTo(page.body);

	const $select = $body.find('.eorl-run-multiselect');
	const $metricsRunSelect = $body.find('.eorl-metrics-run-select');
	const $rows = $body.find('.eorl-compare-rows');
	const $metricsOutput = $body.find('.eorl-metrics-output');

	frappe.call({
		method: 'eorl_lab.api.runs.list_runs',
		args: { limit: 100 },
		callback(r) {
			(r.message || []).forEach((run) => {
				$select.append(`<option value="${run.name}">${run.name} (${run.status})</option>`);
				$metricsRunSelect.append(`<option value="${run.name}">${run.name} (${run.status})</option>`);
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
							<td>${row.unique_sequence_count}</td>
							<td>${row.sequence_entropy.toFixed(3)}</td>
							<td>${(row.actor_continuity * 100).toFixed(0)}%</td>
							<td>${row.average_actor_run_length.toFixed(2)}</td>
						</tr>`
					);
				});
			},
		});
	});

	$body.find('.eorl-compute-metrics-btn').on('click', () => {
		const run = $metricsRunSelect.val();
		if (!run) return;
		$metricsOutput.text('Computing...');
		frappe.call({
			method: 'eorl_lab.api.metrics.compute_run_metrics',
			args: { run_name: run },
			callback(r) {
				$metricsOutput.text(JSON.stringify(r.message.metrics, null, 2));
			},
		});
	});
};
