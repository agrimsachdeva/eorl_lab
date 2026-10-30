frappe.pages['eorl-survival-analysis'].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'EORL Survival Analysis',
		single_column: true,
	});

	const $body = $(
		`<div style="padding: 15px;">
			<p class="text-muted">
				SOTA Milestone 9 (spec section 44.4: "Time to recovery / completion
				-> Kaplan-Meier visualization"). Pick runs launched with a regime
				shift -- a run that never recovers within its observed episodes
				becomes a right-censored observation, not a dropped data point.
			</p>
			<div class="row" style="margin-bottom: 10px;">
				<div class="col-sm-8">
					<label class="text-muted">Runs (select 2 or more, each launched with a regime shift)</label>
					<select multiple class="form-control eorl-run-multiselect" style="height: 140px;"></select>
				</div>
				<div class="col-sm-4"><label class="text-muted">&nbsp;</label><div>
					<button class="btn btn-primary eorl-analyze-btn">Run Survival Analysis</button></div></div>
			</div>
			<div class="eorl-km-summary text-muted" style="margin-bottom: 10px;"></div>
			<div class="eorl-km-chart"></div>
			<div class="table-responsive" style="margin-top: 20px;">
				<table class="table table-bordered" style="background: var(--card-bg);">
					<thead><tr><th>Run</th><th>Episodes to recover</th><th>Recovered?</th></tr></thead>
					<tbody class="eorl-km-runs-rows"></tbody>
				</table>
			</div>
		</div>`
	).appendTo(page.body);

	const $select = $body.find('.eorl-run-multiselect');
	const $summary = $body.find('.eorl-km-summary');
	const $chart = $body.find('.eorl-km-chart');
	const $runsRows = $body.find('.eorl-km-runs-rows');

	frappe.call({
		method: 'eorl_lab.api.runs.list_runs',
		args: { limit: 200 },
		callback(r) {
			(r.message || []).forEach((run) => {
				$select.append(`<option value="${run.name}">${run.name} (${run.status})</option>`);
			});
		},
	});

	$body.find('.eorl-analyze-btn').on('click', () => {
		const runs = $select.val() || [];
		if (runs.length < 2) {
			frappe.msgprint('Select at least 2 runs.');
			return;
		}
		frappe.call({
			method: 'eorl_lab.api.process.get_survival_analysis_data',
			args: { run_ids: runs },
			callback(r) {
				const d = r.message;
				$summary.text(
					`N runs: ${d.n_runs} (${d.n_events} recovered, ${d.n_censored} censored). ` +
					(d.median_recovery_time !== null
						? `Median recovery time: ${d.median_recovery_time} episodes.`
						: 'Median recovery time: not reached (fewer than half the runs ever recovered).')
				);

				$chart.empty();
				new frappe.Chart($chart[0], {
					title: 'Kaplan-Meier Survival Curve (fraction not-yet-recovered)',
					data: {
						labels: d.survival_function.map((p) => `t=${p.time}`),
						datasets: [{ name: 'Survival probability', values: d.survival_function.map((p) => p.survival_probability) }],
					},
					type: 'line', height: 250, colors: ['#5e64ff'],
				});

				$runsRows.empty();
				d.runs.forEach((row) => {
					$runsRows.append(
						`<tr><td>${row.run}</td><td>${row.duration}</td><td>${row.event_observed ? 'yes' : 'no (censored)'}</td></tr>`
					);
				});
			},
		});
	});
};
