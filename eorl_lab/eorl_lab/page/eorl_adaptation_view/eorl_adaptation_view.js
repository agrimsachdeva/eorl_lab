frappe.pages['eorl-adaptation-view'].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'EORL Adaptation / Event-Study View',
		single_column: true,
	});

	const $body = $(
		`<div style="padding: 15px;">
			<p class="text-muted">
				SOTA Milestone 7 (spec section 40, scoped to a per-episode
				performance trajectory). Pick a run that was launched with a
				regime shift to see its pre-/post-shock performance; the shift's
				trigger episode (if any) is called out below the chart and
				highlighted in the phase table -- it is never shown to the
				agents themselves (spec section 2.4), only to the researcher here.
			</p>
			<div class="row" style="margin-bottom: 15px;">
				<div class="col-sm-4">
					<label class="text-muted">Run</label>
					<select class="form-control eorl-run-select"><option value="">Select a run...</option></select>
				</div>
			</div>
			<div class="eorl-shock-note text-muted" style="margin-bottom: 10px;"></div>
			<div class="eorl-trajectory-chart"></div>
			<div class="table-responsive" style="margin-top: 20px;">
				<table class="table table-bordered" style="background: var(--card-bg);">
					<thead><tr><th>Episode</th><th>Phase</th><th>Success</th></tr></thead>
					<tbody class="eorl-phase-rows"></tbody>
				</table>
			</div>
		</div>`
	).appendTo(page.body);

	const $runSelect = $body.find('.eorl-run-select');
	const $shockNote = $body.find('.eorl-shock-note');
	const $chartContainer = $body.find('.eorl-trajectory-chart');
	const $phaseRows = $body.find('.eorl-phase-rows');
	let chart = null;

	const PHASE_COLORS = { warmup: '', stable: '', shock: 'background-color: rgba(255,99,71,0.15);', recovery: 'background-color: rgba(255,205,86,0.15);' };

	frappe.call({
		method: 'eorl_lab.api.runs.list_runs',
		args: { limit: 200 },
		callback(r) {
			(r.message || []).forEach((run) => {
				$runSelect.append(`<option value="${run.name}">${run.name} (${run.status})</option>`);
			});
		},
	});

	$runSelect.on('change', () => {
		const run = $runSelect.val();
		if (!run) return;
		frappe.call({
			method: 'eorl_lab.api.process.get_adaptation_view_data',
			args: { run },
			callback(r) {
				const data = r.message;

				$shockNote.text(
					data.regime_shift_trigger_episode
						? `Regime shift triggered at episode ${data.regime_shift_trigger_episode} (hidden from agents).`
						: 'This run has no regime shift -- a flat trajectory is expected.'
				);

				const labels = data.episodes.map((e) => `Ep ${e.episode_number}`);
				const values = data.episodes.map((e) => (e.success ? 1 : 0));

				if (chart) $chartContainer.empty();
				chart = new frappe.Chart($chartContainer[0], {
					title: 'Episode Success (1 = success, 0 = failure)',
					data: { labels, datasets: [{ name: 'Success', values }] },
					type: 'line',
					height: 250,
					colors: ['#5e64ff'],
					axisOptions: { yAxisMode: 'tick' },
				});

				$phaseRows.empty();
				data.episodes.forEach((e) => {
					const isShock = data.regime_shift_trigger_episode && e.episode_number === data.regime_shift_trigger_episode;
					const style = PHASE_COLORS[e.phase] || '';
					$phaseRows.append(
						`<tr style="${style}">
							<td>${e.episode_number}${isShock ? ' <strong>(shift triggers here)</strong>' : ''}</td>
							<td>${e.phase}</td>
							<td>${e.success ? 'yes' : 'no'}</td>
						</tr>`
					);
				});
			},
		});
	});
};
