frappe.pages['eorl-power-planner'].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'EORL Power / Precision Planner',
		single_column: true,
	});

	const $body = $(
		`<div style="padding: 15px;">
			<p class="text-muted">
				SOTA Milestone 8 (spec section 49). Monte Carlo power estimates
				for the exact Welch's t-test <code>compare_groups</code> runs --
				not a closed-form formula -- so this reflects what the app's own
				test will actually detect.
			</p>
			<h5>Given n, how much power do I have?</h5>
			<div class="row" style="margin-bottom: 10px;">
				<div class="col-sm-2"><label class="text-muted">Standardized effect (Hedges' g)</label>
					<input type="number" step="0.1" class="form-control eorl-effect-input" value="0.5"></div>
				<div class="col-sm-2"><label class="text-muted">N per group</label>
					<input type="number" class="form-control eorl-n-input" value="10"></div>
				<div class="col-sm-2"><label class="text-muted">Alpha</label>
					<input type="number" step="0.01" class="form-control eorl-alpha-input" value="0.05"></div>
				<div class="col-sm-2"><label class="text-muted">&nbsp;</label><div>
					<button class="btn btn-primary eorl-compute-power-btn">Compute Power</button></div></div>
			</div>
			<div class="eorl-power-result" style="margin-bottom: 25px;"></div>

			<h5>Given a target power, how many runs do I need?</h5>
			<div class="row" style="margin-bottom: 10px;">
				<div class="col-sm-2"><label class="text-muted">Standardized effect (Hedges' g)</label>
					<input type="number" step="0.1" class="form-control eorl-effect2-input" value="0.5"></div>
				<div class="col-sm-2"><label class="text-muted">Target power</label>
					<input type="number" step="0.05" class="form-control eorl-power-input" value="0.8"></div>
				<div class="col-sm-2"><label class="text-muted">Alpha</label>
					<input type="number" step="0.01" class="form-control eorl-alpha2-input" value="0.05"></div>
				<div class="col-sm-2"><label class="text-muted">&nbsp;</label><div>
					<button class="btn btn-primary eorl-compute-n-btn">Compute Required N</button></div></div>
			</div>
			<div class="eorl-n-result"></div>
		</div>`
	).appendTo(page.body);

	$body.find('.eorl-compute-power-btn').on('click', () => {
		frappe.call({
			method: 'eorl_lab.api.analysis.compute_power_analysis',
			args: {
				standardized_effect: $body.find('.eorl-effect-input').val(),
				n_per_group: $body.find('.eorl-n-input').val(),
				alpha: $body.find('.eorl-alpha-input').val(),
			},
			callback(r) {
				const d = r.message;
				$body.find('.eorl-power-result').html(
					`<div class="card" style="padding: 12px; max-width: 400px;">
						<strong>Estimated power: ${(d.power * 100).toFixed(1)}%</strong><br>
						<span class="text-muted">effect=${d.standardized_effect}, n/group=${d.n_per_group}, alpha=${d.alpha}, ${d.n_simulations} simulations</span>
					</div>`
				);
			},
		});
	});

	$body.find('.eorl-compute-n-btn').on('click', () => {
		frappe.call({
			method: 'eorl_lab.api.analysis.compute_required_sample_size',
			args: {
				standardized_effect: $body.find('.eorl-effect2-input').val(),
				target_power: $body.find('.eorl-power-input').val(),
				alpha: $body.find('.eorl-alpha2-input').val(),
			},
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
