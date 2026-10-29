frappe.pages['eorl-reproducibility'].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'EORL Reproducibility',
		single_column: true,
	});

	const $body = $(
		`<div style="padding: 15px;">
			<p class="text-muted">
				Exports one run's manifest, episodes, full event log, and memory
				records as a single JSON file. This is the raw-data half of spec
				section 7.9's reproducibility bundle -- resolved prompts, a replayable
				scenario stream, computed metrics, and a one-click re-run from the
				bundle are a later milestone.
			</p>
			<div class="row">
				<div class="col-sm-6">
					<select class="form-control eorl-run-select"><option value="">Select a run...</option></select>
				</div>
				<div class="col-sm-3">
					<button class="btn btn-primary eorl-export-btn">Export Bundle</button>
				</div>
			</div>
			<div class="eorl-export-status text-muted" style="margin-top: 10px;"></div>
		</div>`
	).appendTo(page.body);

	const $select = $body.find('.eorl-run-select');
	const $status = $body.find('.eorl-export-status');

	frappe.call({
		method: 'eorl_lab.api.runs.list_runs',
		args: { limit: 100 },
		callback(r) {
			(r.message || []).forEach((run) => {
				$select.append(`<option value="${run.name}">${run.name} (${run.status})</option>`);
			});
		},
	});

	$body.find('.eorl-export-btn').on('click', () => {
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
};
