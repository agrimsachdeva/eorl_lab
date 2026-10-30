frappe.pages['eorl-paired-branch-inference'].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'EORL Paired-Branch Inference',
		single_column: true,
	});

	const $body = $(
		`<div style="padding: 15px;">
			<p class="text-muted">
				SOTA Milestone 10 (spec section 44.3). The generic
				<a href="/app/eorl-scientific-cockpit">Scientific Cockpit</a>
				can run a paired comparison, but gives no hint of which runs
				are actually sibling branches of each other -- this page lists
				a parent run's real <code>EORL Branch</code> records, grouped by
				branch point, so you pick genuine matched pairs instead of
				guessing run names.
			</p>
			<div class="row" style="margin-bottom: 10px;">
				<div class="col-sm-4">
					<label class="text-muted">Parent Run</label>
					<select class="form-control eorl-parent-run-select"><option value="">Select a run...</option></select>
				</div>
			</div>
			<div class="eorl-branch-groups"></div>

			<div class="row" style="margin-top: 20px; margin-bottom: 10px;">
				<div class="col-sm-4">
					<label class="text-muted">Analysis Plan (will be set to paired_by="branch_point")</label>
					<select class="form-control eorl-plan-select"><option value="">Select a plan...</option></select>
				</div>
				<div class="col-sm-4"><label class="text-muted">&nbsp;</label><div>
					<button class="btn btn-primary eorl-compare-btn">Compare Selected Pairs</button></div></div>
			</div>
			<div class="eorl-pair-result"></div>
		</div>`
	).appendTo(page.body);

	const $parentSelect = $body.find('.eorl-parent-run-select');
	const $groups = $body.find('.eorl-branch-groups');
	const $planSelect = $body.find('.eorl-plan-select');
	const $result = $body.find('.eorl-pair-result');

	frappe.call({
		method: 'eorl_lab.api.runs.list_runs',
		args: { limit: 200 },
		callback(r) {
			(r.message || []).forEach((run) => {
				$parentSelect.append(`<option value="${run.name}">${run.name} (${run.status})</option>`);
			});
		},
	});
	frappe.call({
		method: 'frappe.client.get_list',
		args: { doctype: 'EORL Analysis Plan', fields: ['name'], limit_page_length: 100 },
		callback(r) {
			(r.message || []).forEach((p) => $planSelect.append(`<option value="${p.name}">${p.name}</option>`));
		},
	});

	$parentSelect.on('change', () => {
		const parentRun = $parentSelect.val();
		if (!parentRun) return;
		frappe.call({
			method: 'eorl_lab.api.runs.list_branch_groups',
			args: { parent_run: parentRun },
			callback(r) {
				const groups = r.message.groups;
				$groups.empty();
				const episodes = Object.keys(groups);
				if (!episodes.length) {
					$groups.html('<p class="text-muted">This run has no branches yet -- create some via branch_run() first.</p>');
					return;
				}
				episodes.forEach((episode) => {
					const branches = groups[episode];
					let rows = branches.map((b, i) =>
						`<tr>
							<td>${b.child_run}</td>
							<td>${b.intervention_description || ''}</td>
							<td><label><input type="radio" name="group-${episode}-${b.child_run}-a" class="eorl-assign-a" data-run="${b.child_run}" data-episode="${episode}"> Group A</label></td>
							<td><label><input type="radio" name="group-${episode}-${b.child_run}-b" class="eorl-assign-b" data-run="${b.child_run}" data-episode="${episode}"> Group B</label></td>
						</tr>`
					).join('');
					$groups.append(
						`<div style="margin-top: 15px;">
							<strong>Branch point: episode ${episode}</strong> (${branches.length} sibling branch${branches.length > 1 ? 'es' : ''})
							<table class="table table-bordered" style="background: var(--card-bg); margin-top: 5px;">
								<thead><tr><th>Child Run</th><th>Intervention</th><th>Assign</th><th></th></tr></thead>
								<tbody>${rows}</tbody>
							</table>
						</div>`
					);
				});
			},
		});
	});

	// Simple radio-style assignment: clicking "Group A" for a run
	// deselects "Group B" for that same run, and vice versa.
	$groups.on('change', '.eorl-assign-a, .eorl-assign-b', function () {
		const $row = $(this).closest('tr');
		if ($(this).hasClass('eorl-assign-a')) {
			$row.find('.eorl-assign-b').prop('checked', false);
		} else {
			$row.find('.eorl-assign-a').prop('checked', false);
		}
	});

	$body.find('.eorl-compare-btn').on('click', () => {
		const plan = $planSelect.val();
		const groupA = $groups.find('.eorl-assign-a:checked').map(function () { return $(this).data('run'); }).get();
		const groupB = $groups.find('.eorl-assign-b:checked').map(function () { return $(this).data('run'); }).get();

		if (!plan || groupA.length < 2 || groupB.length !== groupA.length) {
			frappe.msgprint('Select an Analysis Plan, and assign at least 2 branches to each group with equal counts (one matched pair per branch point).');
			return;
		}

		frappe.call({
			method: 'frappe.client.set_value',
			args: { doctype: 'EORL Analysis Plan', name: plan, fieldname: 'paired_by', value: 'branch_point' },
			callback() {
				frappe.call({
					method: 'eorl_lab.api.analysis.compare_groups',
					args: { analysis_plan_name: plan, run_ids_group_a: groupA, run_ids_group_b: groupB },
					callback(r) {
						const result = r.message;
						let html = `<div class="card" style="padding: 12px; max-width: 600px;">
							<strong>Paired: ${result.paired}</strong><br>
							<strong>Standardized effect: ${result.standardized_effect.toFixed(3)}</strong><br>`;
						result.results.forEach((test, i) => {
							html += `${test.test}: p=${test.p_value === null ? 'n/a' : test.p_value.toFixed(4)}
								<a href="/app/eorl-analysis-result/${result.analysis_result_names[i]}">(view result)</a><br>`;
						});
						html += '</div>';
						$result.html(html);
					},
				});
			},
		});
	});
};
