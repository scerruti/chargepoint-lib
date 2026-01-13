// PyWebview JS API integration
function startDashboard() {
    const yearSelect = document.getElementById('year-select');
    const monthSelect = document.getElementById('month-select');
    const tableBody = document.querySelector('#session-table tbody');
    const modal = document.getElementById('modal');
    const modalBody = document.getElementById('modal-body');
    const closeBtn = document.querySelector('.close');

    // Load years
    window.pywebview.api.get_years().then(years => {
        years.forEach(y => {
            const opt = document.createElement('option');
            opt.value = y;
            opt.textContent = y;
            yearSelect.appendChild(opt);
        });
        if (years.length) yearSelect.value = years[years.length-1];
        loadMonths();
    });

    // Load months for selected year
    async function loadMonths() {
        monthSelect.innerHTML = '';
        const months = await window.pywebview.api.get_months(yearSelect.value);
        months.forEach(m => {
            const opt = document.createElement('option');
            opt.value = m;
            opt.textContent = m;
            monthSelect.appendChild(opt);
        });
        if (months.length) monthSelect.value = months[months.length-1];
        loadSessions();
    }

    // Load sessions for selected year/month
    async function loadSessions() {
        tableBody.innerHTML = '';
        const sessions = await window.pywebview.api.get_sessions(yearSelect.value, monthSelect.value);
        for (const sessionId of sessions) {
            const details = await window.pywebview.api.get_session_details(yearSelect.value, monthSelect.value, sessionId);
            const tr = document.createElement('tr');
            // Extract fields (date, time, duration, kWh, vehicle, confidence)
            const start = details.start_time || details.start || '';
            const dateObj = start ? new Date(start) : null;
            const dateStr = dateObj ? dateObj.toLocaleDateString() : '';
            const timeStr = dateObj ? dateObj.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : '';
            const duration = details.duration || (details.end_time && start ? ((new Date(details.end_time) - new Date(start))/60000).toFixed(0) + ' min' : '');
            const energy = details.energy_kwh || details.energy || '';
            const vehicle = (details.vehicle && details.vehicle.name) || details.vehicle_name || '';
            const confidence = details.confidence ? (details.confidence*100).toFixed(0)+'%' : '';
            [dateStr, timeStr, duration, energy, vehicle, confidence].forEach(val => {
                const td = document.createElement('td');
                td.textContent = val;
                tr.appendChild(td);
            });
            tr.addEventListener('click', () => showModal(details));
            tableBody.appendChild(tr);
        }
    }

    yearSelect.addEventListener('change', loadMonths);
    monthSelect.addEventListener('change', loadSessions);

    function showModal(details) {
        modalBody.innerHTML = '<pre>' + JSON.stringify(details, null, 2) + '</pre>';
        modal.style.display = 'block';
    }
    closeBtn.onclick = () => { modal.style.display = 'none'; };
    window.onclick = (event) => { if (event.target === modal) modal.style.display = 'none'; };
}

if (window.pywebview && window.pywebview.api) {
    startDashboard();
} else {
    document.addEventListener('pywebviewready', startDashboard);
}
