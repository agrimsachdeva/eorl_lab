frappe.pages['eorl-process-explorer'].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'EORL Process Explorer',
		single_column: true,
	});

	const $body = $(
		`<div style="padding: 15px;">
			<p class="text-muted">
				The directly-follows graph, path variants and episode swimlane of one run, under a
				registered sequence view. <b>all_actions</b> counts every tool call, including
				optional reads. <b>consequential_actions</b> drops reads and control calls and tags the
				sourcing decision with the supplier chosen. Both views come from the same events; an
				Analysis Plan names its view before launch.
			</p>
			<div class="row" style="margin-bottom: 15px;">
				<div class="col-sm-4">
					<label class="text-muted">Run</label>
					<select class="form-control eorl-run-select"><option value="">Select a run...</option></select>
				</div>
				<div class="col-sm-4">
					<label class="text-muted">Sequence scope</label>
					<select class="form-control eorl-scope-select">
						<option value="all_actions">all_actions</option>
						<option value="consequential_actions">consequential_actions</option>
						<option value="write_actions">write_actions</option>
						<option value="actor_function_actions">actor_function_actions</option>
					</select>
				</div>
			</div>
			<div class="eorl-pe-summary row" style="margin-bottom: 15px;"></div>
			<h5>Continuity and coherence <small class="text-muted eorl-coh-version"></small></h5>
			<div class="table-responsive"><table class="table table-bordered table-sm" style="background: var(--card-bg);">
				<tbody class="eorl-coherence-rows"></tbody></table></div>
			<h5>Directly-Follows Graph</h5>
			<div class="table-responsive">
				<table class="table table-bordered" style="background: var(--card-bg);">
					<thead><tr><th>From</th><th>To</th><th>Count</th><th>% of From's outgoing</th></tr></thead>
					<tbody class="eorl-dfg-rows"></tbody>
				</table>
			</div>
			<h5 style="margin-top: 20px;">Variants</h5>
			<div class="table-responsive">
				<table class="table table-bordered table-sm" style="background: var(--card-bg);">
					<thead><tr><th>#</th><th>Episodes</th><th>Share</th><th>Length</th><th>Path</th></tr></thead>
					<tbody class="eorl-variant-rows"></tbody>
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
	const $scopeSelect = $body.find('.eorl-scope-select');
	const $dfgRows = $body.find('.eorl-dfg-rows');
	const $swimlaneHeader = $body.find('.eorl-swimlane-header');
	const $swimlaneRows = $body.find('.eorl-swimlane-rows');
	let current = null;

	eorl_lab.export.buttons(page, () => current && {
		name: `process_${current.run}_${current.scope}`,
		columns: ['from', 'to', 'count', 'pct_of_from'],
		rows: current.dfg_edges,
		data: current,
		metadata: { run_ids: [current.run], sequence_scope: current.scope, taxonomy_version: current.taxonomy_version,
			metric_version: current.continuity.path_coherence_version, view: 'directly_follows_graph' },
		specification: { endpoint: 'eorl_lab.api.process.get_process_explorer_data', args: { run: current.run, scope: current.scope } },
	});

	const fmt = (v) => (v === null || v === undefined ? '—' : Number(v).toFixed(3));
	const esc = frappe.utils.escape_html;

	function load() {
		const run = $runSelect.val();
		if (!run) return;
		frappe.call({
			method: 'eorl_lab.api.process.get_process_explorer_data',
			args: { run, scope: $scopeSelect.val() },
			callback(r) {
				const data = (current = r.message);
				const s = data.summary;
				$body.find('.eorl-pe-summary').html(
					[['Episodes', s.episodes], ['Distinct paths', s.unique_sequence_count],
						['Sequence entropy (bits)', fmt(s.sequence_entropy)], ['Modal-path share', fmt(s.modal_path_share)]]
						.map(([k, v]) => `<div class="col-sm-3"><div class="card" style="padding:10px;"><div class="text-muted">${k}</div><div style="font-size:18px;">${v}</div></div></div>`).join('')
				);

				const c = data.continuity;
				$body.find('.eorl-coh-version').text(c.path_coherence_version);
				const rows = [['Actor continuity (Milestone 7)', c.actor_continuity], ['Functional continuity (Milestone 7)', c.functional_continuity]];
				Object.entries(c.path_coherence_v1).forEach(([k, v]) => rows.push([k === 'composite' ? '<b>Attribute-level path coherence (composite)</b>' : `&nbsp;&nbsp;coherence: ${k}`, v]));
				$body.find('.eorl-coherence-rows').html(rows.map(([k, v]) => `<tr><td>${k}</td><td>${fmt(v)}</td></tr>`).join(''));

				$dfgRows.html(data.dfg_edges.map((e) => `<tr><td>${esc(e.from)}</td><td>${esc(e.to)}</td><td>${e.count}</td><td>${e.pct_of_from}%</td></tr>`).join(''));
				$body.find('.eorl-variant-rows').html(data.variants.map((v) =>
					`<tr><td>${v.variant}</td><td>${v.episodes}</td><td>${fmt(v.share)}</td><td>${v.length}</td><td style="font-size:11px;">${v.path.map(esc).join(' → ')}</td></tr>`).join(''));

				const maxSteps = Math.max(0, ...data.swimlane.map((ep) => ep.steps.length));
				let headerHtml = '<th>Episode</th><th>Phase</th><th>Success</th><th>Utility</th>';
				for (let i = 0; i < maxSteps; i++) headerHtml += `<th>Step ${i + 1}</th>`;
				$swimlaneHeader.html(headerHtml);

				$swimlaneRows.empty();
				data.swimlane.forEach((ep) => {
					let rowHtml = `<td><a href="#" class="eorl-episode-drilldown" data-episode="${ep.episode}">${ep.episode_number}</a></td><td>${ep.phase}</td><td>${ep.success ? 'yes' : 'no'}</td><td>${fmt(ep.utility)}</td>`;
					for (let i = 0; i < maxSteps; i++) {
						const step = ep.steps[i];
						rowHtml += step ? `<td title="${esc(step.actor_slot || '')} (${step.category})">${esc(step.tool)}${step.choice ? `<br><small>${esc(step.choice)}</small>` : ''}</td>` : '<td></td>';
					}
					$swimlaneRows.append(`<tr data-run="${run}">${rowHtml}</tr>`);
				});
			},
		});
	}

	frappe.call({
		method: 'eorl_lab.api.runs.list_runs',
		args: { limit: 500 },
		callback(r) {
			(r.message || []).forEach((run) => {
				$runSelect.append(`<option value="${run.name}">${run.name} (${run.status})</option>`);
			});
			const opts = frappe.route_options || {};
			frappe.route_options = null;
			if (opts.run) {
				if (!$runSelect.find(`option[value="${opts.run}"]`).length) $runSelect.append(`<option value="${opts.run}">${opts.run}</option>`);
				$runSelect.val(opts.run);
				if (opts.scope) $scopeSelect.val(opts.scope);
				load();
			}
		},
	});

	$runSelect.on('change', load);
	$scopeSelect.on('change', load);

	$swimlaneRows.on('click', '.eorl-episode-drilldown', function (e) {
		e.preventDefault();
		const run = $(this).closest('tr').data('run');
		const episode = $(this).data('episode');
		frappe.route_options = { run, episode };
		frappe.set_route('eorl-trace-explorer');
	});
};
