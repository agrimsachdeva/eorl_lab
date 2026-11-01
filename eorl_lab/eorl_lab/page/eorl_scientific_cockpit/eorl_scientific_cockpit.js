frappe.pages['eorl-scientific-cockpit'].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'EORL Scientific Cockpit',
		single_column: true,
	});

	const $body = $(
		`<div style="padding: 15px;">
			<p class="text-muted">
				Pick a saved <a href="/app/eorl-analysis-plan">EORL Analysis Plan</a> and two groups of
				runs, then compare. Both the parametric and the distribution-free test are always
				computed for the plan's pairing mode; the plan names which one is primary. The unit of
				analysis is the run (the independence guardrail): episodes inside one run are not
				independent replications. Hedges' g carries a seeded bootstrap interval, the primary
				p-value is adjusted across the plan's multiple-testing family, and the plan's registered
				rule turns the result into an interpretation label.
			</p>
			<div class="alert alert-info eorl-readonly-note" style="display:none;">
				Read-only account: results are computed and shown but not saved. Stored results are
				listed under <a href="/app/eorl-analysis-result">EORL Analysis Result</a>.
			</div>
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
			<button class="btn btn-primary eorl-compare-btn">Compare</button>
			<div class="eorl-cockpit-summary" style="margin-top: 20px; display:none;">
				<div class="row">
					<div class="col-sm-3">
						<div class="card" style="padding: 12px;">
							<div class="text-muted">Independent N</div>
							<div class="eorl-n-runs" style="font-size: 20px;"></div>
							<div class="text-muted eorl-n-episodes" style="font-size: 11px;"></div>
						</div>
					</div>
					<div class="col-sm-3">
						<div class="card" style="padding: 12px;">
							<div class="text-muted">Mean A / Mean B</div>
							<div class="eorl-means" style="font-size: 20px;"></div>
						</div>
					</div>
					<div class="col-sm-3">
						<div class="card" style="padding: 12px;">
							<div class="text-muted">Hedges' g [95% CI]</div>
							<div class="eorl-effect" style="font-size: 20px;"></div>
							<div class="text-muted eorl-effect-ci-method" style="font-size: 11px;"></div>
						</div>
					</div>
					<div class="col-sm-3">
						<div class="card" style="padding: 12px;">
							<div class="text-muted">Pairing / scope</div>
							<div class="eorl-pairing" style="font-size: 16px;"></div>
							<div class="text-muted eorl-scope" style="font-size: 11px;"></div>
						</div>
					</div>
				</div>
				<div class="card eorl-interpretation" style="padding: 12px; margin-top: 12px;"></div>
				<table class="table table-bordered" style="margin-top: 15px; background: var(--card-bg);">
					<thead>
						<tr><th>Test</th><th>Raw p</th><th>Adjusted p</th><th>95% CI (raw difference)</th><th>Click-through</th></tr>
					</thead>
					<tbody class="eorl-test-rows"></tbody>
				</table>
				<div class="text-muted eorl-run-links" style="font-size: 12px;"></div>
			</div>
		</div>`
	).appendTo(page.body);

	let current = null;
	const fmtP = (p) => (p === null || p === undefined ? '—' : p < 0.0001 ? Number(p).toExponential(2) : Number(p).toFixed(4));
	const fmt = (v) => (v === null || v === undefined ? '—' : Number(v).toFixed(3));
	eorl_lab.export.buttons(page, () => current && {
		name: `analysis_${current.analysis_plan}`,
		columns: ['test', 'p_value', 'adjusted_p_value', 'mean_diff', 'ci_95'],
		rows: current.results,
		data: current,
		metadata: { analysis_plan_id: current.analysis_plan, metric: current.metric_name, sequence_scope: current.sequence_scope,
			run_ids_a: current.run_ids_a, run_ids_b: current.run_ids_b, persisted_results: current.analysis_result_names },
		specification: { analysis_plan: current.analysis_plan, primary_test: current.primary_test, multiplicity: current.multiplicity },
	});

	const $planSelect = $body.find('.eorl-plan-select');
	const $groupA = $body.find('.eorl-group-a-select');
	const $groupB = $body.find('.eorl-group-b-select');
	const $summary = $body.find('.eorl-cockpit-summary');
	const $testRows = $body.find('.eorl-test-rows');

	frappe.call({
		method: 'frappe.client.get_list',
		args: { doctype: 'EORL Analysis Plan', fields: ['name'], limit_page_length: 100 },
		callback(r) {
			(r.message || []).forEach((p) => $planSelect.append(`<option value="${p.name}">${p.name}</option>`));
		},
	});

	frappe.call({
		method: 'eorl_lab.api.runs.list_runs',
		args: { limit: 500 },
		callback(r) {
			(r.message || []).forEach((run) => {
				const label = `${run.name} (${run.status})`;
				$groupA.append(`<option value="${run.name}">${label}</option>`);
				$groupB.append(`<option value="${run.name}">${label}</option>`);
			});
		},
	});

	$body.find('.eorl-compare-btn').on('click', () => {
		const plan = $planSelect.val();
		const groupA = $groupA.val() || [];
		const groupB = $groupB.val() || [];
		if (!plan) {
			frappe.msgprint('Select an Analysis Plan.');
			return;
		}
		if (groupA.length < 2 || groupB.length < 2) {
			frappe.msgprint('Each group needs at least 2 independent runs.');
			return;
		}
		frappe.call({
			method: 'eorl_lab.api.analysis.compare_groups',
			args: { analysis_plan_name: plan, run_ids_group_a: groupA, run_ids_group_b: groupB },
			callback(r) {
				const result = (current = Object.assign(r.message, { run_ids_a: groupA, run_ids_b: groupB }));
				$summary.show();
				$body.find('.eorl-readonly-note').toggle(!result.persisted);
				$body.find('.eorl-n-runs').text(`${result.n_independent_runs_a} vs ${result.n_independent_runs_b} runs`);
				$body.find('.eorl-n-episodes').text(`${result.n_episodes_a} vs ${result.n_episodes_b} episodes (not the sample size used)`);
				$body.find('.eorl-means').text(`${fmt(result.mean_a)} / ${fmt(result.mean_b)}`);
				const g = result.standardized_effect_ci || {};
				$body.find('.eorl-effect').text(`${fmt(result.standardized_effect)} [${fmt(g.ci_low)}, ${fmt(g.ci_high)}]`);
				$body.find('.eorl-effect-ci-method').text(`${g.method || ''}, ${g.n_resamples || ''} resamples, seed ${g.seed || ''}`);
				$body.find('.eorl-pairing').text(result.paired ? 'Paired (branches)' : 'Independent groups');
				$body.find('.eorl-scope').text(`metric ${result.metric_name}; primary test ${result.primary_test}`);

				const it = result.interpretation || {};
				const m = result.multiplicity;
				$body.find('.eorl-interpretation').html(
					`<div class="text-muted">Registered interpretation</div>
					<div style="font-size: 20px;">${frappe.utils.escape_html(it.label || '—')}</div>
					<div class="text-muted" style="font-size: 11px;">rule cell: ${frappe.utils.escape_html(it.cell || '')}${m ? `; family ${frappe.utils.escape_html(m.family_id)} (${m.method}, ${m.family_size} outcomes)` : '; no multiple-testing family'}</div>`
				);

				$testRows.empty();
				result.results.forEach((test, i) => {
					const ci = test.ci_95 && test.ci_95[0] !== null ? `[${fmt(test.ci_95[0])}, ${fmt(test.ci_95[1])}]` : '—';
					const resultName = result.analysis_result_names[i];
					const link = resultName ? `<a href="/app/eorl-analysis-result/${resultName}">View full result &amp; provenance</a>` : '<span class="text-muted">not saved</span>';
					$testRows.append(
						`<tr><td>${test.test}${test.test === result.primary_test ? ' <b>(primary)</b>' : ''}</td>
							<td>${fmtP(test.p_value)}</td><td>${fmtP(test.adjusted_p_value)}</td><td>${ci}</td><td>${link}</td></tr>`
					);
				});
				const links = (ids) => ids.map((x) => `<a href="/app/eorl-run/${x}">${x}</a>`).join(', ');
				$body.find('.eorl-run-links').html(`Group A: ${links(groupA)}<br>Group B: ${links(groupB)}<br>Plan: <a href="/app/eorl-analysis-plan/${encodeURIComponent(result.analysis_plan)}">${frappe.utils.escape_html(result.analysis_plan)}</a>`);
			},
		});
	});
};
