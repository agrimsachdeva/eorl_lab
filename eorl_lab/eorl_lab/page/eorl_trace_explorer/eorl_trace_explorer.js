frappe.pages['eorl-trace-explorer'].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'EORL Trace Explorer',
		single_column: true,
	});

	const state = { run: null, episode: null, events: [] };

	const $body = $(
		`<div style="padding: 15px;">
			<div class="row" style="margin-bottom: 10px;">
				<div class="col-sm-3">
					<label class="text-muted">Run</label>
					<select class="form-control eorl-run-select"><option value="">Select a run...</option></select>
				</div>
				<div class="col-sm-3">
					<label class="text-muted">Episode</label>
					<select class="form-control eorl-episode-select"><option value="">Select an episode...</option></select>
				</div>
				<div class="col-sm-2">
					<label class="text-muted">Event Type</label>
					<select class="form-control eorl-filter-type"><option value="">All</option></select>
				</div>
				<div class="col-sm-2">
					<label class="text-muted">Actor</label>
					<select class="form-control eorl-filter-actor"><option value="">All</option></select>
				</div>
				<div class="col-sm-2">
					<label class="text-muted">&nbsp;</label>
					<div><label><input type="checkbox" class="eorl-filter-failed"> Failures only</label></div>
				</div>
			</div>
			<table class="table table-bordered" style="background: var(--card-bg);">
				<thead>
					<tr>
						<th style="width:40px;">#</th><th>Event</th><th>Actor</th>
						<th>Target</th><th style="width:60px;">OK</th><th>Payload</th>
					</tr>
				</thead>
				<tbody class="eorl-event-rows"></tbody>
			</table>
		</div>`
	).appendTo(page.body);

	const $runSelect = $body.find('.eorl-run-select');
	const $episodeSelect = $body.find('.eorl-episode-select');
	const $typeFilter = $body.find('.eorl-filter-type');
	const $actorFilter = $body.find('.eorl-filter-actor');
	const $failedFilter = $body.find('.eorl-filter-failed');
	const $eventRows = $body.find('.eorl-event-rows');

	function load_runs(preselect_run, preselect_episode) {
		frappe.call({
			method: 'eorl_lab.api.runs.list_runs',
			args: { limit: 100 },
			callback(r) {
				(r.message || []).forEach((run) => {
					$runSelect.append(`<option value="${run.name}">${run.name} (${run.status})</option>`);
				});
				if (preselect_run) {
					$runSelect.val(preselect_run);
					load_episodes(preselect_run, preselect_episode);
				}
			},
		});
	}

	function load_episodes(run, preselect_episode) {
		state.run = run;
		$episodeSelect.empty().append('<option value="">Select an episode...</option>');
		frappe.call({
			method: 'eorl_lab.api.traces.list_episodes',
			args: { run },
			callback(r) {
				const episodes = r.message || [];
				episodes.forEach((ep) => {
					$episodeSelect.append(
						`<option value="${ep.name}">#${ep.episode_number} - ${ep.phase} - ${ep.status}</option>`
					);
				});
				if (!episodes.length) {
					$eventRows.empty();
					return;
				}
				// SOTA Milestone 10: a linked drill-down from Process
				// Explorer / Adaptation View can pre-select a SPECIFIC
				// episode (by name), not just default to the first one.
				const target = preselect_episode && episodes.find((ep) => ep.name === preselect_episode);
				const toLoad = target ? target.name : episodes[0].name;
				$episodeSelect.val(toLoad);
				load_trace(toLoad);
			},
		});
	}

	function load_trace(episode) {
		state.episode = episode;
		frappe.call({
			method: 'eorl_lab.api.traces.get_episode_trace',
			args: { episode },
			callback(r) {
				state.events = (r.message && r.message.events) || [];
				populate_filters();
				render_rows();
			},
		});
	}

	function populate_filters() {
		const types = [...new Set(state.events.map((e) => e.event_type))].sort();
		const actors = [...new Set(state.events.map((e) => e.actor_slot).filter(Boolean))].sort();
		$typeFilter.find('option:not(:first)').remove();
		$actorFilter.find('option:not(:first)').remove();
		types.forEach((t) => $typeFilter.append(`<option value="${t}">${t}</option>`));
		actors.forEach((a) => $actorFilter.append(`<option value="${a}">${a}</option>`));
	}

	function render_rows() {
		const type_filter = $typeFilter.val();
		const actor_filter = $actorFilter.val();
		const failed_only = $failedFilter.is(':checked');

		const filtered = state.events.filter((e) => {
			if (type_filter && e.event_type !== type_filter) return false;
			if (actor_filter && e.actor_slot !== actor_filter) return false;
			if (failed_only && e.success !== 0) return false;
			return true;
		});

		$eventRows.empty();
		if (!filtered.length) {
			$eventRows.append('<tr><td colspan="6" class="text-muted">No events match.</td></tr>');
			return;
		}

		filtered.forEach((e) => {
			let payload = '';
			try {
				payload = JSON.stringify(JSON.parse(e.payload_json || '{}'));
			} catch (err) {
				payload = e.payload_json || '';
			}
			const short_payload = payload.length > 120 ? payload.slice(0, 120) + '...' : payload;
			const ok_icon = e.success === 1 ? '✓' : e.success === 0 ? '✗' : '';
			const row_class = e.success === 0 ? 'text-danger' : '';

			const $row = $(
				`<tr class="${row_class}">
					<td>${e.sequence_no}</td>
					<td><strong>${e.event_type}</strong></td>
					<td>${frappe.utils.escape_html(e.actor_slot || '')}</td>
					<td>${frappe.utils.escape_html(e.target_type || '')} ${frappe.utils.escape_html(e.target_id || '')}</td>
					<td>${ok_icon}</td>
					<td><code class="eorl-payload" style="cursor:pointer;" title="Click to expand">${frappe.utils.escape_html(short_payload)}</code></td>
				</tr>`
			);
			$row.find('.eorl-payload').on('click', function () {
				$(this).text(payload);
			});
			$eventRows.append($row);
		});
	}

	$runSelect.on('change', () => {
		const pendingEpisode = $episodeSelect.data('eorl-pending-episode');
		$episodeSelect.removeData('eorl-pending-episode');
		load_episodes($runSelect.val(), pendingEpisode);
	});
	$episodeSelect.on('change', () => load_trace($episodeSelect.val()));
	$typeFilter.on('change', render_rows);
	$actorFilter.on('change', render_rows);
	$failedFilter.on('change', render_rows);

	load_runs(
		frappe.route_options && frappe.route_options.run,
		frappe.route_options && frappe.route_options.episode
	);
	frappe.route_options = null;
};

frappe.pages['eorl-trace-explorer'].on_page_show = function (wrapper) {
	// on_page_load only fires once per page instance in Frappe's SPA;
	// this re-applies a run (and, since SOTA Milestone 10, an episode)
	// selected from the Run Monitor / Process Explorer / Adaptation
	// View on every subsequent visit, not just the first.
	if (frappe.route_options && frappe.route_options.run) {
		const run = frappe.route_options.run;
		const episode = frappe.route_options.episode;
		frappe.route_options = null;
		const $runSelect = $(wrapper).find('.eorl-run-select');
		const $episodeSelect = $(wrapper).find('.eorl-episode-select');
		if ($runSelect.length) {
			if (!$runSelect.find(`option[value="${run}"]`).length) {
				$runSelect.append(`<option value="${run}">${run}</option>`);
			}
			$runSelect.val(run);
			// Call the page's own load_episodes directly (with the
			// episode to preselect) rather than firing a plain 'change'
			// event, which would drop the episode argument -- the
			// change handler bound below only forwards the run.
			$episodeSelect.data('eorl-pending-episode', episode);
			$runSelect.trigger('change');
		}
	}
};
