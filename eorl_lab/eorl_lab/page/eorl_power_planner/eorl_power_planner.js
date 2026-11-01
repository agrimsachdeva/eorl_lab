frappe.pages['eorl-power-planner'].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'EORL Power / Precision Planner',
		single_column: true,
	});

	const $body = $(
		`<div style="padding: 15px;">
			<p class="text-muted">
				Monte Carlo power for the exact test <code>compare_groups</code> runs: Welch's t for
				independent runs, the paired t for sibling branches. Every estimate is seeded, so the
				same inputs always give the same number; the Monte Carlo standard error is shown with
				it. Effects are standardized: Hedges' g for independent groups, d<sub>z</sub> (mean
				within-pair difference over its SD) for paired branches.
			</p>
			<div class="row" style="margin-bottom: 10px;">
				<div class="col-sm-2"><label class="text-muted">Design</label>
					<select class="form-control eorl-design"><option value="independent">independent runs</option><option value="paired">paired branches</option></select></div>
				<div class="col-sm-2"><label class="text-muted">Alpha</label>
					<input type="number" step="0.01" class="form-control eorl-alpha-input" value="0.05"></div>
				<div class="col-sm-2"><label class="text-muted">Simulations</label>
					<input type="number" class="form-control eorl-nsim-input" value="2000"></div>
				<div class="col-sm-2"><label class="text-muted">Seed</label>
					<input type="number" class="form-control eorl-seed-input" value="20261101"></div>
			</div>

			<h5>Power table</h5>
			<div class="row" style="margin-bottom: 10px;">
				<div class="col-sm-3"><label class="text-muted">Effects (minimum meaningful)</label>
					<input type="text" class="form-control eorl-effects-input" value="0.3, 0.5, 0.8"></div>
				<div class="col-sm-3"><label class="text-muted">Runs (or pairs) per condition</label>
					<input type="text" class="form-control eorl-ns-input" value="5, 8, 10, 20, 27, 40"></div>
				<div class="col-sm-2"><label class="text-muted">&nbsp;</label><div>
					<button class="btn btn-primary eorl-grid-btn">Compute table</button></div></div>
			</div>
			<div class="table-responsive"><table class="table table-bordered table-sm" style="background: var(--card-bg);">
				<thead class="eorl-grid-head"></thead><tbody class="eorl-grid-rows"></tbody></table></div>
			<div class="text-muted eorl-grid-note" style="font-size: 11px; margin-bottom: 25px;"></div>

			<h5>Given a target power, how many runs do I need? (independent design)</h5>
			<div class="row" style="margin-bottom: 10px;">
				<div class="col-sm-2"><label class="text-muted">Effect (Hedges' g)</label>
					<input type="number" step="0.1" class="form-control eorl-effect2-input" value="0.5"></div>
				<div class="col-sm-2"><label class="text-muted">Target power</label>
					<input type="number" step="0.05" class="form-control eorl-power-input" value="0.8"></div>
				<div class="col-sm-2"><label class="text-muted">&nbsp;</label><div>
					<button class="btn btn-default eorl-compute-n-btn">Compute required N</button></div></div>
			</div>
			<div class="eorl-n-result"></div>
		</div>`
	).appendTo(page.body);

	const list = (s) => s.split(',').map((x) => x.trim()).filter(Boolean).map(Number);
	let current = null;

	eorl_lab.export.buttons(page, () => current && {
		name: `power_${current.design}_seed${current.seed}`,
		columns: ['design', 'standardized_effect', 'n_per_condition', 'power', 'mc_standard_error', 'n_simulations', 'seed'],
		rows: current.rows, data: current,
		metadata: { view: 'power_table', design: current.design, alpha: current.alpha, seed: current.seed, n_simulations: current.n_simulations },
	});

	$body.find('.eorl-grid-btn').on('click', () => {
		const effects = list($body.find('.eorl-effects-input').val());
		const ns = list($body.find('.eorl-ns-input').val());
		frappe.call({
			method: 'eorl_lab.api.analysis.compute_power_grid',
			args: {
				effects: JSON.stringify(effects), ns: JSON.stringify(ns), design: $body.find('.eorl-design').val(),
				alpha: $body.find('.eorl-alpha-input').val(), n_simulations: $body.find('.eorl-nsim-input').val(),
				seed: $body.find('.eorl-seed-input').val(),
			},
			freeze: true, freeze_message: __('Simulating...'),
			callback(r) {
				const d = (current = r.message);
				$body.find('.eorl-grid-head').html(`<tr><th>Effect</th>${ns.map((n) => `<th>n = ${n}</th>`).join('')}</tr>`);
				$body.find('.eorl-grid-rows').html(effects.map((e) => {
					const cells = ns.map((n) => {
						const row = d.rows.find((x) => x.standardized_effect === e && x.n_per_condition === n);
						return `<td>${(row.power * 100).toFixed(1)}% <small class="text-muted">± ${(row.mc_standard_error * 100).toFixed(1)}</small></td>`;
					});
					return `<tr><th>${e}</th>${cells.join('')}</tr>`;
				}).join(''));
				$body.find('.eorl-grid-note').text(`${d.design} design, alpha ${d.alpha}, ${d.n_simulations} simulations per cell, seed ${d.seed}. ± is one Monte Carlo standard error.`);
			},
		});
	});

	$body.find('.eorl-compute-n-btn').on('click', () => {
		frappe.call({
			method: 'eorl_lab.api.analysis.compute_required_sample_size',
			args: {
				standardized_effect: $body.find('.eorl-effect2-input').val(),
				target_power: $body.find('.eorl-power-input').val(),
				alpha: $body.find('.eorl-alpha-input').val(),
				seed: $body.find('.eorl-seed-input').val(),
			},
			freeze: true,
			callback(r) {
				const d = r.message;
				const html = d.required_n_per_group
					? `<strong>Required N per group: ${d.required_n_per_group}</strong> (achieved power ${(d.achieved_power * 100).toFixed(1)}%)`
					: `<strong>Target power not reached</strong> up to n=${d.searched_up_to} (best achieved: ${(d.achieved_power * 100).toFixed(1)}%)`;
				$body.find('.eorl-n-result').html(`<div class="card" style="padding: 12px; max-width: 500px;">${html}</div>`);
			},
		});
	});
};
