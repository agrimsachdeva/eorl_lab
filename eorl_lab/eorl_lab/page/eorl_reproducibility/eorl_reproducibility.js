frappe.pages['eorl-reproducibility'].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'EORL Reproducibility',
		single_column: true,
	});

	const $body = $(
		`<div style="padding: 15px;">
			<p class="text-muted">
				The full bundle (zip) contains run_manifest.json, architecture.json,
				resolved_agent_configs/, scenario_stream.jsonl, events.jsonl,
				process_paths.csv, metrics.csv, model_metadata.json,
				environment_metadata.json, code_commit.txt, requirements_lock.txt, and
				README_REPRODUCE.md -- everything spec section 7.9 asks for except a
				multi-experiment-aware manifest (this app doesn't yet link runs back
				to the experiment that launched them).
			</p>
			<div class="row">
				<div class="col-sm-6">
					<select class="form-control eorl-run-select"><option value="">Select a run...</option></select>
				</div>
				<div class="col-sm-3">
					<button class="btn btn-default eorl-quick-export-btn">Quick Export (JSON)</button>
				</div>
				<div class="col-sm-3">
					<button class="btn btn-primary eorl-full-bundle-btn">Download Full Bundle (.zip)</button>
				</div>
			</div>
			<div class="eorl-export-status text-muted" style="margin-top: 10px;"></div>
			<hr>
			<h5>Reproduce This Run</h5>
			<p class="text-muted">
				Launches a brand-new run from this run's own recorded seed, architecture,
				and regime shift, then verifies the new run's scenario-case hashes and
				computed metrics match this one's. Only works for runs launched via the
				config-driven architecture entrypoint (Milestone 5+) -- older runs don't
				carry enough configuration to replay and will report a clear error.
			</p>
			<button class="btn btn-default eorl-reproduce-btn">Reproduce &amp; Verify</button>
			<div class="eorl-reproduce-status" style="margin-top: 10px;"></div>
		</div>`
	).appendTo(page.body);

	const $select = $body.find('.eorl-run-select');
	const $status = $body.find('.eorl-export-status');
	const $reproduceStatus = $body.find('.eorl-reproduce-status');

	frappe.call({
		method: 'eorl_lab.api.runs.list_runs',
		args: { limit: 100 },
		callback(r) {
			(r.message || []).forEach((run) => {
				$select.append(`<option value="${run.name}">${run.name} (${run.status})</option>`);
			});
		},
	});

	$body.find('.eorl-quick-export-btn').on('click', () => {
		const run = $select.val();
		if (!run) {
			frappe.msgprint('Select a run first.');
			return;
		}
		$status.text('Exporting...');
		frappe.call({
			method: 'eorl_lab.api.exports.export_run_bundle',
			args: { run },
			callback(r) {
				const bundle = r.message;
				const blob = new Blob([JSON.stringify(bundle, null, 2)], { type: 'application/json' });
				const url = URL.createObjectURL(blob);
				const a = document.createElement('a');
				a.href = url;
				a.download = `${run}_bundle.json`;
				document.body.appendChild(a);
				a.click();
				document.body.removeChild(a);
				URL.revokeObjectURL(url);
				$status.text(
					`Exported ${run}: ${bundle.episodes.length} episode(s), ${bundle.events.length} event(s), ${bundle.memory_records.length} memory record(s).`
				);
			},
		});
	});

	$body.find('.eorl-full-bundle-btn').on('click', () => {
		const run = $select.val();
		if (!run) {
			frappe.msgprint('Select a run first.');
			return;
		}
		$status.text(`Preparing full bundle for ${run}...`);
		const url = `/api/method/eorl_lab.api.exports.download_full_bundle?run=${encodeURIComponent(run)}`;
		window.open(url, '_blank');
		$status.text(`Full bundle download started for ${run}.`);
	});

	$body.find('.eorl-reproduce-btn').on('click', () => {
		const run = $select.val();
		if (!run) {
			frappe.msgprint('Select a run first.');
			return;
		}
		$reproduceStatus.text('Reproducing (this launches a new run and may take a few seconds)...');
		frappe.call({
			method: 'eorl_lab.api.exports.reproduce_run',
			args: { run_name: run },
			callback(r) {
				const result = r.message;
				const scenario_badge = result.scenario_stream_matches
					? '<span class="indicator-pill green">Scenario stream matches</span>'
					: '<span class="indicator-pill red">Scenario stream MISMATCH</span>';
				const metrics_badge = result.metrics_match
					? '<span class="indicator-pill green">Metrics match</span>'
					: `<span class="indicator-pill red">Metrics differ: ${result.mismatched_metrics.join(', ')}</span>`;
				$reproduceStatus.html(
					`<div>Reproduction run: <a href="#" class="eorl-open-reproduction">${result.reproduction_run}</a></div>
					<div style="margin-top:5px;">${scenario_badge} ${metrics_badge}</div>`
				);
				$reproduceStatus.find('.eorl-open-reproduction').on('click', (e) => {
					e.preventDefault();
					frappe.route_options = { run: result.reproduction_run };
					frappe.set_route('eorl-trace-explorer');
				});
			},
			error() {
				$reproduceStatus.html('<span class="indicator-pill red">Reproduction failed -- see console/error log.</span>');
			},
		});
	});
};
