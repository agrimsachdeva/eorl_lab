frappe.pages['eorl-process-explorer'].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'EORL Process Explorer',
		single_column: true,
	});

	const $body = $(
		`<div style="padding: 15px;">
			<p class="text-muted">
				SOTA Milestone 7 (spec section 39, scoped to its DFG + episode
				swimlane slice). The Directly-Follows Graph is pooled across
				every episode in this run (Milestone 7's own
				<code>directly_follows_graph</code> metric); the swimlane below
				shows each individual episode's own actor/tool sequence.
			</p>
			<div class="row" style="margin-bottom: 15px;">
				<div class="col-sm-4">
					<label class="text-muted">Run</label>
					<select class="form-control eorl-run-select"><option value="">Select a run...</option></select>
				</div>
			</div>
			<h5>Directly-Follows Graph</h5>
			<div class="table-responsive">
				<table class="table table-bordered" style="background: var(--card-bg);">
					<thead><tr><th>From</th><th>To</th><th>Count</th><th>% of From's outgoing</th></tr></thead>
					<tbody class="eorl-dfg-rows"></tbody>
				</table>
			</div>
			<h5 style="margin-top: 20px;">Episode Swimlane</h5>
			<div class="table-responsive">
				<table class="table table-bordered eorl-swimlane-table" style="background: var(--card-bg);">
					<thead><tr class="eorl-swimlane-header"><th>Episode</th><th>Phase</th><th>Success</th></tr></thead>
					<tbody class="eorl-swimlane-rows"></tbody>
				</table>
			</div>
		</div>`
	).appendTo(page.body);

	const $runSelect = $body.find('.eorl-run-select');
	const $dfgRows = $body.find('.eorl-dfg-rows');
	const $swimlaneHeader = $body.find('.eorl-swimlane-header');
	const $swimlaneRows = $body.find('.eorl-swimlane-rows');

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
			method: 'eorl_lab.api.process.get_process_explorer_data',
			args: { run },
			callback(r) {
				const data = r.message;

				$dfgRows.empty();
				data.dfg_edges.forEach((edge) => {
					$dfgRows.append(
						`<tr><td>${edge.from}</td><td>${edge.to}</td><td>${edge.count}</td><td>${edge.pct_of_from}%</td></tr>`
					);
				});

				const maxSteps = Math.max(0, ...data.swimlane.map((ep) => ep.steps.length));
				let headerHtml = '<th>Episode</th><th>Phase</th><th>Success</th>';
				for (let i = 0; i < maxSteps; i++) headerHtml += `<th>Step ${i + 1}</th>`;
				$swimlaneHeader.html(headerHtml);

				$swimlaneRows.empty();
				data.swimlane.forEach((ep) => {
					// SOTA Milestone 10: a linked drill-down into the
					// Trace Explorer for this exact episode -- not live
					// cross-filtering (each page stays independent), but
					// a real one-click path from "what happened in this
					// episode's process" to "show me every event".
					let rowHtml = `<td><a href="#" class="eorl-episode-drilldown" data-episode="${ep.episode}">${ep.episode_number}</a></td><td>${ep.phase}</td><td>${ep.success ? 'yes' : 'no'}</td>`;
					for (let i = 0; i < maxSteps; i++) {
						const step = ep.steps[i];
						rowHtml += step ? `<td title="${step.actor_slot}">${step.tool}</td>` : '<td></td>';
					}
					$swimlaneRows.append(`<tr data-run="${run}">${rowHtml}</tr>`);
				});
			},
		});
	});

	$swimlaneRows.on('click', '.eorl-episode-drilldown', function (e) {
		e.preventDefault();
		const run = $(this).closest('tr').data('run');
		const episode = $(this).data('episode');
		frappe.route_options = { run, episode };
		frappe.set_route('eorl-trace-explorer');
	});
};
