frappe.pages['eorl-scientific-cockpit'].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'EORL Scientific Cockpit',
		single_column: true,
	});

	const $body = $(
		`<div style="padding: 15px;">
			<p class="text-muted">
				SOTA Milestone 5 (spec section 38, scoped to its KPI-card core):
				pick a saved <a href="/app/eorl-analysis-plan">EORL Analysis Plan</a> and
				two groups of runs, then compare. This always computes AND persists
				BOTH the parametric and the distribution-free test for whichever
				pairing mode the plan declares (spec section 44.4: "may recommend,
				but should never silently select") -- it never picks one for you.
				The plan's own <code>analysis_unit</code> must be "run"; this blocks
				outright otherwise (spec section 44.2's independence guardrail --
				episodes inside one run are not independent replications).
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
							<div class="text-muted">Standardized Effect (Hedges' g)</div>
							<div class="eorl-effect" style="font-size: 20px;"></div>
						</div>
					</div>
					<div class="col-sm-3">
						<div class="card" style="padding: 12px;">
							<div class="text-muted">Pairing</div>
							<div class="eorl-pairing" style="font-size: 20px;"></div>
						</div>
					</div>
				</div>
				<table class="table table-bordered" style="margin-top: 15px; background: var(--card-bg);">
					<thead>
						<tr><th>Test</th><th>p-value</th><th>95% CI</th><th>Click-through</th></tr>
					</thead>
					<tbody class="eorl-test-rows"></tbody>
				</table>
			</div>
		</div>`
	).appendTo(page.body);

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
		args: { limit: 200 },
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
				const result = r.message;
				$summary.show();
				$body.find('.eorl-n-runs').text(`${result.n_independent_runs_a} vs ${result.n_independent_runs_b} runs`);
				$body.find('.eorl-n-episodes').text(`${result.n_episodes_a} vs ${result.n_episodes_b} episodes (not the sample size used)`);
				$body.find('.eorl-means').text(`${result.mean_a.toFixed(3)} / ${result.mean_b.toFixed(3)}`);
				$body.find('.eorl-effect').text(result.standardized_effect.toFixed(3));
				$body.find('.eorl-pairing').text(result.paired ? 'Paired (branches)' : 'Independent groups');

				$testRows.empty();
				result.results.forEach((test, i) => {
					const ci = test.ci_95 ? `[${test.ci_95[0].toFixed(3)}, ${test.ci_95[1].toFixed(3)}]` : '—';
					const resultName = result.analysis_result_names[i];
					$testRows.append(
						`<tr>
							<td>${test.test}</td>
							<td>${test.p_value === null || test.p_value === undefined ? '—' : test.p_value.toFixed(4)}</td>
							<td>${ci}</td>
							<td><a href="/app/eorl-analysis-result/${resultName}">View full result &amp; provenance</a></td>
						</tr>`
					);
				});
			},
		});
	});
};
