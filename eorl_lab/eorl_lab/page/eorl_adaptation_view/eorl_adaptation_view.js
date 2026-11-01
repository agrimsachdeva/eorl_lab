frappe.pages['eorl-adaptation-view'].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'EORL Adaptation / Event-Study View',
		single_column: true,
	});

	const $body = $(
		`<div style="padding: 15px;">
			<p class="text-muted">
				Pre- and post-shock behavior of one run. Utility is 1 for a completed episode with no
				rejected units and falls with the share rejected on inspection. Repertoire is reported
				as three separate sets: paths observed, paths that were viable (completed, no hard
				violation, utility &ge; 0.9), and pre-shock viable paths that were used viably after the
				shock. The shock is never shown to the actors, only to the researcher here.
			</p>
			<div class="row" style="margin-bottom: 15px;">
				<div class="col-sm-4">
					<label class="text-muted">Run</label>
					<select class="form-control eorl-run-select"><option value="">Select a run...</option></select>
				</div>
			</div>
			<div class="eorl-shock-note text-muted" style="margin-bottom: 10px;"></div>
			<div class="eorl-trajectory-chart"></div>
			<div class="row">
				<div class="col-sm-6"><h5>Adaptive repertoire</h5><table class="table table-bordered table-sm" style="background: var(--card-bg);"><tbody class="eorl-rep-rows"></tbody></table></div>
				<div class="col-sm-6"><h5>Shock adaptation</h5><table class="table table-bordered table-sm" style="background: var(--card-bg);"><tbody class="eorl-shock-rows"></tbody></table></div>
			</div>
			<div class="table-responsive" style="margin-top: 20px;">
				<table class="table table-bordered" style="background: var(--card-bg);">
					<thead><tr><th>Episode</th><th>Phase</th><th>Success</th><th>Utility</th><th>Supplier</th><th>Viable</th><th>In pre-shock repertoire</th></tr></thead>
					<tbody class="eorl-phase-rows"></tbody>
				</table>
			</div>
		</div>`
	).appendTo(page.body);

	const $runSelect = $body.find('.eorl-run-select');
	const $shockNote = $body.find('.eorl-shock-note');
	const $chartContainer = $body.find('.eorl-trajectory-chart');
	const $phaseRows = $body.find('.eorl-phase-rows');
	let current = null;

	const PHASE_COLORS = { warmup: '', stable: '', shock: 'background-color: rgba(255,99,71,0.15);', recovery: 'background-color: rgba(255,205,86,0.15);' };
	const fmt = (v) => (v === null || v === undefined ? '—' : typeof v === 'number' ? (Number.isInteger(v) ? v : v.toFixed(3)) : frappe.utils.escape_html(JSON.stringify(v)));
	const yn = (v) => (v ? 'yes' : 'no');

	eorl_lab.export.buttons(page, () => current && {
		name: `adaptation_${current.run}`,
		columns: ['episode_number', 'phase', 'success', 'utility', 'chosen_supplier', 'viable', 'in_pre_shock_repertoire'],
		rows: current.episodes,
		data: current,
		metadata: { run_ids: [current.run], view: 'adaptation_trajectory', regime_shift_trigger_episode: current.regime_shift_trigger_episode,
			viability_criterion: current.repertoire.viability_criterion, utility_threshold: current.repertoire.utility_threshold,
			sequence_scope: 'consequential_actions' },
		specification: { endpoint: 'eorl_lab.api.process.get_adaptation_view_data', args: { run: current.run } },
	});

	function load() {
		const run = $runSelect.val();
		if (!run) return;
		frappe.call({
			method: 'eorl_lab.api.process.get_adaptation_view_data',
			args: { run },
			callback(r) {
				const data = (current = r.message);
				$shockNote.text(
					data.regime_shift_trigger_episode
						? `Regime shift triggered at episode ${data.regime_shift_trigger_episode} (hidden from agents).`
						: 'This run has no regime shift in its own episodes. A branch child that starts after the shock has only post-shock episodes.'
				);

				$chartContainer.empty();
				new frappe.Chart($chartContainer[0], {
					title: 'Episode utility',
					data: { labels: data.episodes.map((e) => `Ep ${e.episode_number}`), datasets: [{ name: 'Utility', values: data.episodes.map((e) => e.utility) }],
						yMarkers: [{ label: 'viability threshold', value: data.repertoire.utility_threshold }] },
					type: 'line', height: 250, colors: ['#5e64ff'],
				});

				const rep = data.repertoire;
				const repKeys = ['observed_path_count', 'viable_path_count', 'viable_path_entropy', 'viable_path_concentration', 'pre_shock_repertoire_size',
					'pre_shock_repertoire_entropy', 'activated_after_shock_paths', 'adaptive_repertoire_utilization', 'post_shock_reuse_rate',
					'post_shock_novel_path_rate', 'path_extinction_rate_v2', 'repertoire_retention', 'repertoire_activation_latency'];
				$body.find('.eorl-rep-rows').html(repKeys.filter((k) => k in rep).map((k) => `<tr><td>${k}</td><td>${fmt(rep[k])}</td></tr>`).join(''));
				const sa = data.shock_adaptation || {};
				$body.find('.eorl-shock-rows').html(Object.keys(sa).length
					? Object.entries(sa).filter(([k]) => k !== 'pre_shock_dominant_path').map(([k, v]) => `<tr><td>${k}</td><td>${fmt(v)}</td></tr>`).join('')
					: '<tr><td class="text-muted">Needs pre- and post-shock episodes in this run.</td></tr>');

				$phaseRows.empty();
				data.episodes.forEach((e) => {
					const isShock = data.regime_shift_trigger_episode && e.episode_number === data.regime_shift_trigger_episode;
					$phaseRows.append(
						`<tr style="${PHASE_COLORS[e.phase] || ''}" data-run="${run}">
							<td><a href="#" class="eorl-episode-drilldown" data-episode="${e.episode}">${e.episode_number}</a>${isShock ? ' <strong>(shift triggers here)</strong>' : ''}</td>
							<td>${e.phase}</td><td>${yn(e.success)}</td><td>${fmt(e.utility)}</td>
							<td>${frappe.utils.escape_html(e.chosen_supplier || '')}</td><td>${yn(e.viable)}</td><td>${yn(e.in_pre_shock_repertoire)}</td>
						</tr>`
					);
				});
			},
		});
	}

	frappe.call({
		method: 'eorl_lab.api.runs.list_runs',
		args: { limit: 500 },
		callback(r) {
			(r.message || []).forEach((run) => $runSelect.append(`<option value="${run.name}">${run.name} (${run.status})</option>`));
			const opts = frappe.route_options || {};
			frappe.route_options = null;
			if (opts.run) {
				if (!$runSelect.find(`option[value="${opts.run}"]`).length) $runSelect.append(`<option value="${opts.run}">${opts.run}</option>`);
				$runSelect.val(opts.run);
				load();
			}
		},
	});
	$runSelect.on('change', load);

	$phaseRows.on('click', '.eorl-episode-drilldown', function (ev) {
		ev.preventDefault();
		frappe.route_options = { run: $(this).closest('tr').data('run'), episode: $(this).data('episode') };
		frappe.set_route('eorl-trace-explorer');
	});
};
