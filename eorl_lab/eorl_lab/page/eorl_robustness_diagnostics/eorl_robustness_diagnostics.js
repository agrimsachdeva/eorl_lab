frappe.pages['eorl-robustness-diagnostics'].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'EORL Robustness & Replication Diagnostics',
		single_column: true,
	});

	const $body = $(
		`<div style="padding: 15px;">
			<p class="text-muted">
				SOTA Milestone 8 (spec sections 47-48). Both diagnostics read
				the same run-level outcome values a
				<a href="/app/eorl-scientific-cockpit">Scientific Cockpit</a>
				comparison would -- these are exploratory robustness checks on
				an existing comparison, not new confirmatory results, so
				nothing here is persisted as an <code>EORL Analysis Result</code>.
			</p>
			<div class="row" style="margin-bottom: 10px;">
				<div class="col-sm-4">
					<label class="text-muted">Analysis Plan</label>
					<select class="form-control eorl-plan-select"><option value="">Select a plan...</option></select>
				</div>
				<div class="col-sm-4">
					<label class="text-muted">Group A Runs</label>
					<select multiple class="form-control eorl-group-a-select" style="height: 100px;"></select>
				</div>
				<div class="col-sm-4">
					<label class="text-muted">Group B Runs</label>
					<select multiple class="form-control eorl-group-b-select" style="height: 100px;"></select>
				</div>
			</div>
			<button class="btn btn-primary eorl-run-diagnostics-btn">Run Diagnostics</button>

			<h5 style="margin-top: 25px;">Replication Stability</h5>
			<p class="text-muted">Running mean-difference estimate as runs accumulate, one group at a time.</p>
			<div class="eorl-trajectory-chart"></div>

			<h5 style="margin-top: 25px;">Robustness (Leave-One-Run-Out)</h5>
			<p class="text-muted">
				Full-sample estimate vs. re-estimating with each run excluded, one at a time.
				A result that shifts a lot with ONE exclusion is less robust than one that doesn't.
			</p>
			<div class="eorl-max-deviation text-muted" style="margin-bottom: 10px;"></div>
			<div class="eorl-forest-plot"></div>
		</div>`
	).appendTo(page.body);

	const $planSelect = $body.find('.eorl-plan-select');
	const $groupA = $body.find('.eorl-group-a-select');
	const $groupB = $body.find('.eorl-group-b-select');
	const $trajectoryChart = $body.find('.eorl-trajectory-chart');
	const $maxDeviation = $body.find('.eorl-max-deviation');
	const $forestPlot = $body.find('.eorl-forest-plot');

	frappe.call({
		method: 'frappe.client.get_list',
		args: { doctype: 'EORL Analysis Plan', fields: ['name'], limit_page_length: 100 },
		callback(r) {
			(r.message || []).forEach((p) => $planSelect.append(`<option value="${p.name}">${p.name}</option>`));
		},
	});
	frappe.call({
		method: 'eorl_lab.api.runs.list_runs',
		args: { limit: 200 },
		callback(r) {
			(r.message || []).forEach((run) => {
				const label = `${run.name} (${run.status})`;
				$groupA.append(`<option value="${run.name}">${label}</option>`);
				$groupB.append(`<option value="${run.name}">${label}</option>`);
			});
		},
	});

	function render_forest_plot(rows) {
		const allBounds = [];
		rows.forEach((r) => {
			if (r.ci_95[0] !== null) allBounds.push(r.ci_95[0], r.ci_95[1]);
		});
		const min = Math.min(...allBounds), max = Math.max(...allBounds);
		const range = max - min || 1;
		const toPct = (v) => ((v - min) / range) * 100;

		let html = '';
		rows.forEach((row) => {
			const isBaseline = row.excluded === null;
			const left = row.ci_95[0] !== null ? toPct(row.ci_95[0]) : 50;
			const width = row.ci_95[0] !== null ? toPct(row.ci_95[1]) - left : 0;
			const markerLeft = row.mean_diff !== null ? toPct(row.mean_diff) : 50;
			html += `
				<div style="display: flex; align-items: center; margin-bottom: 4px; ${isBaseline ? 'font-weight: bold;' : ''}">
					<div style="width: 160px; font-size: 12px;" title="${row.label}">${row.label}</div>
					<div style="flex: 1; position: relative; height: 18px; background: var(--card-bg); border-left: 1px solid var(--border-color);">
						<div style="position: absolute; left: ${left}%; width: ${width}%; height: 4px; top: 7px; background: ${isBaseline ? '#5e64ff' : '#b0b3ff'};"></div>
						<div style="position: absolute; left: ${markerLeft}%; top: 3px; width: 10px; height: 10px; border-radius: 50%; background: ${isBaseline ? '#5e64ff' : '#8890ff'}; transform: translateX(-50%);"></div>
					</div>
					<div style="width: 90px; font-size: 11px; text-align: right;">${row.mean_diff !== null ? row.mean_diff.toFixed(3) : 'n/a'}</div>
				</div>`;
		});
		$forestPlot.html(html);
	}

	$body.find('.eorl-run-diagnostics-btn').on('click', () => {
		const plan = $planSelect.val();
		const groupA = $groupA.val() || [];
		const groupB = $groupB.val() || [];
		if (!plan || groupA.length < 3 || groupB.length < 3) {
			frappe.msgprint('Select a plan and at least 3 runs per group (robustness needs 2 remaining after exclusion).');
			return;
		}

		frappe.call({
			method: 'eorl_lab.api.analysis.compute_replication_diagnostics',
			args: { analysis_plan_name: plan, run_ids_group_a: groupA, run_ids_group_b: groupB },
			callback(r) {
				const trajectory = r.message.trajectory;
				$trajectoryChart.empty();
				new frappe.Chart($trajectoryChart[0], {
					title: 'Mean Difference vs. N (cumulative)',
					data: {
						labels: trajectory.map((p) => `n=${p.n_per_group}`),
						datasets: [{ name: 'Mean Diff', values: trajectory.map((p) => p.mean_diff) }],
					},
					type: 'line', height: 220, colors: ['#5e64ff'],
				});
			},
		});

		frappe.call({
			method: 'eorl_lab.api.analysis.compute_robustness_jackknife',
			args: { analysis_plan_name: plan, run_ids_group_a: groupA, run_ids_group_b: groupB },
			callback(r) {
				render_forest_plot(r.message.rows);
				$maxDeviation.text(`Max shift from any single exclusion: ${r.message.max_single_exclusion_deviation.toFixed(4)}`);
			},
		});
	});
};
