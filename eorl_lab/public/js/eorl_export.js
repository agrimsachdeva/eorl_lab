// Shared export helpers for the EORL Desk pages (submission-day plan
// section 18): every download carries the metadata needed to trace it
// back to the runs, plan and metric version that produced it.
frappe.provide('eorl_lab.export');

eorl_lab.export.metadata = function (extra) {
	return Object.assign({ generated_at: new Date().toISOString(), site: window.location.host }, extra || {});
};

eorl_lab.export._download = function (filename, text, mime) {
	const blob = new Blob([text], { type: mime });
	const a = document.createElement('a');
	a.href = URL.createObjectURL(blob);
	a.download = filename;
	document.body.appendChild(a);
	a.click();
	setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 0);
};

eorl_lab.export._cell = function (v) {
	if (v === null || v === undefined) return '';
	const s = typeof v === 'object' ? JSON.stringify(v) : String(v);
	return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
};

// CSV with the metadata as leading "# key: value" comment lines.
eorl_lab.export.csv = function (filename, columns, rows, metadata) {
	const lines = Object.entries(eorl_lab.export.metadata(metadata)).map(([k, v]) => `# ${k}: ${typeof v === 'object' ? JSON.stringify(v) : v}`);
	lines.push(columns.map(eorl_lab.export._cell).join(','));
	rows.forEach((r) => lines.push(columns.map((c) => eorl_lab.export._cell(r[c])).join(',')));
	eorl_lab.export._download(filename, lines.join('\n') + '\n', 'text/csv');
};

eorl_lab.export.json = function (filename, data, metadata) {
	eorl_lab.export._download(filename, JSON.stringify({ metadata: eorl_lab.export.metadata(metadata), data }, null, 1), 'application/json');
};

eorl_lab.export.copy = function (data, metadata) {
	const text = JSON.stringify({ metadata: eorl_lab.export.metadata(metadata), specification: data }, null, 1);
	frappe.utils.copy_to_clipboard(text);
};

// Adds Download CSV / Download JSON / Copy specification buttons to a page.
eorl_lab.export.buttons = function (page, getter) {
	page.add_inner_button(__('Download CSV'), () => {
		const x = getter();
		if (!x) return frappe.msgprint(__('Load data first.'));
		eorl_lab.export.csv(`${x.name}.csv`, x.columns, x.rows, x.metadata);
	}, __('Export'));
	page.add_inner_button(__('Download JSON'), () => {
		const x = getter();
		if (!x) return frappe.msgprint(__('Load data first.'));
		eorl_lab.export.json(`${x.name}.json`, x.data || x.rows, x.metadata);
	}, __('Export'));
	page.add_inner_button(__('Copy specification'), () => {
		const x = getter();
		if (!x) return frappe.msgprint(__('Load data first.'));
		eorl_lab.export.copy(x.specification || x.metadata, x.metadata);
	}, __('Export'));
};
