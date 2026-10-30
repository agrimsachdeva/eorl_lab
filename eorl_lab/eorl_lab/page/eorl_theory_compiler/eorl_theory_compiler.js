frappe.pages['eorl-theory-compiler'].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'EORL Theory Compiler',
		single_column: true,
	});

	const $body = $(
		`<div style="padding: 15px;">
			<p class="text-muted">
				SOTA Milestone 10 (spec section 21). A structured wizard, NOT
				autonomous theory generation (the spec's own words) -- fill in
				your theory's structure below and this scaffolds a real
				<code>EORL Experiment</code> + <code>EORL Analysis Plan</code>
				from it. <code>outcome_metric</code> is only auto-filled when
				your focal construct already has a real measurement function
				(today: Routine coherence, Adaptive repertoire); otherwise it's
				left as an explicit placeholder for you to fill in -- this never
				guesses a metric that doesn't exist.
			</p>
			<div class="row" style="margin-bottom: 10px;">
				<div class="col-sm-6">
					<label class="text-muted">1. Focal theoretical construct</label>
					<select class="form-control eorl-construct-select"><option value="">(none)</option></select>
				</div>
				<div class="col-sm-6">
					<label class="text-muted">Experiment name (optional, auto-generated if blank)</label>
					<input type="text" class="form-control eorl-experiment-name">
				</div>
			</div>
			<div class="row" style="margin-bottom: 10px;">
				<div class="col-sm-12">
					<label class="text-muted">2. Theoretical definition</label>
					<textarea class="form-control eorl-theoretical-definition" rows="2"></textarea>
				</div>
			</div>
			<div class="row" style="margin-bottom: 10px;">
				<div class="col-sm-12">
					<label class="text-muted">3. Proposed mechanism</label>
					<textarea class="form-control eorl-mechanism" rows="2"></textarea>
				</div>
			</div>
			<div class="row" style="margin-bottom: 10px;">
				<div class="col-sm-6">
					<label class="text-muted">4. Manipulation</label>
					<textarea class="form-control eorl-manipulation" rows="2"></textarea>
				</div>
				<div class="col-sm-6">
					<label class="text-muted">5. Counterfactual condition</label>
					<textarea class="form-control eorl-counterfactual" rows="2"></textarea>
				</div>
			</div>
			<div class="row" style="margin-bottom: 10px;">
				<div class="col-sm-12">
					<label class="text-muted">6. Outcomes</label>
					<textarea class="form-control eorl-outcomes" rows="2"></textarea>
				</div>
			</div>
			<div class="row" style="margin-bottom: 10px;">
				<div class="col-sm-6">
					<label class="text-muted">7. Mediating process measures</label>
					<textarea class="form-control eorl-mediating" rows="2"></textarea>
				</div>
				<div class="col-sm-6">
					<label class="text-muted">8. Boundary conditions</label>
					<textarea class="form-control eorl-boundary" rows="2"></textarea>
				</div>
			</div>
			<button class="btn btn-primary eorl-compile-btn">Compile Theory into Experiment Scaffold</button>
			<div class="eorl-compile-result" style="margin-top: 15px;"></div>
		</div>`
	).appendTo(page.body);

	const $constructSelect = $body.find('.eorl-construct-select');

	frappe.call({
		method: 'frappe.client.get_list',
		args: { doctype: 'EORL Construct', fields: ['name'], limit_page_length: 50 },
		callback(r) {
			(r.message || []).forEach((c) => $constructSelect.append(`<option value="${c.name}">${c.name}</option>`));
		},
	});

	$body.find('.eorl-compile-btn').on('click', () => {
		frappe.call({
			method: 'eorl_lab.api.experiments.compile_theory',
			args: {
				focal_construct: $constructSelect.val() || null,
				experiment_name: $body.find('.eorl-experiment-name').val() || null,
				theoretical_definition: $body.find('.eorl-theoretical-definition').val(),
				proposed_mechanism: $body.find('.eorl-mechanism').val(),
				manipulation: $body.find('.eorl-manipulation').val(),
				counterfactual_condition: $body.find('.eorl-counterfactual').val(),
				outcomes: $body.find('.eorl-outcomes').val(),
				mediating_measures: $body.find('.eorl-mediating').val(),
				boundary_conditions: $body.find('.eorl-boundary').val(),
			},
			callback(r) {
				const d = r.message;
				$body.find('.eorl-compile-result').html(
					`<div class="card" style="padding: 12px; max-width: 600px;">
						<strong>Scaffolded:</strong><br>
						<a href="/app/eorl-experiment/${d.experiment}">${d.experiment}</a><br>
						<a href="/app/eorl-analysis-plan/${d.analysis_plan}">${d.analysis_plan}</a>
						<hr>
						<strong>Next steps:</strong>
						<ul>${d.next_steps.map((s) => `<li>${s}</li>`).join('')}</ul>
					</div>`
				);
			},
		});
	});
};
