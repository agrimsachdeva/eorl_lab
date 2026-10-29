frappe.pages['eorl-experiment-studio'].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'EORL Experiment Studio',
		single_column: true,
	});

	page.set_primary_action('New Experiment', () => frappe.new_doc('EORL Experiment'), 'add');

	const $body = $(
		`<div style="padding: 15px;">
			<p class="text-muted">
				Compose architectures, agents, and tool policies as ordinary DocType
				records first (links below), then pick a saved EORL Experiment here to
				review and launch it. The full composition wizard (spec section 7.5's
				10-step flow) is a later milestone -- this is "review and launch",
				not "build from scratch in one screen".
			</p>
			<div class="row" style="margin-bottom: 15px;">
				<div class="col-sm-3"><a href="/app/eorl-architecture">Architectures</a></div>
				<div class="col-sm-3"><a href="/app/eorl-agent-template">Agent Templates</a></div>
				<div class="col-sm-3"><a href="/app/eorl-tool-policy">Tool Policies</a></div>
				<div class="col-sm-3"><a href="/app/eorl-regime-shift">Regime Shifts</a></div>
			</div>
			<div class="row" style="margin-bottom: 15px;">
				<div class="col-sm-6">
					<select class="form-control eorl-experiment-select"><option value="">Select an experiment...</option></select>
				</div>
			</div>
			<div class="eorl-experiment-summary" style="display:none;">
				<table class="table table-bordered" style="background: var(--card-bg); max-width: 500px;">
					<tbody>
						<tr><th>Architecture A</th><td class="eorl-arch-a"></td></tr>
						<tr><th>Architecture B</th><td class="eorl-arch-b"></td></tr>
						<tr><th>Regime Shift</th><td class="eorl-regime"></td></tr>
						<tr><th>Episodes / run</th><td class="eorl-episodes"></td></tr>
						<tr><th>Repetitions / cell</th><td class="eorl-reps"></td></tr>
						<tr><th>Cells</th><td class="eorl-cells"></td></tr>
						<tr><th><strong>Total runs</strong></th><td class="eorl-total-runs"><strong></strong></td></tr>
					</tbody>
				</table>
				<button class="btn btn-default eorl-validate-btn">Validate Only</button>
				<button class="btn btn-primary eorl-launch-btn">Launch Pilot</button>
				<div class="eorl-launch-status" style="margin-top: 10px;"></div>
			</div>
		</div>`
	).appendTo(page.body);

	const $select = $body.find('.eorl-experiment-select');
	const $summary = $body.find('.eorl-experiment-summary');
	const $status = $body.find('.eorl-launch-status');

	function load_experiments() {
		frappe.call({
			method: 'frappe.client.get_list',
			args: { doctype: 'EORL Experiment', fields: ['name', 'status'], limit_page_length: 100 },
			callback(r) {
				$select.find('option:not(:first)').remove();
				(r.message || []).forEach((exp) => {
					$select.append(`<option value="${exp.name}">${exp.name} (${exp.status})</option>`);
				});
			},
		});
	}

	function load_summary(experiment_name) {
		if (!experiment_name) {
			$summary.hide();
			return;
		}
		frappe.call({
			method: 'eorl_lab.api.experiments.get_experiment_summary',
			args: { experiment_name },
			callback(r) {
				const s = r.message;
				$summary.find('.eorl-arch-a').text(s.architecture_a || '-');
				$summary.find('.eorl-arch-b').text(s.architecture_b || '(single-cell)');
				$summary.find('.eorl-regime').text(s.regime_shift || '(none)');
				$summary.find('.eorl-episodes').text(s.episode_count);
				$summary.find('.eorl-reps').text(s.repetitions_per_cell);
				$summary.find('.eorl-cells').text(s.cell_count);
				$summary.find('.eorl-total-runs').html(`<strong>${s.total_run_count}</strong>`);
				$status.text('');
				$summary.show();
			},
		});
	}

	$select.on('change', () => load_summary($select.val()));

	$body.find('.eorl-validate-btn').on('click', () => {
		const experiment_name = $select.val();
		if (!experiment_name) return;
		frappe.call({
			method: 'eorl_lab.api.experiments.validate_experiment',
			args: { experiment_name },
			callback(r) {
				const v = r.message;
				$status.html(
					v.valid
						? `<span class="indicator-pill green">Valid</span> ${v.cell_count} cell(s), ${v.total_run_count} run(s).`
						: `<span class="indicator-pill red">Invalid</span> ${v.errors.join('; ')}`
				);
			},
		});
	});

	$body.find('.eorl-launch-btn').on('click', () => {
		const experiment_name = $select.val();
		if (!experiment_name) return;
		$status.text('Launching pilot (this runs synchronously -- may take a few seconds per run)...');
		frappe.call({
			method: 'eorl_lab.api.experiments.launch_pilot',
			args: { experiment_name },
			callback(r) {
				const result = r.message;
				const lines = result.runs.map(
					(run) => `${run.architecture} rep ${run.repetition} (seed ${run.seed}): ${run.run} - ${run.success ? 'success' : 'failed'}`
				);
				$status.html(`<div>Launched ${result.runs.length} run(s):</div><pre>${lines.join('\n')}</pre>`);
			},
		});
	});

	load_experiments();
};
