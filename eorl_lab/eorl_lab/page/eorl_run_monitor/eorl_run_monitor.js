frappe.pages['eorl-run-monitor'].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'EORL Run Monitor',
		single_column: true,
	});

	const $body = $(
		`<div style="padding: 15px;">
			<div class="text-muted" style="margin-bottom: 10px;">
				Auto-refreshes every 5 seconds. Click a run to open its trace.
			</div>
			<table class="table table-bordered" style="background: var(--card-bg);">
				<thead>
					<tr>
						<th>Run</th><th>Status</th><th>Seed</th><th>Episode</th>
						<th>Events</th><th>Started</th><th>Ended</th><th>Failure Reason</th>
					</tr>
				</thead>
				<tbody class="eorl-run-rows"></tbody>
			</table>
		</div>`
	).appendTo(page.body);

	const $rows = $body.find('.eorl-run-rows');

	function status_badge(status) {
		const colors = {
			completed: 'green', running: 'blue', failed: 'red',
			aborted: 'orange', queued: 'grey', initializing: 'blue',
		};
		return `<span class="indicator-pill ${colors[status] || 'grey'}">${frappe.utils.escape_html(status || '')}</span>`;
	}

	function refresh() {
		frappe.call({
			method: 'eorl_lab.api.runs.list_runs',
			args: { limit: 50 },
			callback(r) {
				const runs = r.message || [];
				$rows.empty();
				if (!runs.length) {
					$rows.append('<tr><td colspan="8" class="text-muted">No runs yet.</td></tr>');
					return;
				}
				runs.forEach((run) => {
					const $row = $(
						`<tr style="cursor:pointer;">
							<td><a href="#" class="eorl-open-trace">${run.name}</a></td>
							<td>${status_badge(run.status)}</td>
							<td>${run.run_seed ?? ''}</td>
							<td>${run.current_episode ?? ''}</td>
							<td>${run.event_count ?? ''}</td>
							<td>${frappe.datetime.str_to_user(run.started_at) || ''}</td>
							<td>${frappe.datetime.str_to_user(run.ended_at) || ''}</td>
							<td class="text-muted">${frappe.utils.escape_html(run.failure_reason || '')}</td>
						</tr>`
					);
					$row.find('.eorl-open-trace').on('click', (e) => {
						e.preventDefault();
						frappe.route_options = { run: run.name };
						frappe.set_route('eorl-trace-explorer');
					});
					$rows.append($row);
				});
			},
		});
	}

	refresh();
	const interval_id = setInterval(refresh, 5000);
	$(wrapper).on('hide', () => clearInterval(interval_id));
};
